"""
WealthPoint — Wealth Forecast  (pages/2_Wealth_Forecast.py)
Long-horizon Monte Carlo projection with life events
"""
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dataclasses import dataclass
from typing import Optional, Literal
from datetime import date
from dateutil.relativedelta import relativedelta
import copy, sys, os

st.set_page_config(
    page_title="WealthPoint · Wealth Forecast",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from wealthpoint_theme import (
    inject_global_css, sidebar_brand, sidebar_section,
    page_header, section, kpi_card, fmt_chf,
    PRIMARY, PRIMARY_DARK, PRIMARY_LIGHT, PRIMARY_PALE, PRIMARY_WASH,
    PRIMARY_MID,
    GREY_900, GREY_700, GREY_500, GREY_300, GREY_100, WHITE,
    RED_SOFT, GREEN_SOFT, AMBER, AMBER_PALE,
)

inject_global_css()

# ── Plotly theme aligned to WealthPoint ──────────────────────────────────────
PLOT_LAYOUT = dict(
    paper_bgcolor=WHITE,
    plot_bgcolor=GREY_100,
    font=dict(family="DM Sans, sans-serif", color=GREY_700, size=11),
    legend=dict(bgcolor=WHITE, bordercolor=PRIMARY_PALE, borderwidth=1,
                font=dict(size=10)),
    xaxis=dict(gridcolor=WHITE, showgrid=True, tickfont=dict(size=10),
               linecolor=GREY_300),
    yaxis=dict(gridcolor=WHITE, showgrid=True, tickfont=dict(size=10),
               linecolor=GREY_300),
    hovermode="x unified",
    hoverlabel=dict(bgcolor=WHITE, bordercolor=PRIMARY_PALE,
                    font=dict(color=GREY_900, family="DM Sans, sans-serif")),
    margin=dict(l=20, r=140, t=30, b=20),
)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
BUCKETS       = ["cash","listed","privateMarkets","realEstate"]
BUCKET_LABELS = {"cash":"Cash","listed":"Listed Equities",
                 "privateMarkets":"Private Markets","realEstate":"Real Estate"}
BUCKET_COLORS = {"cash":PRIMARY_LIGHT,"listed":PRIMARY,
                 "privateMarkets":PRIMARY_DARK,"realEstate":PRIMARY_MID}
EVENT_TYPES   = ["INCOME","EXPENSE","ASSET_SALE","ASSET_PURCHASE",
                 "CAPITAL_CALL","DISTRIBUTION","TAX","DONATION","INHERITANCE"]
TODAY         = date.today().replace(day=1)

# ── DATA CLASSES ──────────────────────────────────────────────────────────────
@dataclass
class WealthEvent:
    id: str; name: str; type: str
    start_date: date; end_date: Optional[date]
    frequency: Literal["ONCE","MONTHLY","ANNUAL"]
    amount: float; bucket: str

def yr(n): return TODAY + relativedelta(years=n)

DEFAULT_EVENTS = [
    WealthEvent("ev1","Salary income",       "INCOME",     TODAY, yr(5),  "MONTHLY", +30_000,    "cash"),
    WealthEvent("ev2","Living expenses",     "EXPENSE",    TODAY, yr(10), "MONTHLY", -20_000,    "cash"),
    WealthEvent("ev3","Real estate sale",    "ASSET_SALE", yr(5), None,   "ONCE",    +5_000_000, "cash"),
    WealthEvent("ev4","Annual tax payment",  "TAX",        TODAY, yr(20), "ANNUAL",  -300_000,   "cash"),
    WealthEvent("ev5","Charitable donation", "DONATION",   yr(12),None,   "ONCE",    -500_000,   "cash"),
]

# ── SESSION STATE ─────────────────────────────────────────────────────────────
if "wf_events" not in st.session_state:
    st.session_state.wf_events = copy.deepcopy(DEFAULT_EVENTS)

# ── HELPERS ───────────────────────────────────────────────────────────────────
def build_monthly_events(events, start, n_months):
    monthly = [{} for _ in range(n_months)]
    for ev in events:
        for i in range(n_months):
            d = start + relativedelta(months=i); amt = 0.0
            if ev.frequency == "ONCE":
                if d.year==ev.start_date.year and d.month==ev.start_date.month:
                    amt=ev.amount
            elif ev.frequency == "MONTHLY":
                end=ev.end_date or (start+relativedelta(months=n_months))
                if ev.start_date<=d<=end: amt=ev.amount
            elif ev.frequency == "ANNUAL":
                end=ev.end_date or (start+relativedelta(months=n_months))
                if ev.start_date<=d<=end and d.month==ev.start_date.month: amt=ev.amount
            if amt!=0: monthly[i][ev.bucket]=monthly[i].get(ev.bucket,0)+amt
    return monthly

def event_total(ev, n_months):
    total=0.0
    for i in range(n_months):
        d=TODAY+relativedelta(months=i); amt=0.0
        if ev.frequency=="ONCE":
            if d.year==ev.start_date.year and d.month==ev.start_date.month: amt=ev.amount
        elif ev.frequency=="MONTHLY":
            end=ev.end_date or (TODAY+relativedelta(months=n_months))
            if ev.start_date<=d<=end: amt=ev.amount
        elif ev.frequency=="ANNUAL":
            end=ev.end_date or (TODAY+relativedelta(months=n_months))
            if ev.start_date<=d<=end and d.month==ev.start_date.month: amt=ev.amount
        total+=amt
    return total

# ── SIMULATION ────────────────────────────────────────────────────────────────
CORR = np.array([
    [1.00,0.05,0.05,0.05],
    [0.05,1.00,0.60,0.30],
    [0.05,0.60,1.00,0.40],
    [0.05,0.30,0.40,1.00],
])

@st.cache_data(show_spinner=False)
def run_mc(net_worth, bw_tuple, mu_tuple, sig_tuple, inflation,
           events_tuple, horizon_years, n_paths, seed):
    weights = list(bw_tuple)
    mu_a    = list(mu_tuple)
    sig_a   = list(sig_tuple)
    n_mo    = horizon_years*12
    events  = [WealthEvent(*e) for e in events_tuple]
    mf      = build_monthly_events(events, TODAY, n_mo)
    L       = np.linalg.cholesky(CORR)
    rng     = np.random.default_rng(seed)

    mu_m    = np.array([(1+m)**(1/12)-1 for m in mu_a])
    sig_m   = np.array([s/np.sqrt(12) for s in sig_a])
    infl_m  = (1+inflation)**(1/12)-1

    bkts    = np.array([[net_worth*w for w in weights]]*n_paths, dtype=np.float64)
    paths   = np.zeros((n_paths, n_mo+1)); paths[:,0]=bkts.sum(axis=1)
    infl    = np.ones(n_mo+1)

    for t in range(n_mo):
        z    = rng.standard_normal((n_paths,4))@L.T
        rets = np.clip(mu_m+sig_m*z, -0.40, 0.40)
        bkts*=(1+rets)
        for bi,b in enumerate(BUCKETS):
            if b in mf[t]: bkts[:,bi]+=mf[t][b]
        bkts=np.maximum(bkts,0)
        if (t+1)%12==0:
            tot=bkts.sum(axis=1,keepdims=True)
            bkts=tot*np.array(weights)
        paths[:,t+1]=bkts.sum(axis=1)
        infl[t+1]=infl[t]*(1+infl_m)
    return paths, infl

def pcts(paths):
    return {k:np.percentile(paths,p,axis=0)
            for k,p in [("p10",10),("p25",25),("p50",50),("p75",75),("p90",90)]}

def fstats(paths):
    f=paths[:,-1]
    return {k:float(getattr(np,fn)(f))
            for k,fn in [("p10","percentile10"),("p25","percentile25"),("p50","median"),
                         ("p75","percentile75"),("p90","percentile90"),("mean","mean")]}

def fstats(paths):
    f=paths[:,-1]
    return {"p10":float(np.percentile(f,10)),"p25":float(np.percentile(f,25)),
            "p50":float(np.percentile(f,50)),"p75":float(np.percentile(f,75)),
            "p90":float(np.percentile(f,90)),"mean":float(np.mean(f))}

# ══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════
with st.sidebar:
    sidebar_brand("Wealth Forecast")

    sidebar_section("Initial Wealth")
    net_worth    = st.number_input("Net Worth (CHF)", value=10_000_000, step=500_000, format="%d")
    st.markdown(f"<div style='font-size:0.78rem;color:{GREY_700};margin:0.4rem 0 0.2rem;'>Initial allocation</div>",
                unsafe_allow_html=True)
    w_cash   = st.slider("Cash (%)",          0,100,20)
    w_listed = st.slider("Listed Equities (%)",0,100,50)
    w_priv   = st.slider("Private Markets (%)",0,100,20)
    w_re     = st.slider("Real Estate (%)",   0,100,10)
    tot_w    = w_cash+w_listed+w_priv+w_re
    if tot_w!=100:
        st.markdown(f"<div class='wp-warn'>⚠ Total = {tot_w}% — must equal 100%</div>",
                    unsafe_allow_html=True)

    sidebar_section("Return Assumptions")
    c1,c2=st.columns(2)
    with c1:
        st.caption("μ (%/yr)")
        mu_cash  = st.number_input("Cash",   value=1.0,step=0.1,format="%.1f",key="mu_c")/100
        mu_lst   = st.number_input("Listed", value=5.0,step=0.1,format="%.1f",key="mu_l")/100
        mu_priv  = st.number_input("Private",value=7.0,step=0.1,format="%.1f",key="mu_p")/100
        mu_re    = st.number_input("Real Est",value=3.5,step=0.1,format="%.1f",key="mu_r")/100
    with c2:
        st.caption("σ (%/yr)")
        sig_cash = st.number_input("Cash",   value=0.5, step=0.1,format="%.1f",key="sg_c")/100
        sig_lst  = st.number_input("Listed", value=15.0,step=0.5,format="%.1f",key="sg_l")/100
        sig_priv = st.number_input("Private",value=20.0,step=0.5,format="%.1f",key="sg_p")/100
        sig_re   = st.number_input("Real Est",value=10.0,step=0.5,format="%.1f",key="sg_r")/100
    inflation = st.slider("Inflation (%/yr)",0.0,6.0,2.0,0.1)/100

    sidebar_section("Simulation")
    horizon_years = st.select_slider("Horizon (years)",[10,15,20,25,30,40,50],value=20)
    n_paths       = st.select_slider("MC Paths",[500,1000,2000,5000],value=2000)
    show_real     = st.toggle("Real terms (inflation-adjusted)",value=False)
    seed          = st.number_input("Random seed",value=42,step=1)

    st.markdown(f"<hr style='border:none;border-top:1px solid {PRIMARY_PALE};margin:1rem 0 0.5rem;'/>",
                unsafe_allow_html=True)
    run_btn = st.button("▶  Run Forecast", use_container_width=True)

# ══════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════

st.title(" ")
page_header(
    "Wealth Forecast",
    f"Monte Carlo projection · {n_paths:,} paths · Horizon {horizon_years} years · "
    f"{'Real' if show_real else 'Nominal'} terms",
    badge="Module 02"
)

# Guard: allocation must sum to 100
if tot_w != 100:
    st.markdown(f"<div class='wp-warn'>⚠ Allocation sums to {tot_w}%. Please adjust sliders to 100% before running.</div>",
                unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════════════
# RUN SIMULATION
# ══════════════════════════════════════════════════════════════════════
tw = max(tot_w,1)
bw = (w_cash/tw, w_listed/tw, w_priv/tw, w_re/tw)

events_tpl = tuple(
    (e.id,e.name,e.type,e.start_date,e.end_date,e.frequency,e.amount,e.bucket)
    for e in st.session_state.wf_events
)

with st.spinner("Running Monte Carlo simulation…"):
    paths, infl = run_mc(
        net_worth, bw,
        (mu_cash,mu_lst,mu_priv,mu_re),
        (sig_cash,sig_lst,sig_priv,sig_re),
        inflation, events_tpl,
        horizon_years, n_paths, seed,
    )

dp    = paths/infl[np.newaxis,:] if show_real else paths
pc    = pcts(dp)
st_   = fstats(dp)
n_mo  = horizon_years*12
dates_ax = [TODAY+relativedelta(months=i) for i in range(n_mo+1)]

# ══════════════════════════════════════════════════════════════════════
# KPI ROW
# ══════════════════════════════════════════════════════════════════════
prob_double = float((dp[:,-1]>=net_worth*2).mean()*100)
prob_loss   = float((dp[:,-1]<net_worth).mean()*100)
infl_total  = (infl[-1]-1)*100
p50_real    = pc["p50"][-1]/infl[-1]

cols = st.columns(5)
for col,(lbl,val,sub,neg,pos) in zip(cols,[
    ("P50 — Base Case",   fmt_chf(st_["p50"]), f"×{st_['p50']/net_worth:.1f} initial capital", False,True),
    ("P10 — Adverse",     fmt_chf(st_["p10"]), f"×{st_['p10']/net_worth:.1f} initial capital", True, False),
    ("P90 — Favourable",  fmt_chf(st_["p90"]), f"×{st_['p90']/net_worth:.1f} initial capital", False,True),
    ("Prob. to Double",   f"{prob_double:.0f}%","of simulated paths",                          False,prob_double>40),
    ("Prob. of Loss",     f"{prob_loss:.0f}%",  "paths below initial capital",                 prob_loss>10,False),
]):
    col.markdown(kpi_card(lbl,val,sub,neg,pos), unsafe_allow_html=True)

p50_real_html = fmt_chf(p50_real)
st.markdown(f"""
<div style='display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:0.8rem;'>
  <span class='wp-badge badge-n'>P50 real terms: {p50_real_html}</span>
  <span class='wp-badge badge-w'>Cumul. inflation: {infl_total:.0f}%</span>
  <span class='wp-badge badge-n'>Horizon: {horizon_years} years</span>
</div>""", unsafe_allow_html=True)

st.markdown("<hr class='wp-hr'/>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════
t1,t2,t3,t4 = st.tabs(["Projection","Assumptions","Life Events","Report"])

# ─── Tab 1: Projection ───────────────────────────────────────────────
with t1:
    section("Wealth Trajectory")

    fig = go.Figure()
    # Bands
    fig.add_trace(go.Scatter(
        x=dates_ax+dates_ax[::-1],
        y=list(pc["p90"]/1e6)+list(pc["p10"][::-1]/1e6),
        fill="toself", fillcolor=f"rgba(177,144,105,0.10)",
        line=dict(color="rgba(0,0,0,0)"), name="P10–P90", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=dates_ax+dates_ax[::-1],
        y=list(pc["p75"]/1e6)+list(pc["p25"][::-1]/1e6),
        fill="toself", fillcolor=f"rgba(177,144,105,0.22)",
        line=dict(color="rgba(0,0,0,0)"), name="P25–P75", hoverinfo="skip",
    ))
    # P50 median
    fig.add_trace(go.Scatter(x=dates_ax, y=pc["p50"]/1e6,
        line=dict(color=PRIMARY,width=2.5), name="P50 median"))
    # P10 / P90
    fig.add_trace(go.Scatter(x=dates_ax, y=pc["p10"]/1e6,
        line=dict(color=PRIMARY_DARK,width=1,dash="dot"), name="P10", opacity=0.7))
    fig.add_trace(go.Scatter(x=dates_ax, y=pc["p90"]/1e6,
        line=dict(color=PRIMARY_DARK,width=1,dash="dot"), name="P90", opacity=0.7))
    # Real P50 overlay
    if not show_real:
        fig.add_trace(go.Scatter(x=dates_ax, y=(pc["p50"]/infl)/1e6,
            line=dict(color=GREY_300,width=1.5,dash="dash"),
            name="P50 real (infl.adj.)", opacity=0.65))
    # Initial capital
    fig.add_hline(y=net_worth/1e6,
        line=dict(color=PRIMARY_PALE,width=1.5,dash="dash"),
        annotation_text="Initial capital",
        annotation_font_color=GREY_500, annotation_font_size=10)
    # Event markers
    for ev in st.session_state.wf_events:
        if ev.frequency=="ONCE":
            ev_d=ev.start_date
            if TODAY<=ev_d<=TODAY+relativedelta(years=horizon_years):
                col=GREEN_SOFT if ev.amount>0 else RED_SOFT
                fig.add_vline(x=str(ev_d),line=dict(color=col,width=1,dash="dot"),opacity=0.55)
                fig.add_annotation(x=str(ev_d),y=pc["p90"][-1]/1e6,text=ev.name,
                    textangle=-50,font=dict(color=GREY_500,size=9),
                    showarrow=False,yshift=8)
    # End labels
    for lbl,key,col in [("P90","p90",PRIMARY_LIGHT),("P50","p50",PRIMARY),("P10","p10",PRIMARY_DARK)]:
        fig.add_annotation(x=dates_ax[-1],y=pc[key][-1]/1e6,
            text=f"  {lbl}: {fmt_chf(pc[key][-1])}",
            xanchor="left",yanchor="middle",
            font=dict(color=col,size=10),showarrow=False)

    fig.update_layout(**{**PLOT_LAYOUT,"height":430,
        "yaxis":dict(**PLOT_LAYOUT["yaxis"],ticksuffix="M",title="Net Worth (CHF M)"),
        "plot_bgcolor":GREY_100})
    st.plotly_chart(fig, use_container_width=True)

    # Row 2: distribution + probability curve
    c1,c2=st.columns(2)
    with c1:
        section("Final Distribution")
        fv=dp[:,-1]/1e6
        fig2=go.Figure()
        fig2.add_trace(go.Histogram(x=fv,nbinsx=60,
            marker=dict(color=PRIMARY_PALE,line=dict(color=PRIMARY_LIGHT,width=0.5)),
            opacity=0.9,name="Distribution"))
        for key,col,dash in [("p10",RED_SOFT,"dash"),("p50",PRIMARY,"solid"),("p90",GREEN_SOFT,"dash")]:
            fig2.add_vline(x=st_[key]/1e6,line=dict(color=col,width=1.5,dash=dash),
                annotation_text=key.upper(),
                annotation_font_color=col,annotation_font_size=10)
        fig2.update_layout(**{**PLOT_LAYOUT,"height":300,"margin":dict(l=20,r=20,t=20,b=20),
            "xaxis":dict(**PLOT_LAYOUT["xaxis"],ticksuffix="M",title="CHF M"),
            "yaxis":dict(**PLOT_LAYOUT["yaxis"],title="Frequency"),
            "showlegend":False,"plot_bgcolor":GREY_100})
        st.plotly_chart(fig2, use_container_width=True)

    with c2:
        section("Probability of Exceeding Threshold")
        ths=np.linspace(net_worth*0.3,net_worth*8,120)
        prbs=[(dp[:,-1]>=t).mean()*100 for t in ths]
        fig3=go.Figure()
        fig3.add_trace(go.Scatter(x=ths/1e6,y=prbs,
            line=dict(color=PRIMARY,width=2),
            fill="tozeroy",fillcolor=f"rgba(177,144,105,0.12)"))
        fig3.add_hline(y=50,line=dict(color=GREY_300,width=1,dash="dash"),
            annotation_text="50%",annotation_font_color=GREY_500)
        fig3.add_vline(x=st_["p50"]/1e6,line=dict(color=PRIMARY,width=1,dash="dot"),
            annotation_text="P50",annotation_font_color=PRIMARY)
        fig3.update_layout(**{**PLOT_LAYOUT,"height":300,"margin":dict(l=20,r=20,t=20,b=20),
            "xaxis":dict(**PLOT_LAYOUT["xaxis"],ticksuffix="M",title="Threshold (CHF M)"),
            "yaxis":dict(**PLOT_LAYOUT["yaxis"],ticksuffix="%",title="Probability"),
            "showlegend":False,"plot_bgcolor":GREY_100})
        st.plotly_chart(fig3, use_container_width=True)

# ─── Tab 2: Assumptions ──────────────────────────────────────────────
with t2:
    c1,c2=st.columns([1,1.2])

    with c1:
        section("Initial Allocation")
        ac_v=[bw[i]*100 for i in range(4)]
        fig_pie=go.Figure(go.Pie(
            labels=[BUCKET_LABELS[b] for b in BUCKETS],
            values=ac_v,
            marker=dict(colors=[BUCKET_COLORS[b] for b in BUCKETS],
                        line=dict(color=WHITE,width=2)),
            hole=0.48, textinfo="label+percent",
            textfont=dict(size=11,color=GREY_900),
        ))
        fig_pie.update_layout(paper_bgcolor=WHITE,showlegend=False,
            margin=dict(l=10,r=10,t=10,b=10),height=240,
            font=dict(family="DM Sans, sans-serif",color=GREY_700))
        st.plotly_chart(fig_pie, use_container_width=True)

        rows=""
        for i,b in enumerate(BUCKETS):
            rows+=f"<tr><td>{BUCKET_LABELS[b]}</td><td>{bw[i]*100:.1f}%</td><td>{fmt_chf(net_worth*bw[i])}</td></tr>"
        st.markdown(f"""
        <table class='wp-table'><thead><tr>
          <th>Asset Class</th><th>Weight</th><th>Value</th>
        </tr></thead><tbody>{rows}</tbody></table>""",unsafe_allow_html=True)

    with c2:
        section("Return & Volatility by Asset Class")
        mu_vals=[mu_cash,mu_lst,mu_priv,mu_re]
        sg_vals=[sig_cash,sig_lst,sig_priv,sig_re]
        sharpes=[(m-0.01)/s if s>0 else 0 for m,s in zip(mu_vals,sg_vals)]

        fig_bar=go.Figure()
        fig_bar.add_trace(go.Bar(name="μ Return",
            x=[BUCKET_LABELS[b] for b in BUCKETS],
            y=[v*100 for v in mu_vals],
            marker_color=[BUCKET_COLORS[b] for b in BUCKETS],opacity=0.9))
        fig_bar.add_trace(go.Bar(name="σ Volatility",
            x=[BUCKET_LABELS[b] for b in BUCKETS],
            y=[v*100 for v in sg_vals],
            marker_color=[BUCKET_COLORS[b] for b in BUCKETS],opacity=0.4))
        fig_bar.update_layout(**{**PLOT_LAYOUT,"height":240,"barmode":"group",
            "margin":dict(l=20,r=20,t=10,b=20),"showlegend":True,
            "xaxis":dict(gridcolor=WHITE),"yaxis":dict(gridcolor=WHITE,ticksuffix="%"),
            "plot_bgcolor":GREY_100,"paper_bgcolor":WHITE})
        st.plotly_chart(fig_bar, use_container_width=True)

        rows=""
        for i,b in enumerate(BUCKETS):
            rows+=f"<tr><td>{BUCKET_LABELS[b]}</td><td>{mu_vals[i]*100:.1f}%</td><td>{sg_vals[i]*100:.1f}%</td><td>{sharpes[i]:.2f}</td></tr>"
        st.markdown(f"""
        <table class='wp-table'><thead><tr>
          <th>Class</th><th>μ (%/yr)</th><th>σ (%/yr)</th><th>Sharpe</th>
        </tr></thead><tbody>{rows}</tbody></table>""",unsafe_allow_html=True)

    st.markdown("<hr class='wp-hr'/>",unsafe_allow_html=True)
    section("Portfolio-Level Metrics")
    wmu  = sum(mu_vals[i]*bw[i] for i in range(4))
    wvol = sum(sg_vals[i]*bw[i] for i in range(4))
    wsh  = (wmu-0.01)/wvol if wvol>0 else 0

    cols=st.columns(4)
    for col,(lbl,val) in zip(cols,[
        ("Weighted μ",       f"{wmu*100:.2f}%/yr"),
        ("Weighted σ",       f"{wvol*100:.2f}%/yr"),
        ("Portfolio Sharpe", f"{wsh:.2f}"),
        ("Inflation",        f"{inflation*100:.1f}%/yr"),
    ]):
        col.metric(lbl,val)

    st.markdown("<hr class='wp-hr'/>",unsafe_allow_html=True)
    section("Correlation Matrix (Fixed)")
    corr_df=pd.DataFrame(CORR,
        index=[BUCKET_LABELS[b] for b in BUCKETS],
        columns=[BUCKET_LABELS[b] for b in BUCKETS])
    fig_h=px.imshow(corr_df,text_auto=".2f",
        color_continuous_scale=[[0,PRIMARY_PALE],[0.5,PRIMARY_LIGHT],[1,PRIMARY]])
    fig_h.update_layout(paper_bgcolor=WHITE,plot_bgcolor=WHITE,
        font=dict(family="DM Sans, sans-serif",color=GREY_700,size=11),
        margin=dict(l=10,r=10,t=10,b=10),height=240,
        coloraxis_showscale=False)
    st.plotly_chart(fig_h, use_container_width=True)

# ─── Tab 3: Life Events ──────────────────────────────────────────────
with t3:
    section("Scheduled Life Events")
    evdata=[]
    for ev in st.session_state.wf_events:
        imp=event_total(ev,n_mo)
        evdata.append({"Name":ev.name,"Type":ev.type,"Starts":ev.start_date.strftime("%b %Y"),
                       "Ends":ev.end_date.strftime("%b %Y") if ev.end_date else "—",
                       "Freq":ev.frequency,"Amount (CHF)":f"{ev.amount:+,.0f}",
                       "Bucket":BUCKET_LABELS[ev.bucket],"Total Impact":f"{imp:+,.0f}"})
    st.dataframe(pd.DataFrame(evdata), hide_index=True, use_container_width=True)

    section("Monthly Net Cash Flow")
    mf  = build_monthly_events(st.session_state.wf_events, TODAY, n_mo)
    nf  = np.array([sum(m.values()) for m in mf])
    d_mo= [TODAY+relativedelta(months=i) for i in range(n_mo)]

    fig_fl=go.Figure()
    fig_fl.add_trace(go.Bar(x=d_mo,y=nf/1e3,
        marker_color=[GREEN_SOFT if v>=0 else RED_SOFT for v in nf],
        opacity=0.8))
    fig_fl.add_hline(y=0,line=dict(color=GREY_300,width=0.8))
    fig_fl.update_layout(**{**PLOT_LAYOUT,"height":250,"margin":dict(l=20,r=20,t=10,b=20),
        "showlegend":False,
        "yaxis":dict(gridcolor=WHITE,ticksuffix="k",title="CHF k"),
        "plot_bgcolor":GREY_100,"paper_bgcolor":WHITE})
    st.plotly_chart(fig_fl, use_container_width=True)

    st.markdown("<hr class='wp-hr'/>",unsafe_allow_html=True)
    section("Add Life Event")

    with st.form("wf_add_event",clear_on_submit=True):
        fc1,fc2,fc3=st.columns(3)
        with fc1:
            ev_name   = st.text_input("Event name",placeholder="e.g. Inheritance received")
            ev_type   = st.selectbox("Type",EVENT_TYPES)
            ev_bucket = st.selectbox("Bucket",BUCKETS,format_func=lambda x:BUCKET_LABELS[x])
        with fc2:
            ev_amount = st.number_input("Amount CHF (+ inflow / − outflow)",value=0,step=10_000)
            ev_freq   = st.selectbox("Frequency",["ONCE","MONTHLY","ANNUAL"])
            ev_start  = st.number_input("Start (in N years)",value=0,min_value=0,max_value=horizon_years)
        with fc3:
            ev_end    = st.number_input("End (in N years, 0 = one-off)",value=0,min_value=0,max_value=horizon_years)
        sub=st.form_submit_button("➕  Add Event",type="primary")
        if sub and ev_name:
            nid=f"ev{len(st.session_state.wf_events)+1}"
            end_dt=yr(ev_end) if ev_end>0 else None
            st.session_state.wf_events.append(
                WealthEvent(nid,ev_name,ev_type,yr(ev_start),end_dt,ev_freq,float(ev_amount),ev_bucket))
            st.rerun()

    if st.session_state.wf_events:
        del_name=st.selectbox("Remove event",["—"]+[e.name for e in st.session_state.wf_events])
        if del_name!="—":
            if st.button(f"🗑  Remove «{del_name}»"):
                st.session_state.wf_events=[e for e in st.session_state.wf_events if e.name!=del_name]
                st.rerun()

    if st.button("↺  Reset to defaults"):
        st.session_state.wf_events=copy.deepcopy(DEFAULT_EVENTS)
        st.rerun()

# ─── Tab 4: Report ───────────────────────────────────────────────────
with t4:
    section("Results Summary")
    cols=st.columns(4)
    for col,(lbl,val,sub) in zip(cols,[
        ("P50 — Base Case",    fmt_chf(st_["p50"]), f"×{st_['p50']/net_worth:.1f} initial"),
        ("P10 — Adverse",      fmt_chf(st_["p10"]), f"×{st_['p10']/net_worth:.1f} initial"),
        ("P90 — Favourable",   fmt_chf(st_["p90"]), f"×{st_['p90']/net_worth:.1f} initial"),
        ("P50 Real Terms",     fmt_chf(p50_real),   f"After {infl_total:.0f}% cumul. inflation"),
    ]):
        col.markdown(kpi_card(lbl,val,sub), unsafe_allow_html=True)

    st.markdown("<hr class='wp-hr'/>",unsafe_allow_html=True)
    section("Percentile Table by Year")
    step=2 if horizon_years<=20 else 5
    rows_pct=[]
    for y in range(0,horizon_years+1,step):
        mi=y*12
        if mi<len(pc["p50"]):
            rows_pct.append({"Year":(TODAY+relativedelta(years=y)).year,
                "P10":fmt_chf(pc["p10"][mi]),"P25":fmt_chf(pc["p25"][mi]),
                "P50":fmt_chf(pc["p50"][mi]),"P75":fmt_chf(pc["p75"][mi]),
                "P90":fmt_chf(pc["p90"][mi])})
    st.dataframe(pd.DataFrame(rows_pct), hide_index=True, use_container_width=True)

    st.markdown("<hr class='wp-hr'/>",unsafe_allow_html=True)
    section("Planner Observations")

    w_risky=bw[1]+bw[2]
    if w_risky>=0.75:   risk_profile="Aggressive (Growth)"
    elif w_risky>=0.55: risk_profile="Balanced"
    else:               risk_profile="Conservative"
    total_flows=sum(event_total(e,n_mo) for e in st.session_state.wf_events)
    prob_loss20=float((dp[:,-1]<net_worth*0.8).mean()*100)
    wmu=sum([mu_cash,mu_lst,mu_priv,mu_re][i]*bw[i] for i in range(4))

    obs=[
        ("Risk Profile",
         f"Your allocation is **{risk_profile}** with {w_risky*100:.0f}% in risk assets "
         f"(listed + private markets). Weighted expected return: **{wmu*100:.2f}%/yr**."),
        ("Trajectory",
         f"In the central scenario (P50), wealth grows from **{fmt_chf(net_worth)}** to "
         f"**{fmt_chf(st_['p50'])}** over {horizon_years} years — a **{st_['p50']/net_worth:.1f}× multiple**."),
        ("Inflation",
         f"At {inflation*100:.1f}%/yr over {horizon_years} years, cumulative inflation is "
         f"**{infl_total:.0f}%**. P50 in today's purchasing power: **{fmt_chf(p50_real)}**."),
        ("Life Events",
         f"Scheduled events produce a net flow of **{'+' if total_flows>=0 else ''}{fmt_chf(total_flows)}**. "
         f"{'This supports the growth trajectory.' if total_flows>=0 else 'Market returns must absorb this net outflow.'}"),
        ("Downside Risk",
         f"Probability of losing >20% of initial capital: **{prob_loss20:.1f}%**. "
         f"Probability of doubling: **{prob_double:.0f}%**."),
    ]
    for title,text in obs:
        with st.expander(f"○  {title}"):
            st.markdown(text)

    st.markdown("<hr class='wp-hr'/>",unsafe_allow_html=True)
    st.markdown("""
    <div class='wp-disclaimer'>
      <strong>Disclaimer</strong> — Projections are based on statistical assumptions and Monte Carlo simulations.
      They do not constitute a guarantee of future performance or investment advice.
      Financial markets are subject to risks that cannot be fully modelled.
      This output is for illustrative purposes only.
    </div>""", unsafe_allow_html=True)
