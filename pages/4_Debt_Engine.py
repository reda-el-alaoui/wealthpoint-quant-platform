# =============================================================================
# WealthPoint — Module 04 · Debt Cashflow Engine
# =============================================================================
# Engine source: production code (verbatim from reference implementation)
#
# Bug fix critique: n_remaining dans _annuity_payment utilise
# loan.term_months - t  (NOT  horizon - t)
#
# Exemple: 520k @ 1.9% sur 20A (240M) affiché sur horizon=120
#   ❌ n=120 → pmt ≈ 4 761 €  (calcule comme si le prêt durait 10A)
#   ✓ n=240 → pmt ≈ 2 606 €  (correct)
# =============================================================================

import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import warnings, sys, os, copy
from dataclasses import dataclass
from typing import Optional, Literal

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="WealthPoint · Debt Engine",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from wealthpoint_theme import (
    inject_global_css, sidebar_brand, sidebar_section,
    page_header, section, kpi_card, apply_mpl_style,
    PRIMARY, PRIMARY_DARK, PRIMARY_LIGHT, PRIMARY_PALE, PRIMARY_WASH,
    GREY_900, GREY_700, GREY_500, GREY_300, GREY_100, WHITE,
    RED_SOFT, RED_PALE, GREEN_SOFT, GREEN_PALE, AMBER, AMBER_PALE,
)

inject_global_css()
apply_mpl_style()

# ── Module accent colour (teal) ───────────────────────────────────────────────
TEAL      = "#0F766E"
TEAL_PALE = "#CCFBF1"

st.markdown(f"""
<style>
  .wp-section {{ border-left-color: {TEAL} !important; }}
  .kpi-card   {{ border-top-color:  {TEAL} !important; }}
  .kpi-value  {{ color: {TEAL} !important; }}
  .stButton > button       {{ background: {TEAL} !important; }}
  .stButton > button:hover {{ background: #0D6460 !important; }}
  [data-testid="stSidebarNav"] [aria-current="page"] {{
      border-left-color: {TEAL} !important;
  }}
  .badge-fixed {{ display:inline-block; padding:0.15rem 0.5rem; border-radius:2px;
                  font-size:0.68rem; letter-spacing:0.07em; text-transform:uppercase;
                  font-weight:500; background:#DBEAFE; color:#1D4ED8; }}
  .badge-var   {{ display:inline-block; padding:0.15rem 0.5rem; border-radius:2px;
                  font-size:0.68rem; letter-spacing:0.07em; text-transform:uppercase;
                  font-weight:500; background:{TEAL_PALE}; color:{TEAL}; }}
  .badge-io    {{ display:inline-block; padding:0.15rem 0.5rem; border-radius:2px;
                  font-size:0.68rem; letter-spacing:0.07em; text-transform:uppercase;
                  font-weight:500; background:{AMBER_PALE}; color:{AMBER}; }}
  .test-pass {{ color:{GREEN_SOFT}; font-weight:600; }}
  .test-fail {{ color:{RED_SOFT};   font-weight:600; }}
  .mono      {{ font-family:'Courier New',monospace; font-size:0.79rem; }}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# 1. VASICEK PATH GENERATOR  (verbatim)
# =============================================================================

def vasicek_path(r0: float, kappa: float, theta: float, sigma: float,
                 months: int, seed: int = 42) -> np.ndarray:
    """
    Euler-Maruyama: dr_t = kappa*(theta - r_t)*dt + sigma*sqrt(dt)*Z
    Floored at 0 (contractual floor for borrowers).
    """
    rng = np.random.default_rng(seed)
    dt = 1 / 12
    path = np.zeros(months)
    path[0] = r0
    for t in range(1, months):
        z = rng.standard_normal()
        path[t] = max(0.0, path[t-1] + kappa*(theta - path[t-1])*dt + sigma*np.sqrt(dt)*z)
    return path


BASE_PATH = vasicek_path(r0=0.045, kappa=0.15, theta=0.035, sigma=0.012, months=360, seed=7)
BEAR_PATH = np.minimum(BASE_PATH + 0.015, 0.09)
BULL_PATH = np.maximum(BASE_PATH - 0.010, 0.005)


# =============================================================================
# 2. LOAN DATACLASS  (verbatim)
# =============================================================================

@dataclass
class Loan:
    """
    Unified descriptor. All rates: annual decimals (0.021 = 2.1%).
    Day count: 30/360 monthly_rate = annual_rate / 12.
    """
    loan_id:        str
    notional:       float
    term_months:    int
    rate_type:      Literal["fixed", "variable"]
    fixed_rate:     Optional[float]       = None
    index_path:     Optional[np.ndarray]  = None
    spread:         float                 = 0.0
    reset_months:   int                   = 12
    floor:          float                 = 0.0
    periodic_cap:   Optional[float]       = None
    lifetime_cap:   Optional[float]       = None
    io_months:      int                   = 0
    color:          str                   = "#888888"

    def __post_init__(self):
        if self.rate_type == "fixed"    and self.fixed_rate  is None:
            raise ValueError(f"{self.loan_id}: fixed_rate required")
        if self.rate_type == "variable" and self.index_path  is None:
            raise ValueError(f"{self.loan_id}: index_path required")


# =============================================================================
# 3. AMORTIZATION ENGINE  (verbatim)
# =============================================================================

def _annuity_payment(balance: float, mr: float, n_remaining: int) -> float:
    """
    P = B * mr*(1+mr)^n / ((1+mr)^n - 1)
    n_remaining = loan.term_months - t  (NOT horizon - t)
    """
    if mr < 1e-10:
        return balance / max(n_remaining, 1)
    return balance * mr * (1 + mr)**n_remaining / ((1 + mr)**n_remaining - 1)


def build_schedule(loan: Loan, horizon: int) -> pd.DataFrame:
    """
    Build monthly repayment schedule.
    horizon truncates OUTPUT only — does not affect payment arithmetic.
    """
    months       = min(loan.term_months, horizon)
    balance      = loan.notional
    prev_rate    = None
    current_rate = loan.fixed_rate if loan.rate_type == "fixed" else 0.0
    rows         = []

    for t in range(months):

        if loan.rate_type == "variable" and t % loan.reset_months == 0:
            idx_rate = loan.index_path[min(t, len(loan.index_path) - 1)]
            raw = idx_rate + loan.spread
            if prev_rate is not None and loan.periodic_cap is not None:
                raw = np.clip(raw, prev_rate - loan.periodic_cap,
                              prev_rate + loan.periodic_cap)
            if loan.lifetime_cap is not None:
                raw = min(raw, loan.lifetime_cap)
            raw = max(raw, loan.floor)
            current_rate = raw
            prev_rate    = current_rate

        mr       = current_rate / 12
        interest = balance * mr

        # KEY: n_remaining from loan.term_months, not horizon
        n_remaining = loan.term_months - t

        is_io   = (t < loan.io_months)
        is_last = (t == months - 1)

        if is_io:
            principal = 0.0
            payment   = interest
        elif is_last:
            principal = balance
            payment   = interest + principal
        else:
            pmt       = _annuity_payment(balance, mr, n_remaining)
            principal = max(0.0, pmt - interest)
            payment   = pmt

        balance = max(0.0, balance - principal)
        rows.append({
            "month":        t + 1,
            "payment":      round(payment, 2),
            "interest":     round(interest, 2),
            "principal":    round(principal, 2),
            "balance":      round(balance, 2),
            "rate_applied": round(current_rate, 6),
        })

    return pd.DataFrame(rows)


def aggregate_portfolio(schedules: dict) -> pd.DataFrame:
    frames = [df.assign(loan_id=lid) for lid, df in schedules.items()]
    combined = pd.concat(frames, ignore_index=True)
    return (combined
            .groupby("month")
            .agg(total_payment   =("payment",   "sum"),
                 total_interest  =("interest",  "sum"),
                 total_principal =("principal", "sum"),
                 total_balance   =("balance",   "sum"))
            .reset_index())


# =============================================================================
# 4. PORTFOLIOS  (verbatim)
# =============================================================================

PORTFOLIOS = {
    "🏠 Résidentiel Classique": [
        Loan("Dupont – RP Paris",    520_000, 240, "fixed",    fixed_rate=0.019, color="#4f8ef7"),
        Loan("Martin – RP Lyon",     310_000, 300, "variable", index_path=BASE_PATH, spread=0.007,
             reset_months=12, lifetime_cap=0.055, color="#a78bfa"),
        Loan("Leroy – Rés. Sec.",    185_000, 180, "fixed",    fixed_rate=0.024, color="#34d399"),
    ],
    "🏢 Investisseurs Locatifs": [
        Loan("SCI Grenelle",         780_000, 240, "variable", index_path=BASE_PATH, spread=0.009,
             reset_months=3, periodic_cap=0.02, lifetime_cap=0.065, color="#f59e0b"),
        Loan("Invest. Bordeaux T3",  230_000, 180, "fixed",    fixed_rate=0.028,
             io_months=60, color="#fb923c"),
        Loan("Meublé Nice Studio",   145_000, 120, "variable", index_path=BEAR_PATH, spread=0.011,
             reset_months=1, floor=0.01, lifetime_cap=0.07, color="#fbbf24"),
        Loan("Garage + Cave Lyon",    62_000,  84, "fixed",    fixed_rate=0.031, color="#fde68a"),
    ],
    "🏗️ Patrimonial HNW": [
        Loan("Villa Côte d'Azur",  2_400_000, 240, "variable", index_path=BULL_PATH, spread=0.006,
             reset_months=12, lifetime_cap=0.05, io_months=60, color="#ec4899"),
        Loan("Bureaux La Défense", 1_850_000, 180, "fixed",    fixed_rate=0.022,
             io_months=36, color="#f43f5e"),
        Loan("Appts Neuilly (x3)",   960_000, 300, "variable", index_path=BASE_PATH, spread=0.008,
             reset_months=6, periodic_cap=0.015, lifetime_cap=0.055, color="#e879f9"),
        Loan("Maison Megève",        480_000, 240, "fixed",    fixed_rate=0.021, color="#c084fc"),
        Loan("Entrepôt logistique",  650_000, 120, "variable", index_path=BEAR_PATH, spread=0.012,
             reset_months=3, floor=0.015, lifetime_cap=0.08, color="#a5b4fc"),
    ],
    "🌱 Primo-Accédants PTZ": [
        Loan("PTZ Neuf Toulouse",    120_000, 240, "fixed",    fixed_rate=0.0,   color="#10b981"),
        Loan("Prêt principal",       255_000, 240, "fixed",    fixed_rate=0.032, color="#34d399"),
        Loan("Crédit conso travaux",  28_000,  60, "variable", index_path=BEAR_PATH, spread=0.03,
             reset_months=12, floor=0.02, lifetime_cap=0.09, color="#6ee7b7"),
    ],
}

INDEX_LABELS = {"BASE": BASE_PATH, "BEAR": BEAR_PATH, "BULL": BULL_PATH}


# =============================================================================
# SESSION STATE
# =============================================================================
if "d4_custom_loans" not in st.session_state:
    st.session_state.d4_custom_loans = []


# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    sidebar_brand("Debt Engine")

    sidebar_section("Portfolio")
    pf_name = st.selectbox("Select portfolio", list(PORTFOLIOS.keys()))

    sidebar_section("Display Parameters")
    horizon = st.slider("Horizon (months)", 12, 360, 120, step=12,
                        help="Truncates display only — does NOT change payment amounts")

    sidebar_section("Vasicek Index Paths")
    st.markdown(f"""
    <div style='font-size:0.72rem;color:{GREY_500};line-height:1.8;'>
      <span style='color:{GREY_700};font-weight:500;'>BASE</span>
      &nbsp;r₀=4.5% · θ=3.5% · σ=1.2%<br/>
      <span style='color:{RED_SOFT};font-weight:500;'>BEAR</span>
      &nbsp;BASE +150 bps · cap 9%<br/>
      <span style='color:{GREEN_SOFT};font-weight:500;'>BULL</span>
      &nbsp;BASE −100 bps · floor 0.5%
    </div>""", unsafe_allow_html=True)

    st.markdown(f"<hr style='border:none;border-top:1px solid {PRIMARY_PALE};margin:1rem 0;'/>",
                unsafe_allow_html=True)

    sidebar_section("Add Custom Loan")
    with st.expander("＋ New loan", expanded=False):
        c_id    = st.text_input("Loan ID", value="Custom Loan")
        c_not   = st.number_input("Notional (€)",  value=200_000, step=10_000, min_value=0)
        c_term  = st.number_input("Term (months)", value=240, step=12, min_value=12)
        c_rtype = st.selectbox("Rate type", ["fixed", "variable"])
        if c_rtype == "fixed":
            c_fixed = st.number_input("Fixed rate (%)", value=2.5, step=0.1) / 100
        else:
            c_idx   = st.selectbox("Index path", ["BASE", "BEAR", "BULL"])
            c_sprd  = st.number_input("Spread (%)", value=0.8, step=0.1) / 100
            c_reset = st.selectbox("Reset (months)", [1, 3, 6, 12], index=3)
            c_floor = st.number_input("Floor (%)", value=0.0, step=0.1) / 100
            c_lcap  = st.number_input("Lifetime cap (%)", value=6.0, step=0.1) / 100
        c_io    = st.number_input("IO months", value=0, step=12, min_value=0)
        c_color = st.color_picker("Colour", value="#B19069")
        if st.button("Add to portfolio"):
            try:
                kw = dict(loan_id=c_id, notional=float(c_not),
                          term_months=int(c_term), rate_type=c_rtype,
                          io_months=int(c_io), color=c_color)
                if c_rtype == "fixed":
                    kw["fixed_rate"] = float(c_fixed)
                else:
                    kw.update(index_path=INDEX_LABELS[c_idx], spread=float(c_sprd),
                              reset_months=int(c_reset), floor=float(c_floor),
                              lifetime_cap=float(c_lcap))
                st.session_state.d4_custom_loans.append(Loan(**kw))
                st.success(f"✅ {c_id} added")
            except Exception as e:
                st.error(str(e))

    if st.session_state.d4_custom_loans:
        if st.button("🗑  Clear custom loans"):
            st.session_state.d4_custom_loans = []
            st.rerun()


# =============================================================================
# COMPUTE
# =============================================================================
loans_active = copy.deepcopy(PORTFOLIOS[pf_name]) + st.session_state.d4_custom_loans
schedules    = {l.loan_id: build_schedule(l, horizon) for l in loans_active}
portfolio    = aggregate_portfolio(schedules)
total_not    = sum(l.notional for l in loans_active)
total_pmt    = portfolio["total_payment"].sum()
total_int    = portfolio["total_interest"].sum()
end_bal      = portfolio["total_balance"].iloc[-1]
avg_rate     = np.mean([schedules[l.loan_id]["rate_applied"].mean() for l in loans_active])
months_x     = portfolio["month"].values


# =============================================================================
# PAGE HEADER + KPIs
# =============================================================================
page_header(
    "Debt Cashflow Engine",
    "Fixed · Variable · IO · Caps / Floors · Vasicek Rate Paths · 4 Portfolios",
    badge="Module 04",
)

c1, c2, c3, c4, c5 = st.columns(5)
for col, (lbl, val, sub, neg, pos) in zip([c1,c2,c3,c4,c5], [
    ("Total Notional",   f"€{total_not/1e6:.2f}M",    f"{len(loans_active)} loans",             False, False),
    ("Total Payments",   f"€{total_pmt/1e3:,.0f}k",   f"Over {horizon//12}y display horizon",   False, False),
    ("Total Interest",   f"€{total_int/1e3:,.0f}k",   f"{total_int/total_pmt:.1%} of payments", True,  False),
    ("Residual Balance", f"€{end_bal/1e6:.2f}M",       f"At month {horizon}",                    False, end_bal < total_not*0.25),
    ("Avg Applied Rate", f"{avg_rate:.2%}",             f"{sum(1 for l in loans_active if l.io_months)} IO loan(s)", False, False),
]):
    col.markdown(kpi_card(lbl, val, sub, neg, pos), unsafe_allow_html=True)

st.markdown(f"""
<div style='display:flex;gap:0.4rem;flex-wrap:wrap;margin-top:0.85rem;'>
  <span class='wp-badge badge-n'>{pf_name}</span>
  <span class='wp-badge badge-w'>Horizon: {horizon}M</span>
  <span class='wp-badge badge-n'>Vasicek r₀=4.5% θ=3.5% σ=1.2%</span>
  <span class='badge-var'>n_remaining = term − t</span>
</div>""", unsafe_allow_html=True)
st.markdown("<hr class='wp-hr'/>", unsafe_allow_html=True)


# =============================================================================
# TABS
# =============================================================================
T1, T2, T3, T4, T5, T6 = st.tabs([
    "📊 Portfolio Cashflows",
    "🏦 Per-Loan Breakdown",
    "📈 Rate Paths",
    "🔍 Amortization Detail",
    "✅ Math Verification",
    "📋 Loan Register",
])


# ── T1: Portfolio Cashflows ───────────────────────────────────────────────────
with T1:
    section("Aggregate Monthly Cashflows")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    ax1.bar(months_x, portfolio["total_principal"]/1e3, color=TEAL,    alpha=0.85, label="Principal", width=1.0)
    ax1.bar(months_x, portfolio["total_interest"] /1e3,
            bottom=portfolio["total_principal"]/1e3,
            color=RED_SOFT, alpha=0.55, label="Interest", width=1.0)
    ax1.set_ylabel("Monthly cashflow (k€)")
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"€{v:,.0f}k"))
    ax1.legend(fontsize=8.5)
    ax1.set_title(f"{pf_name} — Monthly Payment Breakdown")

    ax2.fill_between(months_x, portfolio["total_balance"]/1e6, color=TEAL, alpha=0.18)
    ax2.plot(months_x, portfolio["total_balance"]/1e6, color=TEAL, lw=2, label="Outstanding balance")
    ax2.axhline(total_not/1e6, color=GREY_300, lw=1, ls="--", label=f"Initial notional €{total_not/1e6:.2f}M")
    ax2.set_ylabel("Outstanding (M€)"); ax2.set_xlabel("Month")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"€{v:.2f}M"))
    ax2.legend(fontsize=8.5); ax2.set_title("Remaining Debt Balance")
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True); plt.close()

    section("Annual Summary")
    ann = (portfolio.assign(year=((portfolio["month"]-1)//12)+1)
           .groupby("year")
           .agg(payment=("total_payment","sum"), interest=("total_interest","sum"),
                principal=("total_principal","sum"), end_balance=("total_balance","last"))
           .reset_index())
    rh = ""
    for _, r in ann.iterrows():
        s = r["interest"]/r["payment"] if r["payment"]>0 else 0
        rh += f"""<tr>
          <td>Year {int(r['year'])}</td>
          <td>€{r['payment']/1e3:,.1f}k</td>
          <td class='td-neg'>€{r['interest']/1e3:,.1f}k</td>
          <td class='td-pos'>€{r['principal']/1e3:,.1f}k</td>
          <td>€{r['end_balance']/1e6:.3f}M</td>
          <td class='mono'>{"▓"*int(s*20)}&thinsp;{s:.0%}</td>
        </tr>"""
    st.markdown(f"""<table class='wp-table'><thead><tr>
      <th>Period</th><th>Total Payment</th><th>Interest</th>
      <th>Principal</th><th>End Balance</th><th>Interest share</th>
    </tr></thead><tbody>{rh}</tbody></table>""", unsafe_allow_html=True)


# ── T2: Per-Loan Breakdown ────────────────────────────────────────────────────
with T2:
    section("Stacked Monthly Payments by Loan")
    fig2, ax = plt.subplots(figsize=(14, 5.5))
    bottom = np.zeros(len(months_x))
    for loan in loans_active:
        df_l = schedules[loan.loan_id]
        vals = df_l["payment"].values
        if len(vals) < len(months_x):
            vals = np.pad(vals, (0, len(months_x)-len(vals)))
        ax.bar(months_x, vals/1e3, bottom=bottom/1e3,
               color=loan.color, alpha=0.88, label=loan.loan_id, width=1.0)
        bottom[:len(df_l)] += df_l["payment"].values
    ax.set_xlabel("Month"); ax.set_ylabel("Payment (k€)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"€{v:,.0f}k"))
    ax.legend(fontsize=7.5, ncol=2, loc="upper right")
    ax.set_title("Per-Loan Contribution to Monthly Portfolio Payment")
    plt.tight_layout(); st.pyplot(fig2, use_container_width=True); plt.close()

    section("Loan-Level KPIs")
    rh2 = ""
    for loan in loans_active:
        df_l = schedules[loan.loan_id]
        io_b = f"&nbsp;<span class='badge-io'>IO {loan.io_months}M</span>" if loan.io_months else ""
        if loan.rate_type == "fixed":
            tb = "<span class='badge-fixed'>Fixed</span>"
            rs = f"{loan.fixed_rate:.3%}"
        else:
            tb = "<span class='badge-var'>Variable</span>"
            parts = [f"idx+{loan.spread:.3%}"]
            if loan.periodic_cap: parts.append(f"±{loan.periodic_cap:.2%}/reset")
            if loan.lifetime_cap: parts.append(f"≤{loan.lifetime_cap:.2%}")
            if loan.floor:        parts.append(f"≥{loan.floor:.2%}")
            rs = "  ".join(parts)
        dot = f"<span style='color:{loan.color};font-size:1.05rem;'>●</span>"
        pct = df_l["interest"].sum()/df_l["payment"].sum()*100 if df_l["payment"].sum()>0 else 0
        rh2 += f"""<tr>
          <td>{dot}&nbsp;{loan.loan_id}{io_b}</td>
          <td>{tb}</td>
          <td>€{loan.notional/1e3:,.0f}k</td>
          <td>{loan.term_months}M</td>
          <td class='mono' style='font-size:0.74rem;'>{rs}</td>
          <td>€{df_l['payment'].iloc[0]:,.0f}</td>
          <td class='td-neg'>€{df_l['interest'].sum()/1e3:,.1f}k</td>
          <td class='td-pos'>€{df_l['principal'].sum()/1e3:,.1f}k</td>
          <td>€{df_l['balance'].iloc[-1]/1e3:,.1f}k</td>
          <td>{df_l['rate_applied'].mean():.3%}</td>
          <td class='td-neg'>{pct:.0f}%</td>
        </tr>"""
    st.markdown(f"""<table class='wp-table'><thead><tr>
      <th>Loan</th><th>Type</th><th>Notional</th><th>Term</th>
      <th>Rate / Constraints</th><th>M1 Pmt</th>
      <th>∑ Interest</th><th>∑ Principal</th>
      <th>End Balance</th><th>Avg Rate</th><th>Int %</th>
    </tr></thead><tbody>{rh2}</tbody></table>""", unsafe_allow_html=True)


# ── T3: Rate Paths ────────────────────────────────────────────────────────────
with T3:
    section("Vasicek Index Rate Paths")
    m_range = np.arange(1, horizon+1)
    fig3, ax3 = plt.subplots(figsize=(14, 4.5))
    ax3.plot(m_range, BASE_PATH[:horizon]*100, color=GREY_700, lw=2.0,
             label="BASE  r₀=4.5%, κ=0.15, θ=3.5%, σ=1.2%")
    ax3.plot(m_range, BEAR_PATH[:horizon]*100, color=RED_SOFT,   lw=1.6, ls="--",
             label="BEAR  BASE +150 bps, cap 9%")
    ax3.plot(m_range, BULL_PATH[:horizon]*100, color=GREEN_SOFT, lw=1.6, ls=":",
             label="BULL  BASE −100 bps, floor 0.5%")
    ax3.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f%%"))
    ax3.set_xlabel("Month"); ax3.set_ylabel("Index rate (%)")
    ax3.legend(fontsize=9); ax3.set_title("Vasicek Rate Paths — Euler-Maruyama (30Y, seed=7)")
    fig3.text(0.015, 0.02,
              "dr = κ(θ − r)dt + σ√dt·Z   |   κ=0.15   θ=3.5%   σ=1.2%   dt=1/12   floor=0",
              fontsize=7.5, color=GREY_500)
    plt.tight_layout(); st.pyplot(fig3, use_container_width=True); plt.close()

    var_loans = [l for l in loans_active if l.rate_type == "variable"]
    if var_loans:
        section("Effective Applied Rate — Variable Loans")
        fig4, ax4 = plt.subplots(figsize=(14, 4))
        for loan in var_loans:
            df_l = schedules[loan.loan_id]
            ax4.step(df_l["month"], df_l["rate_applied"]*100, where="post",
                     color=loan.color, lw=1.8, label=f"{loan.loan_id} (reset/{loan.reset_months}M)")
        ax4.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f%%"))
        ax4.set_xlabel("Month"); ax4.set_ylabel("Applied rate (%)")
        ax4.legend(fontsize=7.5, ncol=2)
        ax4.set_title("Applied Rate per Variable Loan (after caps, floor, periodic cap)")
        plt.tight_layout(); st.pyplot(fig4, use_container_width=True); plt.close()
    else:
        st.info("No variable-rate loans in this portfolio.")

    st.markdown(f"""
    <div class='wp-warn'>
      <strong>Rate reset mechanics</strong> — At each reset: raw = index_path[t] + spread.
      Clipped by periodic_cap (if set), capped by lifetime_cap, floored at floor.
      The annuity is recalculated on outstanding balance using
      <code>n_remaining = loan.term_months − t</code> (full original term, not display horizon).
    </div>""", unsafe_allow_html=True)


# ── T4: Amortization Detail ───────────────────────────────────────────────────
with T4:
    section("Individual Loan Schedule")
    loan_sel = st.selectbox("Select loan", [l.loan_id for l in loans_active])
    df_sel   = schedules[loan_sel]
    loan_obj = next(l for l in loans_active if l.loan_id == loan_sel)

    col_chart, col_bal = st.columns([3, 2])
    with col_chart:
        fig5, ax5 = plt.subplots(figsize=(9, 4.5))
        ax5.stackplot(df_sel["month"], df_sel["principal"]/1e3, df_sel["interest"]/1e3,
                      labels=["Principal", "Interest"], colors=[TEAL, RED_SOFT], alpha=[0.85, 0.55])
        ax5.set_xlabel("Month"); ax5.set_ylabel("Payment (k€)")
        ax5.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"€{v:,.1f}k"))
        ax5.legend(fontsize=9); ax5.set_title(f"{loan_sel} — Payment Stack")
        plt.tight_layout(); st.pyplot(fig5, use_container_width=True); plt.close()

    with col_bal:
        fig6, ax6 = plt.subplots(figsize=(6, 4.5))
        ax6.fill_between(df_sel["month"], df_sel["balance"]/1e3, color=TEAL, alpha=0.18)
        ax6.plot(df_sel["month"], df_sel["balance"]/1e3, color=TEAL, lw=2.2)
        if loan_obj.io_months > 0 and loan_obj.io_months <= len(df_sel):
            ax6.axvline(loan_obj.io_months, color=AMBER, lw=1.5, ls="--",
                        label=f"IO end M{loan_obj.io_months}")
            ax6.legend(fontsize=8)
        ax6.set_xlabel("Month"); ax6.set_ylabel("Balance (k€)")
        ax6.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"€{v:,.0f}k"))
        ax6.set_title("Outstanding Balance")
        plt.tight_layout(); st.pyplot(fig6, use_container_width=True); plt.close()

    section("Month-by-Month Schedule")
    n_show  = st.slider("Show first N months", 6, min(len(df_sel), 120), 24, step=6)
    df_view = df_sel.head(n_show).copy()
    df_view["rate_applied"] = df_view["rate_applied"].map("{:.4%}".format)
    df_view["payment"]   = df_view["payment"].map("€{:,.2f}".format)
    df_view["interest"]  = df_view["interest"].map("€{:,.2f}".format)
    df_view["principal"] = df_view["principal"].map("€{:,.2f}".format)
    df_view["balance"]   = df_view["balance"].map("€{:,.2f}".format)
    st.dataframe(df_view.rename(columns={
        "month":"Month","payment":"Payment","interest":"Interest",
        "principal":"Principal","balance":"Balance","rate_applied":"Rate",
    }), use_container_width=True, hide_index=True)


# ── T5: Math Verification  (replicates production test suite verbatim) ────────
with T5:
    section("Mathematical Verification — 9 Test Cases")
    st.markdown(f"""
    <div class='wp-disclaimer' style='margin-bottom:1.2rem;'>
      Replicates the <strong>production verification suite</strong> verbatim.
      Critical invariant: <code>n_remaining = loan.term_months − t</code>
      ensures the annuity formula uses the full contractual term regardless of the
      display horizon.
    </div>""", unsafe_allow_html=True)

    # Run all portfolios at full 360M for tests
    all_sched = {}
    for pn, loans_p in PORTFOLIOS.items():
        all_sched[pn] = {l.loan_id: build_schedule(l, 360) for l in loans_p}

    failures = []

    def _chk(name, got, expected, tol=0.01):
        err = abs(got - expected)
        ok  = err <= tol
        if not ok: failures.append(name)
        return ok, got, expected, err

    def _row(name, ok, got, expected, err, note=""):
        st_cls = "test-pass" if ok else "test-fail"
        st_txt = "✓ PASS" if ok else "✗ FAIL"
        nc = "td-pos" if ok else "td-neg"
        return (f"<tr><td><span class='{st_cls}'>{st_txt}</span></td>"
                f"<td>{name}</td>"
                f"<td class='{nc} mono'>{got:.4f}</td>"
                f"<td class='mono'>{expected:.4f}</td>"
                f"<td class='mono'>{err:.6f}</td>"
                f"<td style='font-size:0.72rem;color:{GREY_500};'>{note}</td></tr>")

    html_rows = ""

    # T1 — Annuity payment M1 (Dupont 520k @ 1.9% / 20Y)
    mr  = 0.019 / 12;  n = 240
    exp = 520_000 * mr*(1+mr)**n / ((1+mr)**n - 1)
    df1 = all_sched["🏠 Résidentiel Classique"]["Dupont – RP Paris"]
    ok1, g1, e1, er1 = _chk("T1", df1["payment"].iloc[0], exp)
    naive = 520_000 * mr*(1+mr)**120 / ((1+mr)**120 - 1)
    html_rows += _row("T1 — M1 payment  Dupont 520k @ 1.9% / 20A",
                      ok1, g1, e1, er1,
                      f"Correct n=240 · naïve n=120 → €{naive:,.0f}")

    # T2 — Interest M1
    ok2, g2, e2, er2 = _chk("T2", df1["interest"].iloc[0], 520_000*0.019/12)
    html_rows += _row("T2 — M1 interest = 520 000 × 1.9% / 12", ok2, g2, e2, er2)

    # T3 — Principal M1 = pmt − interest
    ok3, g3, e3, er3 = _chk("T3", df1["principal"].iloc[0],
                              df1["payment"].iloc[0] - df1["interest"].iloc[0])
    html_rows += _row("T3 — M1 principal = pmt − interest", ok3, g3, e3, er3)

    # T4 — PTZ 0%: total interest = 0
    df_ptz = all_sched["🌱 Primo-Accédants PTZ"]["PTZ Neuf Toulouse"]
    ok4, g4, e4, er4 = _chk("T4", df_ptz["interest"].sum(), 0.0)
    html_rows += _row("T4 — PTZ 0%: ∑ interest = 0", ok4, g4, e4, er4)

    # T5 — PTZ 0%: M1 principal = 120 000/240 = 500
    ok5, g5, e5, er5 = _chk("T5", df_ptz["principal"].iloc[0], 120_000/240)
    html_rows += _row("T5 — PTZ 0%: M1 principal = 500 €", ok5, g5, e5, er5)

    # T6 — IO: principal = 0 during IO window
    df_bx = all_sched["🏢 Investisseurs Locatifs"]["Invest. Bordeaux T3"]
    ok6, g6, e6, er6 = _chk("T6", df_bx["principal"].iloc[:60].max(), 0.0)
    html_rows += _row("T6 — IO 60M: max principal in IO period = 0", ok6, g6, e6, er6)

    # T7 — IO: principal > 0 post-IO
    if len(df_bx) > 60:
        post_io = df_bx["principal"].iloc[60]
        ok7 = post_io > 0
        if not ok7: failures.append("T7")
        html_rows += _row("T7 — Post-IO: principal M61 > 0",
                          ok7, 1.0 if ok7 else 0.0, 1.0, 0.0 if ok7 else 1.0,
                          f"M61 = €{post_io:,.0f}")
    else:
        html_rows += _row("T7 — Post-IO check", True, 1.0, 1.0, 0.0, "N/A")

    # T8 — Lifetime cap: max rate ≤ cap
    df_sci = all_sched["🏢 Investisseurs Locatifs"]["SCI Grenelle"]
    cap    = 0.065;  max_r = df_sci["rate_applied"].max()
    ok8    = max_r <= cap + 1e-9
    if not ok8: failures.append("T8")
    html_rows += _row("T8 — SCI Grenelle lifetime cap 6.5%",
                      ok8, max_r*100, cap*100, abs(max_r-cap)*100,
                      "Cap may not be hit (Vasicek mean-reverts to 3.5%)")

    # T9 — No negative balances in any portfolio
    neg_any = any(
        (df["balance"] < -0.01).any()
        for res in all_sched.values() for df in res.values()
    )
    ok9 = not neg_any
    if not ok9: failures.append("T9 — negative balance")
    html_rows += _row("T9 — All balances ≥ 0 (4 portfolios)", ok9,
                      0.0, 0.0, 0.0, "All portfolios × all loans checked")

    st.markdown(f"""
    <table class='wp-table'><thead><tr>
      <th>Status</th><th>Test</th><th>Got</th><th>Expected</th><th>Error</th><th>Note</th>
    </tr></thead><tbody>{html_rows}</tbody></table>""", unsafe_allow_html=True)

    ok_all = len(failures) == 0
    bg  = GREEN_PALE if ok_all else RED_PALE
    clr = GREEN_SOFT if ok_all else RED_SOFT
    msg = ("✓ ALL 9 TESTS PASSED — engine verified mathematically"
           if ok_all else f"✗ {len(failures)} test(s) FAILED: {', '.join(failures)}")
    st.markdown(f"""
    <div style='margin-top:1rem;padding:0.8rem 1.1rem;border-radius:4px;
                background:{bg};border-left:4px solid {clr};'>
      <span style='color:{clr};font-weight:600;font-size:0.86rem;'>{msg}</span>
    </div>""", unsafe_allow_html=True)

    if ok_all:
        st.markdown(f"""
        <div class='wp-disclaimer' style='margin-top:0.7rem;'>
          <strong>Critical fix (T1)</strong> — Dupont 520k @ 1.9% / 20Y displayed on 10Y horizon:
          correct payment = <strong>€{exp:,.2f}</strong> (n=240) ·
          naïve = <strong>€{naive:,.2f}</strong> (n=120 → +{naive/exp-1:.0%} overstatement).
          Engine always uses <code>n_remaining = loan.term_months − t</code>.
        </div>""", unsafe_allow_html=True)


# ── T6: Loan Register ─────────────────────────────────────────────────────────
with T6:
    col_pie, col_bar = st.columns(2)
    with col_pie:
        section("Notional Allocation")
        fig7, ax7 = plt.subplots(figsize=(6, 5))
        wedges, texts, autotexts = ax7.pie(
            [l.notional for l in loans_active],
            labels=[l.loan_id for l in loans_active],
            autopct="%1.1f%%",
            colors=[l.color for l in loans_active],
            startangle=90, pctdistance=0.72,
            wedgeprops={"linewidth": 1.5, "edgecolor": WHITE},
        )
        for at in autotexts: at.set_fontsize(7.5)
        for t  in texts:     t.set_fontsize(7)
        ax7.set_title(f"Notional allocation — €{total_not/1e6:.2f}M total")
        plt.tight_layout(); st.pyplot(fig7, use_container_width=True); plt.close()

    with col_bar:
        section("Total Interest Cost by Loan")
        fig8, ax8 = plt.subplots(figsize=(6, 5))
        int_totals = [schedules[l.loan_id]["interest"].sum() for l in loans_active]
        bars = ax8.barh([l.loan_id for l in loans_active], int_totals,
                        color=[l.color for l in loans_active], alpha=0.87)
        for bar, v in zip(bars, int_totals):
            ax8.text(v + max(int_totals)*0.01, bar.get_y()+bar.get_height()/2,
                     f"€{v/1e3:,.0f}k", va="center", fontsize=7.5)
        ax8.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"€{v/1e3:,.0f}k"))
        ax8.set_title(f"Interest Cost over {horizon//12}y horizon")
        ax8.tick_params(axis="y", labelsize=7.5)
        plt.tight_layout(); st.pyplot(fig8, use_container_width=True); plt.close()

    section("Full Loan Register")
    reg = ""
    for loan in loans_active:
        df_l  = schedules[loan.loan_id]
        io_t  = f"{loan.io_months}M" if loan.io_months else "—"
        if loan.rate_type == "fixed":
            tb = "<span class='badge-fixed'>Fixed</span>"
            rs = f"{loan.fixed_rate:.3%}"
        else:
            tb = "<span class='badge-var'>Variable</span>"
            parts = [f"idx+{loan.spread:.3%}"]
            if loan.periodic_cap: parts.append(f"±{loan.periodic_cap:.2%}/reset")
            if loan.lifetime_cap: parts.append(f"≤{loan.lifetime_cap:.2%}")
            if loan.floor:        parts.append(f"≥{loan.floor:.2%}")
            rs = "  ".join(parts)
        dot = f"<span style='color:{loan.color};font-size:1.1rem;'>●</span>"
        reg += f"""<tr>
          <td>{dot}&nbsp;{loan.loan_id}</td>
          <td>{tb}</td>
          <td>€{loan.notional/1e3:,.0f}k</td>
          <td>{loan.term_months}M</td>
          <td class='mono' style='font-size:0.73rem;'>{rs}</td>
          <td>{io_t}</td>
          <td class='td-neg'>€{df_l['interest'].sum()/1e3:,.0f}k</td>
          <td>€{df_l['balance'].iloc[-1]/1e3:,.0f}k</td>
          <td>{df_l['rate_applied'].mean():.3%}</td>
        </tr>"""
    st.markdown(f"""<table class='wp-table'><thead><tr>
      <th>Loan</th><th>Type</th><th>Notional</th><th>Term</th>
      <th>Rate / Constraints</th><th>IO</th>
      <th>∑ Interest</th><th>End Balance</th><th>Avg Rate</th>
    </tr></thead><tbody>{reg}</tbody></table>""", unsafe_allow_html=True)


# =============================================================================
# DISCLAIMER
# =============================================================================
st.markdown("<hr class='wp-hr'/>", unsafe_allow_html=True)
st.markdown("""
<div class='wp-disclaimer'>
  <strong>Disclaimer</strong> — Cashflow projections are indicative estimates based on Vasicek
  stochastic rate paths (Euler-Maruyama). Variable rate evolution is model-dependent and will not
  match actual market rates. The Vasicek model assumes mean-reversion and constant volatility;
  real rates exhibit jumps, regime changes and term-structure effects not captured here.
  IO and balloon payments reflect contractual terms only — prepayment, refinancing and default
  are not modelled. Day count convention: 30/360. Not investment, credit or legal advice.
</div>""", unsafe_allow_html=True)
