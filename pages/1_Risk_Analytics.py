"""
WealthPoint — Risk Analytics  (pages/1_Risk_Analytics.py)
Forward-looking portfolio risk from position snapshot + Yahoo Finance timeseries
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
from scipy import stats
from scipy.stats import t as student_t, norm
from datetime import datetime, timedelta
import warnings, sys, os
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="WealthPoint · Risk Analytics",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from wealthpoint_theme import (
    inject_global_css, sidebar_brand, sidebar_section,
    page_header, section, kpi_card, apply_mpl_style,
    PRIMARY, PRIMARY_DARK, PRIMARY_LIGHT, PRIMARY_PALE, PRIMARY_WASH,
    PRIMARY_MID,
    GREY_900, GREY_700, GREY_500, GREY_300, GREY_100, WHITE,
    RED_SOFT, RED_PALE, GREEN_SOFT, AMBER, AMBER_PALE,
    PALETTE_AC,
)

inject_global_css()
apply_mpl_style()

# ══════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════
EWMA_LAMBDA = 0.94
LIQUIDITY = {
    "VTI":1.0,"EWG":0.9,"EWJ":0.9,"EEM":0.85,
    "AGG":0.95,"TLT":0.95,"HYG":0.80,
    "GLD":0.95,"VNQ":0.85,"BTC-USD":0.70,
}
FACTOR_MAP = {"Equity":"VTI","Fixed Income":"AGG","Alternatives":"GLD"}
DURATION   = {"AGG":6.2,"TLT":16.5,"HYG":4.1}
SCENARIOS  = {
    "GFC 2008":         {"VTI":-0.45,"EWG":-0.48,"EWJ":-0.42,"EEM":-0.55,"AGG":0.06,"TLT":0.22,"HYG":-0.22,"GLD":0.05,"VNQ":-0.68,"BTC-USD":0.0},
    "Covid Crash 2020": {"VTI":-0.34,"EWG":-0.38,"EWJ":-0.31,"EEM":-0.32,"AGG":0.04,"TLT":0.19,"HYG":-0.21,"GLD":0.02,"VNQ":-0.42,"BTC-USD":-0.50},
    "Rate Shock 2022":  {"VTI":-0.19,"EWG":-0.16,"EWJ":-0.08,"EEM":-0.22,"AGG":-0.13,"TLT":-0.32,"HYG":-0.15,"GLD":-0.02,"VNQ":-0.30,"BTC-USD":-0.64},
    "Credit Crunch":    {"VTI":-0.14,"EWG":-0.12,"EWJ":-0.10,"EEM":-0.18,"AGG":-0.03,"TLT":0.05,"HYG":-0.20,"GLD":0.08,"VNQ":-0.15,"BTC-USD":-0.20},
    "Stagflation":      {"VTI":-0.18,"EWG":-0.14,"EWJ":-0.10,"EEM":-0.20,"AGG":-0.10,"TLT":-0.18,"HYG":-0.08,"GLD":0.20,"VNQ":-0.12,"BTC-USD":0.05},
    "Crypto Crash":     {"VTI":-0.08,"EWG":-0.05,"EWJ":-0.03,"EEM":-0.07,"AGG":-0.01,"TLT":0.02,"HYG":-0.04,"GLD":0.01,"VNQ":-0.06,"BTC-USD":-0.65},
    "CHF Dépeg 2015":   {"VTI":-0.02,"EWG":-0.09,"EWJ":-0.01,"EEM":-0.03,"AGG":0.01,"TLT":0.02,"HYG":-0.01,"GLD":0.03,"VNQ":-0.02,"BTC-USD":0.0},
}
DEFAULT_PORTFOLIO = [
    {"ticker":"VTI",    "name":"US Total Market",   "qty":150, "class":"Equity"},
    {"ticker":"EWG",    "name":"MSCI Germany",      "qty":200, "class":"Equity"},
    {"ticker":"EWJ",    "name":"MSCI Japan",        "qty":300, "class":"Equity"},
    {"ticker":"EEM",    "name":"MSCI EM",           "qty":120, "class":"Equity"},
    {"ticker":"AGG",    "name":"US Agg Bond",       "qty":100, "class":"Fixed Income"},
    {"ticker":"TLT",    "name":"20Y+ Treasury",     "qty": 80, "class":"Fixed Income"},
    {"ticker":"HYG",    "name":"High Yield Bond",   "qty": 90, "class":"Fixed Income"},
    {"ticker":"GLD",    "name":"Gold",              "qty": 60, "class":"Alternatives"},
    {"ticker":"VNQ",    "name":"REIT",              "qty":110, "class":"Alternatives"},
    {"ticker":"BTC-USD","name":"Bitcoin",           "qty":0.5, "class":"Alternatives"},
]

# ══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════
with st.sidebar:
    sidebar_brand("Risk Analytics")

    sidebar_section("Parameters")
    years_back   = st.slider("History (years)", 2, 7, 5)
    horizon_days = st.selectbox("Risk Horizon", [1,5,21,63], index=2,
                                format_func=lambda x:{1:"1 Day",5:"1 Week",21:"1 Month",63:"3 Months"}[x])
    conf_level   = st.selectbox("Confidence Level", [0.95,0.99],
                                format_func=lambda x:f"{x:.0%}")
    n_sim        = st.select_slider("MC Simulations", [1000,5000,10000], value=5000)
    vol_method   = st.selectbox("Volatility Model", ["Historical","EWMA (λ=0.94)","GARCH(1,1)"])

    sidebar_section("Portfolio Positions")
    ptf_input = []
    for p in DEFAULT_PORTFOLIO:
        c1, c2 = st.columns([3,2])
        with c1:
            st.markdown(f"<div style='font-size:0.78rem;color:{GREY_700};padding-top:0.5rem;'>{p['ticker']}</div>",
                        unsafe_allow_html=True)
        with c2:
            qty = st.number_input("", value=float(p["qty"]), key=f"ra_qty_{p['ticker']}",
                                  label_visibility="collapsed", step=1.0)
        ptf_input.append({**p,"qty":qty})

    st.markdown(f"<hr style='border:none;border-top:1px solid {PRIMARY_PALE};margin:1rem 0;'/>",
                unsafe_allow_html=True)
    run_btn = st.button("▶  Run Analysis", use_container_width=True)

# ══════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════

st.title(" ")
page_header(
    "Risk Analytics",
    f"Forward-Looking · Position Snapshot · {datetime.today().strftime('%d %B %Y')}",
    badge="Module 01"
)

# ══════════════════════════════════════════════════════════════════════
# CACHED FUNCTIONS
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def load_prices(tickers, yrs):
    end   = datetime.today()
    start = end - timedelta(days=365*yrs)
    raw   = yf.download(list(tickers), start=start, end=end,
                        auto_adjust=True, progress=False)["Close"]
    if isinstance(raw, pd.Series):
        raw = raw.to_frame(tickers[0])
    eq_idx = raw[[t for t in tickers if t!="BTC-USD"]].dropna(how="all").index
    if "BTC-USD" in raw.columns:
        btc = raw["BTC-USD"].reindex(eq_idx).ffill()
        raw = raw.reindex(eq_idx); raw["BTC-USD"] = btc
    return raw.ffill()

@st.cache_data(show_spinner=False)
def run_risk(ptf_rows, yrs, horizon, conf, n_sim, vol_str):
    tickers = [p["ticker"] for p in ptf_rows]
    prices  = load_prices(tuple(tickers), yrs)
    latest  = prices.iloc[-1]

    ptf = pd.DataFrame(ptf_rows)
    ptf["price"]    = ptf["ticker"].map(latest)
    ptf["mv"]       = ptf["qty"]*ptf["price"]
    total           = ptf["mv"].sum()
    ptf["weight"]   = ptf["mv"]/total
    ptf["liq"]      = ptf["ticker"].map(LIQUIDITY).fillna(0.85)

    log_ret = np.log(prices/prices.shift(1)).dropna()
    weights = ptf.set_index("ticker")["weight"].reindex(log_ret.columns).fillna(0)
    ptf_ret = (log_ret*weights.values).sum(axis=1)

    # Idiosyncratic vol + beta
    idio, betas = {}, {}
    for _, row in ptf.iterrows():
        tk  = row["ticker"]
        fac = FACTOR_MAP.get(row["class"])
        if not fac or fac==tk or fac not in log_ret.columns:
            idio[tk]=0.0; betas[tk]=1.0; continue
        y=log_ret[tk].dropna(); x=log_ret[fac].reindex(y.index).dropna()
        com=y.index.intersection(x.index)
        if len(com)<60: idio[tk]=0.0; betas[tk]=1.0; continue
        b,a,_,_,_=stats.linregress(x[com],y[com])
        betas[tk]=b; idio[tk]=(y[com]-(a+b*x[com])).std()*np.sqrt(252)
    ptf["beta"]=ptf["ticker"].map(betas); ptf["idio_vol"]=ptf["ticker"].map(idio)

    # Conditional volatility
    def ewma_fn(r, lam=EWMA_LAMBDA):
        v=r.var()
        for ri in r: v=lam*v+(1-lam)*ri**2
        return np.sqrt(v)

    cond_vols={}
    for tk in log_ret.columns:
        r=log_ret[tk].dropna().values[-252:]
        ew=ewma_fn(r)
        try:
            from arch import arch_model
            am=arch_model(r*100,vol="Garch",p=1,q=1,dist="StudentsT",rescale=False)
            res=am.fit(disp="off",options={"maxiter":150})
            fc=res.forecast(horizon=horizon,reindex=False)
            ga=np.sqrt(fc.variance.values[-1,-1])/100
        except: ga=ew
        cond_vols[tk]={"hist":r.std(),"ewma":ew,"garch":ga}

    vk={"Historical":"hist","EWMA (λ=0.94)":"ewma","GARCH(1,1)":"garch"}[vol_str]

    # Historical VaR/CVaR
    def hvc(ret,cl,hz):
        rs=ret*np.sqrt(hz)
        v=np.percentile(rs,(1-cl)*100)
        return v,rs[rs<=v].mean()

    var95,cvar95=hvc(ptf_ret,conf,horizon)
    var99,cvar99=hvc(ptf_ret,0.99,horizon)

    # Correlation regimes
    wkly  = log_ret.resample("W").sum()
    pw    = (wkly*weights.reindex(wkly.columns).fillna(0).values).sum(axis=1)
    thr   = pw.quantile(0.10)
    cw    = pw[pw<=thr].index
    cd    = log_ret.index[pd.to_datetime(log_ret.index).to_period("W").to_timestamp("W").isin(cw)]
    nd    = log_ret.index.difference(cd)
    corr_n = log_ret.loc[nd].corr() if len(nd)>10 else log_ret.corr()
    corr_c = log_ret.loc[cd].corr() if len(cd)>10 else log_ret.corr()

    # Student-t MC
    def stmc(corr_mat, vkey, ns, df_t):
        tks=log_ret.columns.tolist()
        w=weights.reindex(tks).fillna(0).values
        mu=log_ret.mean().values
        vs=np.array([cond_vols[tk][vkey] for tk in tks])
        c=corr_mat.reindex(tks,axis=0).reindex(tks,axis=1).fillna(0).values
        np.fill_diagonal(c,1.0)
        ev=np.linalg.eigvalsh(c)
        if ev.min()<1e-8: c+=(-ev.min()+1e-6)*np.eye(len(tks))
        L=np.linalg.cholesky(c); np.random.seed(42); cr=np.zeros(ns)
        for _ in range(horizon):
            u=np.random.standard_t(df=df_t,size=(ns,len(tks)))
            u/=np.sqrt(df_t/(df_t-2))
            cr+=(mu+(u@L.T)*vs)@w
        return cr

    mc_n=stmc(corr_n,vk,n_sim,5); mc_c=stmc(corr_c,vk,n_sim,4)
    def mcvc(s,cl): v=np.percentile(s,(1-cl)*100); return v,s[s<=v].mean()
    mc_n_v,mc_n_c=mcvc(mc_n,conf); mc_c_v,mc_c_c=mcvc(mc_c,conf)

    # Risk contribution
    cov_a=log_ret.cov()*252; wa=weights.values
    pva=wa@cov_a.values@wa; mrc=(cov_a.values@wa)/np.sqrt(pva)
    ptf["rc"]=(wa*mrc)/((wa*mrc).sum())
    ann_vol=np.sqrt(pva); ann_ret=ptf_ret.mean()*252
    sharpe=(ann_ret-0.045)/ann_vol
    max_dd=((ptf_ret+1).cumprod()/(ptf_ret+1).cumprod().cummax()-1).min()

    # LaVaR
    def bsp(s): return 0.0002 if s>=0.95 else 0.0005 if s>=0.85 else 0.0015
    liq_n=sum(r["weight"]*bsp(r["liq"]) for _,r in ptf.iterrows())
    lavar_n=-(abs(var95)+liq_n); lavar_c=-(abs(var95)+liq_n*3)

    # VaR bands
    var_bands={}
    for wy in [1,2,3,5]:
        nb=int(wy*252)
        if nb>len(ptf_ret): continue
        v,c=hvc(ptf_ret.iloc[-nb:],conf,horizon)
        var_bands[f"{wy}y"]={"VaR":v,"CVaR":c}

    # Weight drift
    px=prices[list(weights.index)].ffill().dropna()
    nav=(px/px.iloc[0])*weights.reindex(list(weights.index)).fillna(0).values
    w_drift=nav.div(nav.sum(axis=1),axis=0)

    return dict(
        ptf=ptf,total=total,log_ret=log_ret,weights=weights,ptf_ret=ptf_ret,
        var95=var95,cvar95=cvar95,var99=var99,cvar99=cvar99,
        ann_vol=ann_vol,ann_ret=ann_ret,sharpe=sharpe,max_dd=max_dd,
        mc_n=mc_n,mc_c=mc_c,mc_n_v=mc_n_v,mc_n_c=mc_n_c,mc_c_v=mc_c_v,mc_c_c=mc_c_c,
        corr_n=corr_n,corr_c=corr_c,corr_diff=corr_c-corr_n,
        lavar_n=lavar_n,lavar_c=lavar_c,var_bands=var_bands,w_drift=w_drift,
        cond_vols=cond_vols,vk=vk,n_crisis=len(cd),
        ptf_vol_hist=ptf_ret.std()*np.sqrt(horizon),
    )

def scenarios_df(ptf_df, total):
    rows=[]
    for sc,shocks in SCENARIOS.items():
        pnl=sum(r["weight"]*shocks.get(r["ticker"],0) for _,r in ptf_df.iterrows())
        eq =sum(r["weight"]*shocks.get(r["ticker"],0) for _,r in ptf_df.iterrows() if r["class"]=="Equity")
        fi =sum(r["weight"]*shocks.get(r["ticker"],0) for _,r in ptf_df.iterrows() if r["class"]=="Fixed Income")
        al =sum(r["weight"]*shocks.get(r["ticker"],0) for _,r in ptf_df.iterrows() if r["class"]=="Alternatives")
        rows.append({"Scenario":sc,"P&L %":pnl,"P&L $":pnl*total,"Equity":eq,"Fixed Income":fi,"Alternatives":al})
    return pd.DataFrame(rows).sort_values("P&L %")

# ══════════════════════════════════════════════════════════════════════
# LANDING STATE
# ══════════════════════════════════════════════════════════════════════
if not run_btn:
    st.markdown(f"""
    <div style='text-align:center;padding:5rem 2rem;'>
      <div style='font-family:Cormorant Garamond,serif;font-size:4rem;
                  font-weight:300;color:{PRIMARY_LIGHT};line-height:1;'>◈</div>
      <div style='font-size:0.83rem;color:{GREY_500};max-width:380px;margin:1.2rem auto 0;
                  line-height:1.8;letter-spacing:0.03em;'>
        Set quantities in the sidebar and click
        <strong style='color:{PRIMARY_DARK};'>Run Analysis</strong>
        to compute the risk dashboard.
      </div>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════════════
with st.spinner("Fetching market data & running risk models…"):
    R  = run_risk(
        tuple(dict(ticker=p["ticker"],name=p["name"],qty=p["qty"],**{"class":p["class"]})
              for p in ptf_input),
        years_back, horizon_days, float(conf_level), n_sim, vol_method
    )

ptf       = R["ptf"]
total     = R["total"]
sc        = scenarios_df(ptf, total)
hz_lbl    = {1:"1 Day",5:"1 Week",21:"1 Month",63:"3 Months"}[horizon_days]

# ══════════════════════════════════════════════════════════════════════
# KPI ROW
# ══════════════════════════════════════════════════════════════════════
cols = st.columns(6)
kpis = [
    ("Total Value",                f"${total:,.0f}",                   "",                                 False,False),
    (f"VaR {conf_level:.0%} · {hz_lbl}", f"{R['var95']:.1%}",         f"${R['var95']*total:,.0f}",        True, False),
    (f"CVaR {conf_level:.0%} · {hz_lbl}",f"{R['cvar95']:.1%}",        f"${R['cvar95']*total:,.0f}",       True, False),
    ("Ann. Volatility",            f"{R['ann_vol']:.1%}",              f"1M hist: {R['ptf_vol_hist']:.1%}",False,False),
    ("Sharpe Ratio",               f"{R['sharpe']:.2f}",               "vs 4.5% risk-free",                R['sharpe']<1,R['sharpe']>=1),
    ("LaVaR (crisis liq.)",        f"{R['lavar_c']:.1%}",              "Liquidity-adjusted",               True, False),
]
for col,(lbl,val,sub,neg,pos) in zip(cols,kpis):
    col.markdown(kpi_card(lbl,val,sub,neg,pos), unsafe_allow_html=True)

# regime badges
var_rng_min = min(v["VaR"] for v in R["var_bands"].values())
var_rng_max = max(v["VaR"] for v in R["var_bands"].values())
st.markdown(f"""
<div style='display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:0.8rem;'>
  <span class='wp-badge badge-n'>Normal regime VaR: {R['mc_n_v']:.1%}</span>
  <span class='wp-badge badge-c'>Crisis regime VaR: {R['mc_c_v']:.1%}</span>
  <span class='wp-badge badge-w'>Estimation range: [{var_rng_min:.1%}, {var_rng_max:.1%}]</span>
</div>""", unsafe_allow_html=True)

st.markdown("<hr class='wp-hr'/>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════
t1,t2,t3,t4,t5 = st.tabs([
    "Portfolio Overview","Risk Metrics","Stress Scenarios","Monte Carlo","Correlations & Drift"
])

# ─── Tab 1: Portfolio Overview ───────────────────────────────────────
with t1:
    section("Holdings & Allocation")
    c1,c2 = st.columns([1.1,1.9])

    with c1:
        fig,ax=plt.subplots(figsize=(4,3.6))
        ac_mv=ptf.groupby("class")["mv"].sum()
        wc=[PALETTE_AC.get(a,PRIMARY) for a in ac_mv.index]
        _,_,autos=ax.pie(ac_mv,labels=None,autopct="%1.1f%%",colors=wc,startangle=90,
                         pctdistance=0.74,wedgeprops={"linewidth":1.5,"edgecolor":WHITE})
        for at in autos: at.set_color(WHITE);at.set_fontsize(8);at.set_fontweight("bold")
        ax.legend(ac_mv.index,loc="lower center",ncol=3,bbox_to_anchor=(0.5,-0.06),
                  fontsize=7.5,handlelength=1.2)
        ax.set_title("Asset Class Allocation",pad=10)
        plt.tight_layout(); st.pyplot(fig,use_container_width=True); plt.close()

    with c2:
        rows=""
        for _,row in ptf.sort_values("mv",ascending=False).iterrows():
            ac_col=PALETTE_AC.get(row["class"],PRIMARY)
            dot=f"<span style='color:{ac_col};'>●</span>"
            rows+=f"""<tr>
              <td>{dot} {row['ticker']}</td>
              <td style='text-align:left;font-size:0.74rem;color:{GREY_500};'>{row['name']}</td>
              <td>{row['class']}</td>
              <td>${row['mv']:,.0f}</td>
              <td>{row['weight']:.1%}</td>
              <td>{row['rc']:.1%}</td>
              <td>{row['idio_vol']:.1%}</td>
              <td>{row['beta']:.2f}</td>
            </tr>"""
        st.markdown(f"""
        <table class='wp-table'><thead><tr>
          <th>Ticker</th><th style='text-align:left'>Name</th><th>Class</th>
          <th>Mkt Value</th><th>Weight</th><th>Risk Contrib</th>
          <th>Idio. Vol</th><th>Beta</th>
        </tr></thead><tbody>{rows}</tbody></table>""", unsafe_allow_html=True)

    section("Weight vs Risk Contribution")
    fig,ax=plt.subplots(figsize=(12,3))
    x=np.arange(len(ptf))
    ax.bar(x-0.22,ptf["weight"],0.4,label="Weight",color=PRIMARY_PALE,edgecolor=PRIMARY_LIGHT,lw=0.8)
    ax.bar(x+0.22,ptf["rc"],   0.4,label="Risk Contribution",color=PRIMARY,edgecolor=PRIMARY_DARK,lw=0.8,alpha=0.85)
    ax.set_xticks(x); ax.set_xticklabels(ptf["ticker"],rotation=30,ha="right")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1,decimals=0))
    ax.legend(); ax.set_ylabel("(%)")
    ax.set_title("Divergence between weight and risk contribution → concentration risk")
    plt.tight_layout(); st.pyplot(fig,use_container_width=True); plt.close()

# ─── Tab 2: Risk Metrics ─────────────────────────────────────────────
with t2:
    c1,c2=st.columns(2)
    with c1:
        section("Return Distribution")
        fig,ax=plt.subplots(figsize=(6,4))
        ax.hist(R["ptf_ret"]*100,bins=80,density=True,alpha=0.55,
                color=PRIMARY_PALE,edgecolor=PRIMARY_LIGHT,lw=0.5,label="Daily Returns")
        mu_r=R["ptf_ret"].mean()*100; sd_r=R["ptf_ret"].std()*100
        xs=np.linspace(mu_r-4.5*sd_r,mu_r+4.5*sd_r,300)
        ax.plot(xs,norm.pdf(xs,mu_r,sd_r),color=GREY_300,lw=1.2,ls="--",label="Normal")
        df_f,loc_f,sc_f=student_t.fit(R["ptf_ret"]*100)
        ax.plot(xs,student_t.pdf(xs,df_f,loc_f,sc_f),color=PRIMARY,lw=2,
                label=f"Student-t (df={df_f:.1f})")
        v1d=R["var95"]/np.sqrt(horizon_days)*100
        ax.axvline(v1d,color=RED_SOFT,lw=1.8,ls="--",label=f"VaR {conf_level:.0%} 1d: {v1d:.2f}%")
        ax.axvline(R["cvar95"]/np.sqrt(horizon_days)*100,color=RED_SOFT,lw=1.8,ls=":")
        ax.legend(fontsize=7.5); ax.set_xlabel("Daily Return (%)")
        ax.set_title("Fat tails: Student-t vs Normal")
        plt.tight_layout(); st.pyplot(fig,use_container_width=True); plt.close()

    with c2:
        section("VaR Estimation Bands")
        fig,ax=plt.subplots(figsize=(6,4))
        bands=R["var_bands"]; xl=list(bands.keys())
        vv=[-bands[w]["VaR"]*100 for w in xl]
        cv=[-bands[w]["CVaR"]*100 for w in xl]
        x=np.arange(len(xl))
        ax.bar(x-0.2,vv,0.38,color=PRIMARY_PALE,edgecolor=PRIMARY_LIGHT,lw=0.8,label=f"VaR {conf_level:.0%}")
        ax.bar(x+0.2,cv,0.38,color=PRIMARY,edgecolor=PRIMARY_DARK,lw=0.8,alpha=0.85,label=f"CVaR {conf_level:.0%}")
        ax.set_xticks(x); ax.set_xticklabels(xl)
        ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.1f%%"))
        ax.legend(); ax.set_ylabel("Risk estimate (%)")
        ax.set_title(f"Model uncertainty by estimation window · {hz_lbl}")
        plt.tight_layout(); st.pyplot(fig,use_container_width=True); plt.close()

    section("Risk Metrics Summary")
    r95=mc_results_95=(R["mc_n_v"],R["mc_n_c"],R["mc_c_v"],R["mc_c_c"])
    rows=""
    metrics=[
        ("Horizon",         hz_lbl,                                      "—","—"),
        (f"VaR {conf_level:.0%}",  f"{R['var95']:.2%} (${R['var95']*total:,.0f})",  f"{R['mc_n_v']:.2%}", f"{R['mc_c_v']:.2%}"),
        (f"CVaR {conf_level:.0%}", f"{R['cvar95']:.2%} (${R['cvar95']*total:,.0f})",f"{R['mc_n_c']:.2%}", f"{R['mc_c_c']:.2%}"),
        ("LaVaR (normal)",  f"{R['lavar_n']:.2%}",                       "—","—"),
        ("LaVaR (crisis)",  f"{R['lavar_c']:.2%}",                       "—","—"),
        ("Ann. Volatility", f"{R['ann_vol']:.2%}",                       "—","—"),
        ("Sharpe Ratio",    f"{R['sharpe']:.2f}",                        "—","—"),
        ("Max Drawdown*",   f"{R['max_dd']:.2%}",                        "—","—"),
        ("Vol Model",       vol_method,                                   "—","—"),
    ]
    for m in metrics:
        nc="td-neg" if any(x in m[0] for x in ["VaR","CVaR","LaVaR","DD"]) else ""
        rows+=f"<tr><td>{m[0]}</td><td class='{nc}'>{m[1]}</td><td class='{nc}'>{m[2]}</td><td class='td-neg'>{m[3]}</td></tr>"
    st.markdown(f"""
    <table class='wp-table'><thead><tr>
      <th>Metric</th><th>Historical</th><th>MC Normal</th><th>MC Crisis</th>
    </tr></thead><tbody>{rows}</tbody></table>
    <div style='font-size:0.7rem;color:{GREY_500};margin-top:0.4rem;'>
    * Drawdown on instrument-weighted returns — not true portfolio (no transaction history).
    </div>""", unsafe_allow_html=True)

# ─── Tab 3: Stress Scenarios ─────────────────────────────────────────
with t3:
    section("Scenario Impact — Instrument-Level Shocks")
    idio_unc=sum(
        ptf.set_index("ticker").loc[tk,"idio_vol"]*abs(R["weights"][tk])
        for tk in R["weights"].index if tk in ptf.set_index("ticker").index
    )*np.sqrt(horizon_days)

    fig,ax=plt.subplots(figsize=(13,5))
    sc_names=sc["Scenario"].tolist(); sc_pcts=sc["P&L %"].tolist(); x=np.arange(len(sc_names))
    bc=[RED_SOFT if p<0 else GREEN_SOFT for p in sc_pcts]
    bars=ax.bar(x,[p*100 for p in sc_pcts],color=bc,alpha=0.80,width=0.55)
    for bar,pct in zip(bars,sc_pcts):
        ax.errorbar(bar.get_x()+bar.get_width()/2,pct*100,
                    yerr=idio_unc*100,fmt="none",color=GREY_500,capsize=4,lw=1,alpha=0.7)
        off=1.5 if pct>=0 else -2.5
        ax.text(bar.get_x()+bar.get_width()/2,pct*100+off,f"{pct:+.1f}%",
                ha="center",fontsize=8.5,fontweight="bold",color=GREY_900)
    ax.axhline(0,color=GREY_300,lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(sc_names,rotation=15,ha="right")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0)); ax.set_ylabel("Estimated P&L (%)")
    ax.set_title(f"Stress scenarios applied to current snapshot  ·  Error bars = ±Idiosyncratic vol ({idio_unc:.1%})")
    plt.tight_layout(); st.pyplot(fig,use_container_width=True); plt.close()

    section("Asset Class Decomposition")
    fig,ax=plt.subplots(figsize=(13,4))
    for i,(ac,col) in enumerate(PALETTE_AC.items()):
        vals=sc[ac].tolist()
        ax.bar(x+(i-1)*0.25,[v*100 for v in vals],0.25,label=ac,color=col,alpha=0.82,
               edgecolor=WHITE,lw=0.5)
    ax.axhline(0,color=GREY_300,lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(sc_names,rotation=15,ha="right")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_ylabel("Contribution (%)"); ax.legend(title="Asset Class",title_fontsize=7.5)
    ax.set_title("Per-asset-class P&L contribution per scenario")
    plt.tight_layout(); st.pyplot(fig,use_container_width=True); plt.close()

    section("Scenario Detail")
    rows=""
    for _,row in sc.iterrows():
        nc="td-neg" if row["P&L %"]<0 else "td-pos"
        rows+=f"""<tr>
          <td>{row['Scenario']}</td>
          <td class='{nc}'>{row['P&L %']:+.2%}</td>
          <td class='{nc}'>${row['P&L $']:+,.0f}</td>
          <td class='td-neg'>{row['Equity']:+.2%}</td>
          <td class='td-neg'>{row['Fixed Income']:+.2%}</td>
          <td class='td-neg'>{row['Alternatives']:+.2%}</td>
        </tr>"""
    st.markdown(f"""
    <table class='wp-table'><thead><tr>
      <th>Scenario</th><th>Total P&L</th><th>P&L ($)</th>
      <th>Equity</th><th>Fixed Income</th><th>Alternatives</th>
    </tr></thead><tbody>{rows}</tbody></table>""",unsafe_allow_html=True)

# ─── Tab 4: Monte Carlo ──────────────────────────────────────────────
with t4:
    c1,c2=st.columns(2)
    with c1:
        section("Return Distribution — Normal vs Crisis")
        fig,ax=plt.subplots(figsize=(6.5,4.5))
        ax.hist(R["mc_n"]*100,bins=100,density=True,alpha=0.5,
                color=PRIMARY_PALE,edgecolor=PRIMARY_LIGHT,lw=0.3,label="Normal regime")
        ax.hist(R["mc_c"]*100,bins=100,density=True,alpha=0.5,
                color=PRIMARY,edgecolor=PRIMARY_DARK,lw=0.3,label="Crisis regime")
        ax.axvline(R["mc_n_v"]*100,color=PRIMARY_DARK,lw=2,ls="--",
                   label=f"Normal VaR {conf_level:.0%}: {R['mc_n_v']:.1%}")
        ax.axvline(R["mc_c_v"]*100,color=RED_SOFT,lw=2,ls="--",
                   label=f"Crisis VaR {conf_level:.0%}: {R['mc_c_v']:.1%}")
        ax.legend(fontsize=7.5); ax.set_xlabel(f"Portfolio Return ({hz_lbl}, %)")
        ax.set_title(f"Student-t MC · {n_sim:,} paths · {hz_lbl}\n{vol_method} conditional vol")
        plt.tight_layout(); st.pyplot(fig,use_container_width=True); plt.close()

    with c2:
        section("Percentile Fan")
        pcs=[1,5,10,25,50,75,90,95,99]
        nv=[np.percentile(R["mc_n"]*100,p) for p in pcs]
        cv=[np.percentile(R["mc_c"]*100,p) for p in pcs]
        fig,ax=plt.subplots(figsize=(6.5,4.5))
        ax.plot(pcs,nv,"o-",color=PRIMARY,lw=2,ms=5,label="Normal regime")
        ax.plot(pcs,cv,"s-",color=RED_SOFT,lw=2,ms=5,label="Crisis regime")
        ax.fill_between(pcs,nv,cv,alpha=0.1,color=RED_SOFT)
        ax.axhline(0,color=GREY_300,lw=0.8); ax.axvline(5,color=GREY_100,lw=0.8,ls=":")
        ax.set_xlabel("Percentile"); ax.set_ylabel(f"Return ({hz_lbl}, %)")
        ax.legend(); ax.set_title("Return percentile fan — gap = crisis premium")
        plt.tight_layout(); st.pyplot(fig,use_container_width=True); plt.close()

    section("Conditional Volatility by Instrument")
    vk=R["vk"]; rows=""
    for _,row in ptf.iterrows():
        tk=row["ticker"]; cv=R["cond_vols"].get(tk,{})
        rows+=f"""<tr>
          <td>{tk}</td><td>{row['class']}</td>
          <td>{cv.get('hist',0)*np.sqrt(252)*100:.1f}%</td>
          <td>{cv.get('ewma',0)*np.sqrt(252)*100:.1f}%</td>
          <td>{cv.get('garch',0)*np.sqrt(252)*100:.1f}%</td>
          <td style='color:{PRIMARY_DARK};font-weight:500;'>{cv.get(vk,0)*np.sqrt(252)*100:.1f}%</td>
        </tr>"""
    st.markdown(f"""
    <table class='wp-table'><thead><tr>
      <th>Ticker</th><th>Class</th><th>Hist (Ann.)</th>
      <th>EWMA (Ann.)</th><th>GARCH (Ann.)</th><th>Active</th>
    </tr></thead><tbody>{rows}</tbody></table>""",unsafe_allow_html=True)

# ─── Tab 5: Correlations & Drift ─────────────────────────────────────
with t5:
    c1,c2=st.columns(2)

    def corr_heatmap(corr_data, title, cmap_name="custom"):
        fig,ax=plt.subplots(figsize=(6,5))
        import matplotlib.colors as mcolors
        if cmap_name=="diff":
            cmap=sns.blend_palette([PRIMARY_LIGHT,WHITE,RED_SOFT],as_cmap=True)
            sns.heatmap(corr_data,ax=ax,mask=np.triu(np.ones_like(corr_data,dtype=bool),k=1),
                        cmap=cmap,center=0,vmin=-0.5,vmax=0.5,annot=True,fmt=".2f",
                        annot_kws={"size":7},linewidths=0.3,linecolor=GREY_100,
                        cbar_kws={"shrink":0.7})
        else:
            cmap=sns.blend_palette([RED_SOFT,WHITE,PRIMARY],as_cmap=True)
            sns.heatmap(corr_data,ax=ax,mask=np.triu(np.ones_like(corr_data,dtype=bool),k=1),
                        cmap=cmap,center=0,vmin=-1,vmax=1,annot=True,fmt=".2f",
                        annot_kws={"size":7},linewidths=0.3,linecolor=GREY_100,
                        cbar_kws={"shrink":0.7})
        ax.set_title(title); ax.tick_params(labelsize=7.5)
        plt.tight_layout(); st.pyplot(fig,use_container_width=True); plt.close()

    with c1:
        section("Normal Regime Correlations")
        corr_heatmap(R["corr_n"],"Normal regime")
    with c2:
        section(f"Δ Crisis − Normal  ({R['n_crisis']:.0f} crisis days)")
        corr_heatmap(R["corr_diff"],"Red = correlation spikes in crisis","diff")

    section("Weight Drift — No Rebalancing")
    drift=R["w_drift"]
    palette=sns.blend_palette([PRIMARY_PALE,PRIMARY,PRIMARY_DARK,
                                GREY_300,GREY_500,GREY_700,
                                "#CDB898","#8C7050","#E8DDD0","#4A3728"],n_colors=len(drift.columns))
    fig,ax=plt.subplots(figsize=(13,3.8))
    for i,tk in enumerate(drift.columns):
        ax.plot(drift.index,drift[tk]*100,lw=1.5,color=palette[i],label=tk)
    ax.set_ylabel("Weight (%)"); ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.0f%%"))
    ax.legend(ncol=5,fontsize=7.5,loc="upper center",bbox_to_anchor=(0.5,1.18))
    ax.set_title("Portfolio weight drift assuming no rebalancing")
    plt.tight_layout(); st.pyplot(fig,use_container_width=True); plt.close()

# ── Disclaimer ────────────────────────────────────────────────────────
st.markdown("<hr class='wp-hr'/>",unsafe_allow_html=True)
st.markdown("""
<div class='wp-disclaimer'>
  <strong>Disclaimer</strong> — All risk estimates are indicative and forward-looking based on the current position
  snapshot and historical price data. Results are not a backtest of actual portfolio performance.
  Figures depend materially on the estimation window, proxy mapping, volatility model, and correlation
  assumptions. Scenarios are hypothetical shocks applied to today's portfolio — not predictions.
  This output does not constitute investment advice.
</div>""", unsafe_allow_html=True)
