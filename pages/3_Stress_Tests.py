# =============================================================================
# WealthPoint — Module 03 · Stress Tests Historiques V2
# Faithful Streamlit port of Colab V2 with WealthPoint design system
#
#  🔴 [1] Proxy substitution explicite par ticker
#  🔴 [2] Score de confiance par scénario
#  🔴 [3] Re-pricing obligataire duration-based
#  🟡 [4] FX decomposition (chocs change par devise × scénario)
#  🟡 [5] Haircut diversification sur peak-to-trough
#  🟡 [6] Bootstrap confidence bands P10/P90
#  🟡 [7] 9 scénarios (EU Sovereign, Crypto Winter, Inflation custom)
#  🟢 [8] Factor-based re-pricing Approche B
#  🟢 [9] Private assets proxy + haircut illiquidité
# =============================================================================

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import seaborn as sns
import warnings, sys, os, copy
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="WealthPoint · Stress Tests",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from wealthpoint_theme import (
    inject_global_css, sidebar_brand, sidebar_section,
    page_header, section, kpi_card, apply_mpl_style,
    PRIMARY, PRIMARY_DARK, PRIMARY_LIGHT, PRIMARY_PALE, PRIMARY_WASH, PRIMARY_MID,
    GREY_900, GREY_700, GREY_500, GREY_300, GREY_100, WHITE,
    RED_SOFT, GREEN_SOFT, AMBER, AMBER_PALE,
)

inject_global_css()
apply_mpl_style()

AC_COLOR = {"Equity": PRIMARY, "Bond": GREEN_SOFT, "Alternative": AMBER, "Private": "#7C3AED"}
SRC_COLOR = {"direct": GREEN_SOFT, "proxy": AMBER, "duration": PRIMARY_LIGHT,
             "factor": "#7C3AED", "blend": PRIMARY_MID, "missing": RED_SOFT}
CONF_SCORES = {"high": 1.0, "medium": 0.6, "low": 0.25}

# =============================================================================
# DEFAULT PORTFOLIO
# =============================================================================
DEFAULT_PTF = [
    dict(ticker="SPY",     name="S&P 500 ETF",               ac="Equity",      w=0.22,
         fx="USD", fp="us_large_blend",    proxy=None,  dur=None, sdur=None, cbkt=None, bccy=None, ilhc=0.00),
    dict(ticker="QQQ",     name="NASDAQ 100 ETF",             ac="Equity",      w=0.09,
         fx="USD", fp="us_large_growth",   proxy=None,  dur=None, sdur=None, cbkt=None, bccy=None, ilhc=0.00),
    dict(ticker="EFA",     name="MSCI EAFE (EUR/JPY)",        ac="Equity",      w=0.10,
         fx="EUR", fp="intl_large_blend",  proxy=None,  dur=None, sdur=None, cbkt=None, bccy=None, ilhc=0.00),
    dict(ticker="EEM",     name="MSCI EM ETF",                ac="Equity",      w=0.05,
         fx="USD", fp="em_blend",          proxy=None,  dur=None, sdur=None, cbkt=None, bccy=None, ilhc=0.00),
    dict(ticker="AGG",     name="US Agg Bond ETF",            ac="Bond",        w=0.10,
         fx="USD", fp="bond_ig_usd",       proxy="AGG", dur=6.2,  sdur=5.5,  cbkt="IG",       bccy="USD", ilhc=0.00),
    dict(ticker="TLT",     name="US 20Y+ Treasury ETF",       ac="Bond",        w=0.10,
         fx="USD", fp="bond_sovereign_usd",proxy="TLT", dur=17.5, sdur=0.0,  cbkt="Sovereign",bccy="USD", ilhc=0.00),
    dict(ticker="LQD",     name="US IG Corp Bond ETF",        ac="Bond",        w=0.08,
         fx="USD", fp="bond_ig_usd",       proxy="LQD", dur=8.7,  sdur=8.2,  cbkt="IG",       bccy="USD", ilhc=0.00),
    dict(ticker="GLD",     name="Gold ETF (SPDR)",            ac="Alternative", w=0.07,
         fx="USD", fp="gold",              proxy=None,  dur=None, sdur=None, cbkt=None, bccy=None, ilhc=0.00),
    dict(ticker="DJP",     name="Broad Commodities ETN",      ac="Alternative", w=0.05,
         fx="USD", fp="commodities",       proxy="DJP", dur=None, sdur=None, cbkt=None, bccy=None, ilhc=0.00),
    dict(ticker="MLPA",    name="MLP / Infrastructure ETF",   ac="Alternative", w=0.04,
         fx="USD", fp="infrastructure",    proxy="MLPA",dur=None, sdur=None, cbkt=None, bccy=None, ilhc=0.00),
    dict(ticker="PE_FUND", name="Private Equity Fund (Buyout)",ac="Private",    w=0.06,
         fx="EUR", fp="pe_buyout",         proxy="IWM", dur=None, sdur=None, cbkt=None, bccy=None, ilhc=0.15),
    dict(ticker="RE_FUND", name="Private Real Estate (Core EU)",ac="Private",   w=0.04,
         fx="EUR", fp="real_estate",       proxy="VNQ", dur=None, sdur=None, cbkt=None, bccy=None, ilhc=0.10),
]

# =============================================================================
# KNOWLEDGE TABLES
# =============================================================================
PROXY_SUB = {
    "AGG":     {"proxy":"^TNX","conf":"medium","note":"10Y US yield before 2003"},
    "TLT":     {"proxy":"^TNX","conf":"medium","note":"Inverted 10Y yield → long Treasury"},
    "LQD":     {"proxy":"AGG", "conf":"medium","note":"AGG as LQD proxy"},
    "GLD":     {"proxy":"GC=F","conf":"high",  "note":"Gold futures before 2004"},
    "DJP":     {"proxy":"GLD", "conf":"low",   "note":"Gold as broad-commodities proxy"},
    "MLPA":    {"proxy":"SPY", "conf":"low",   "note":"SPY as infra/MLP proxy"},
    "EEM":     {"proxy":"EFA", "conf":"medium","note":"EFA as EM proxy before 2003"},
    "PE_FUND": {"proxy":"IWM", "conf":"low",   "note":"Small-cap ETF + haircut as PE proxy"},
    "RE_FUND": {"proxy":"VNQ", "conf":"low",   "note":"US REIT + haircut as EU RE proxy"},
}

BOND_SHOCKS = {
    "Dot-com Bust":          {"ru":-150,"re":-100,"ig": +80,"hy": +300,"sov":   0},
    "9/11 Shock":            {"ru": -50,"re": -30,"ig":+100,"hy": +200,"sov":   0},
    "GFC / Lehman":          {"ru":-200,"re":-150,"ig":+400,"hy":+1500,"sov":+200},
    "COVID Crash":           {"ru":-100,"re": -50,"ig":+350,"hy": +800,"sov":+100},
    "Rates Shock 2022":      {"ru":+310,"re":+250,"ig":+150,"hy": +300,"sov":+200},
    "Taper Tantrum":         {"ru":+100,"re": +60,"ig": +80,"hy": +150,"sov": +80},
    "EU Sovereign Debt":     {"ru": -30,"re": -20,"ig":+100,"hy": +200,"sov":+500},
    "Crypto Winter 2022":    {"ru":+200,"re":+150,"ig":+100,"hy": +250,"sov":+100},
    "Inflation Persistante": {"ru":+200,"re":+180,"ig":+120,"hy": +280,"sov":+150},
}

FX_SHOCKS = {
    "Dot-com Bust":          {"EUR":-0.08,"GBP":-0.05,"JPY":+0.05,"CHF":-0.03},
    "9/11 Shock":            {"EUR":-0.02,"GBP":-0.01,"JPY":+0.03,"CHF":+0.02},
    "GFC / Lehman":          {"EUR":-0.10,"GBP":-0.15,"JPY":+0.12,"CHF":+0.08},
    "COVID Crash":           {"EUR":-0.03,"GBP":-0.08,"JPY":+0.02,"CHF":+0.05},
    "Rates Shock 2022":      {"EUR":-0.15,"GBP":-0.18,"JPY":-0.20,"CHF":-0.05},
    "Taper Tantrum":         {"EUR":-0.03,"GBP":-0.02,"JPY":-0.08,"CHF":-0.02},
    "EU Sovereign Debt":     {"EUR":-0.12,"GBP":-0.05,"JPY":+0.05,"CHF":+0.10},
    "Crypto Winter 2022":    {"EUR":-0.12,"GBP":-0.15,"JPY":-0.18,"CHF":-0.04},
    "Inflation Persistante": {"EUR":-0.08,"GBP":-0.10,"JPY":-0.15,"CHF":-0.02},
}

FACTOR_PROFILES = {
    "us_large_blend":    {"market": 1.00,"size":-0.10,"value": 0.00,"em":0.00,"commod":0.05,"gold":-0.05},
    "us_large_growth":   {"market": 1.10,"size":-0.15,"value":-0.40,"em":0.00,"commod":0.00,"gold":-0.10},
    "intl_large_blend":  {"market": 0.90,"size": 0.05,"value": 0.10,"em":0.20,"commod":0.10,"gold": 0.00},
    "em_blend":          {"market": 0.85,"size": 0.10,"value": 0.15,"em":0.70,"commod":0.20,"gold": 0.05},
    "gold":              {"market":-0.10,"size": 0.00,"value": 0.00,"em":0.00,"commod":0.30,"gold": 1.00},
    "commodities":       {"market": 0.20,"size": 0.00,"value": 0.10,"em":0.10,"commod":0.90,"gold": 0.20},
    "infrastructure":    {"market": 0.60,"size": 0.10,"value": 0.20,"em":0.05,"commod":0.30,"gold": 0.00},
    "pe_buyout":         {"market": 1.20,"size": 0.40,"value": 0.20,"em":0.10,"commod":0.05,"gold": 0.00},
    "real_estate":       {"market": 0.70,"size": 0.10,"value": 0.30,"em":0.05,"commod":0.10,"gold": 0.05},
    "bond_ig_usd":       {"market": 0.00,"size": 0.00,"value": 0.00,"em":0.00,"commod":0.00,"gold": 0.00},
    "bond_sovereign_usd":{"market": 0.00,"size": 0.00,"value": 0.00,"em":0.00,"commod":0.00,"gold": 0.00},
}

FACTOR_SHOCKS = {
    "Dot-com Bust":          {"market":-0.49,"size":+0.08,"value":+0.25,"em":-0.35,"commod":+0.10,"gold":+0.15},
    "9/11 Shock":            {"market":-0.12,"size":-0.08,"value":+0.02,"em":-0.10,"commod":-0.05,"gold":+0.03},
    "GFC / Lehman":          {"market":-0.54,"size":-0.10,"value":-0.20,"em":-0.55,"commod":-0.40,"gold":+0.25},
    "COVID Crash":           {"market":-0.34,"size":-0.15,"value":-0.20,"em":-0.32,"commod":-0.45,"gold":+0.05},
    "Rates Shock 2022":      {"market":-0.25,"size":-0.05,"value":+0.10,"em":-0.28,"commod":+0.25,"gold":-0.02},
    "Taper Tantrum":         {"market":-0.06,"size":-0.04,"value":+0.02,"em":-0.15,"commod":-0.08,"gold":-0.12},
    "EU Sovereign Debt":     {"market":-0.20,"size":-0.08,"value":-0.05,"em":-0.18,"commod":-0.10,"gold":+0.10},
    "Crypto Winter 2022":    {"market":-0.22,"size":-0.08,"value":+0.08,"em":-0.25,"commod":+0.15,"gold":-0.04},
    "Inflation Persistante": {"market":-0.20,"size":-0.03,"value":+0.08,"em":-0.15,"commod":+0.30,"gold":+0.15},
}

DEFAULT_SCENARIOS = [
    {"name":"Dot-com Bust",       "start":"2000-03-10","end":"2002-10-09","type":"historical",
     "desc":"NASDAQ -78%, SPY -49%. Prolonged equity bear market."},
    {"name":"9/11 Shock",         "start":"2001-09-10","end":"2001-09-21","type":"historical",
     "desc":"Markets closed 4 days. Freefall on reopening."},
    {"name":"GFC / Lehman",       "start":"2007-10-09","end":"2009-03-09","type":"historical",
     "desc":"SPY -57%. HY spreads +1500bps. Worst post-war crisis."},
    {"name":"COVID Crash",        "start":"2020-02-19","end":"2020-03-23","type":"historical",
     "desc":"Fastest crash in history — -34% in 33 days."},
    {"name":"Rates Shock 2022",   "start":"2022-01-03","end":"2022-10-12","type":"historical",
     "desc":"Worst bond year since 1788. TLT -40%, SPY -25%."},
    {"name":"Taper Tantrum",      "start":"2013-05-22","end":"2013-06-24","type":"historical",
     "desc":"Bernanke tapering. Rates +100bps in 5 weeks. EM -15%."},
    {"name":"EU Sovereign Debt",  "start":"2010-04-23","end":"2011-11-25","type":"historical",
     "desc":"Peripheral spreads +500bps. EUR stress."},
    {"name":"Crypto Winter 2022", "start":"2021-11-08","end":"2022-12-31","type":"historical",
     "desc":"BTC -77%, ETH -80%. Broad risk-off on growth assets."},
    {"name":"Inflation Persistante","start":None,"end":None,"type":"custom",
     "desc":"Custom: structural inflation 5-7%. Long rates +200bps. Stagflation."},
]

# =============================================================================
# COMPUTATION ENGINE
# =============================================================================
def _mdd(s):
    s = s.dropna()
    if len(s)<2: return 0.0
    return ((s - s.cummax()) / s.cummax()).min()

def bond_reprice(r, sn):
    if sn not in BOND_SHOCKS: return None
    sh = BOND_SHOCKS[sn]
    dur = r.get("dur") or 0.0; sdur = r.get("sdur") or 0.0
    bkt = r.get("cbkt") or "Sovereign"; ccy = r.get("bccy") or "USD"
    dr  = sh.get("ru" if ccy=="USD" else "re", 0) / 10_000
    ds  = (sh["ig"] if bkt=="IG" else sh["hy"] if bkt=="HY" else sh["sov"]) / 10_000
    return -dur*dr + -sdur*ds

def factor_reprice(r, sn):
    if sn not in FACTOR_SHOCKS: return None
    fp = r.get("fp")
    if not fp or fp not in FACTOR_PROFILES: return None
    p = FACTOR_PROFILES[fp]; sh = FACTOR_SHOCKS[sn]
    return (p["market"]*sh["market"] + p["size"]*sh["size"] + p["value"]*sh["value"] +
            p["em"]*sh["em"]         + p["commod"]*sh["commod"] + p["gold"]*sh["gold"])

def fx_impact(fx, sn):
    if fx=="USD" or sn not in FX_SHOCKS: return 0.0
    return FX_SHOCKS[sn].get(fx, 0.0)

def asset_ret(ticker, r, prices, dlmap, sc, method):
    sn  = sc["name"]; ac = r["ac"]
    fxi = fx_impact(r.get("fx","USD"), sn)
    ilh = r.get("ilhc", 0.0)
    out = {"ret":0.0,"fx":fxi,"conf":1.0,"src":"direct","miss":False}

    # Custom scenario
    if sc.get("type")=="custom":
        if ac=="Bond":
            dp = bond_reprice(r, sn) or 0.0
            return {**out,"ret":dp+fxi,"conf":0.70,"src":"duration"}
        dp = factor_reprice(r, sn) or 0.0
        if dp<0 and ilh>0: dp *= (1+ilh)
        return {**out,"ret":dp+fxi,"conf":0.50 if ac=="Private" else 0.65,"src":"factor"}

    # Historical scenario — find price series
    s0,s1   = sc["start"], sc["end"]
    dl      = dlmap.get(ticker, ticker)
    is_priv = (ac=="Private")
    ps=None; conf=1.0; src="direct"; is_prx=False

    if dl in prices.columns:
        cand = prices[dl].loc[s0:s1].dropna()
        if len(cand)>=2:
            ps = cand
            if is_priv:
                pi   = PROXY_SUB.get(ticker,{})
                conf = CONF_SCORES.get(pi.get("conf","low"),0.25)
                src="proxy"; is_prx=True

    # [1] Fallback proxy substitution
    if (ps is None or len(ps)<2) and not is_priv:
        pi = PROXY_SUB.get(dl) or PROXY_SUB.get(ticker)
        if pi and pi.get("proxy") in prices.columns:
            cand2 = prices[pi["proxy"]].loc[s0:s1].dropna()
            if len(cand2)>=2:
                ps=cand2; conf=CONF_SCORES[pi["conf"]]; src="proxy"; is_prx=True

    # [3] Bond duration repricing
    if ac=="Bond":
        dp_d = bond_reprice(r, sn)
        if dp_d is not None:
            if ps is not None and not is_prx:
                dp_p = ps.iloc[-1]/ps.iloc[0]-1 if method=="window" else _mdd(ps)
                dp   = 0.60*dp_d + 0.40*dp_p
                return {**out,"ret":dp+fxi,"conf":min(conf,0.85),"src":"duration+price"}
            return {**out,"ret":dp_d+fxi,"conf":0.65,"src":"duration"}

    # [8] Price + factor blend for equities/alternatives/private
    if ps is not None and len(ps)>=2:
        dp_p = ps.iloc[-1]/ps.iloc[0]-1 if method=="window" else _mdd(ps)
        if is_prx and conf<0.50:
            dp_f = factor_reprice(r, sn)
            if dp_f is not None:
                dp = 0.40*dp_p + 0.60*dp_f
                out.update({"ret":dp+fxi,"conf":conf*0.6+0.25,"src":"blend"})
            else:
                out.update({"ret":dp_p+fxi,"conf":conf,"src":"proxy"})
        else:
            out.update({"ret":dp_p+fxi,"conf":conf,"src":src})
        if ilh>0 and out["ret"]<0:          # [9] illiquidity haircut
            out["ret"] *= (1+ilh); out["src"]+="+illiq"
    else:
        dp_f = factor_reprice(r, sn)
        if dp_f is not None:
            out.update({"ret":dp_f+fxi,"conf":0.40,"src":"factor"})
        else:
            out.update({"ret":0.0,"conf":0.0,"src":"missing","miss":True})

    out["conf"] = max(0.0,min(1.0,out["conf"]))
    return out

def conf_score(ares, weights):
    bd={"direct":0.0,"proxy":0.0,"duration":0.0,"factor":0.0,"blend":0.0,"missing":0.0}
    wc=tw=0.0
    for tk,r in ares.items():
        w=weights.get(tk,0.0); tw+=w; wc+=w*r["conf"]; s=r["src"]
        if "missing" in s:              bd["missing"]  +=w
        elif "blend" in s or "+" in s:  bd["blend"]    +=w
        elif "duration" in s:           bd["duration"] +=w
        elif "factor" in s:             bd["factor"]   +=w
        elif "proxy" in s:              bd["proxy"]    +=w
        else:                           bd["direct"]   +=w
    score = wc/tw if tw>0 else 0.0
    grade = "🟢 High" if score>=0.80 else ("🟡 Medium" if score>=0.55 else "🔴 Low")
    return {"score":score,"grade":grade,"bd":bd}

def boot_bands(prices, weights, sc, dlmap, n=300, block=20):
    if sc.get("type")=="custom" or not sc.get("start"): return {}
    avail=[t for t in weights.index if dlmap.get(t,t) in prices.columns]
    dl_t =[dlmap.get(t,t) for t in avail]
    wav  = weights[avail]/weights[avail].sum()
    wp   = prices[dl_t].loc[sc["start"]:sc["end"]].dropna(how="all")
    if len(wp)<block*2: return {}
    rets=wp.pct_change().dropna(how="all"); nd=len(rets); nb=max(1,nd//block)
    prs=[]
    for _ in range(n):
        starts=np.random.randint(0,max(1,nd-block),size=nb)
        samp=pd.concat([rets.iloc[s:s+block] for s in starts]).reset_index(drop=True)
        cum=(1+samp).prod()-1
        pr=sum(wav[t]*cum.get(dlmap.get(t,t),0.0) for t in avail if dlmap.get(t,t) in cum.index)
        prs.append(pr)
    pa=np.array(prs)
    return {"p10":np.percentile(pa,10),"med":np.median(pa),"p90":np.percentile(pa,90)}

@st.cache_data(show_spinner=False)
def _prices(tickers_key):
    tks = list(tickers_key)
    raw = yf.download(tks, start="1998-01-01", auto_adjust=True, progress=False)

    if isinstance(raw.columns, pd.MultiIndex):
        lvl0 = raw.columns.get_level_values(0).unique().tolist()
        lvl1 = raw.columns.get_level_values(1).unique().tolist()
        if "Close" in lvl0:
            # yfinance >=0.2.x: (price_type, ticker)
            out = raw["Close"]
            if isinstance(out, pd.Series):
                out = out.to_frame(name=tks[0])
        else:
            # older yfinance: (ticker, price_type)
            out = raw.xs("Close", axis=1, level=1)
    else:
        close_col = next((c for c in raw.columns if str(c).lower() == "close"), None)
        if close_col:
            out = raw[[close_col]].rename(columns={close_col: tks[0]})
        else:
            out = raw.iloc[:, :1].copy()
            out.columns = [tks[0]]

    if isinstance(out, pd.DataFrame) and len(out.columns) == 1 and len(tks) == 1:
        out.columns = [tks[0]]

    return out.ffill(limit=5)

@st.cache_data(show_spinner=False)
def run_all(ptf_key, sc_key, pf_val, method, dhc, n_boot):
    ptf  = pd.DataFrame([dict(r) for r in ptf_key]).set_index("ticker")
    scs  = [dict(s) for s in sc_key]
    w    = ptf["weight"] if "weight" in ptf.columns else ptf["w"]
    # Normalise — support both field names
    if "w" in ptf.columns and "weight" not in ptf.columns:
        ptf["weight"] = ptf["w"]
    w = ptf["weight"]
    dlmap = {tk:(row["proxy"] if row["ac"]=="Private" and row["proxy"] else tk)
             for tk,row in ptf.iterrows()}
    prices = _prices(tuple(sorted(set(v for v in dlmap.values() if v))))
    rows=[]
    for sc in scs:
        ares = {tk:asset_ret(tk,row.to_dict(),prices,dlmap,sc,method)
                for tk,row in ptf.iterrows()}
        cs   = conf_score(ares,w)
        pr   = sum(w[t]*ares[t]["ret"] for t in ptf.index)
        loss = max(0.0,-pr)
        if method=="drawdown" and pr<0:
            undiv=sum(w[t]*min(0.0,ares[t]["ret"]) for t in ptf.index)
            adj=undiv+(pr-undiv)*(1-dhc); dloss=max(0.0,-adj)
        else:
            dloss=loss
        contribs={ac:sum(w[t]*ares[t]["ret"] for t in ptf.index if ptf.loc[t,"ac"]==ac)
                  for ac in ["Equity","Bond","Alternative","Private"]}
        caset={t:w[t]*ares[t]["ret"] for t in ptf.index}
        bands=boot_bands(prices,w,sc,dlmap,n=n_boot) if n_boot>0 else {}
        rows.append({
            "name":sc["name"],"type":sc.get("type"),"desc":sc.get("desc",""),
            "start":sc.get("start") or "Custom","end":sc.get("end") or "Custom",
            "pr":pr,"loss":loss,"dloss":dloss,"loss_usd":loss*pf_val,
            "cs":cs["score"],"cg":cs["grade"],
            "c_dir":cs["bd"]["direct"],"c_prx":cs["bd"]["proxy"],
            "c_dur":cs["bd"]["duration"],"c_fac":cs["bd"]["factor"],
            "c_bld":cs["bd"]["blend"],"c_mis":cs["bd"]["missing"],
            **{f"co_{k}":v for k,v in contribs.items()},
            "caset":caset,"ares":ares,
            "bp10":bands.get("p10"),"bmed":bands.get("med"),"bp90":bands.get("p90"),
        })
    return pd.DataFrame(rows),prices

# =============================================================================
# SESSION STATE
# =============================================================================
if "st3_ptf" not in st.session_state:
    st.session_state.st3_ptf = copy.deepcopy(DEFAULT_PTF)

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    sidebar_brand("Stress Tests")
    sidebar_section("Portfolio Weights")
    ptf = st.session_state.st3_ptf
    for i,row in enumerate(ptf):
        c1,c2=st.columns([3,2])
        with c1:
            ac_c=AC_COLOR.get(row["ac"],PRIMARY)
            dot=f"<span style='color:{ac_c};'>●</span>"
            st.markdown(f"<div style='font-size:0.74rem;color:{GREY_700};"
                        f"padding-top:0.45rem;'>{dot} {row['ticker']}</div>",
                        unsafe_allow_html=True)
        with c2:
            nw=st.number_input("w",value=row["w"]*100,key=f"w3_{row['ticker']}",
                               label_visibility="collapsed",
                               min_value=0.0,max_value=100.0,step=1.0,format="%.0f")
            ptf[i]["w"]=nw/100.0
    tw=sum(r["w"] for r in ptf)
    if abs(tw-1.0)>0.005:
        st.markdown(f"<div class='wp-warn'>⚠ Total = {tw:.0%} — must be 100%</div>",
                    unsafe_allow_html=True)

    sidebar_section("Run Parameters")
    pf_val = st.number_input("Portfolio Value (USD)",value=1_000_000,step=100_000,format="%d")
    method = st.selectbox("Return Method",["window","drawdown"],
                          format_func=lambda x:{"window":"Fixed Window","drawdown":"Peak-to-Trough"}[x])
    dhc    = st.slider("Diversification Haircut (%)",0,40,20)/100
    n_boot = st.select_slider("Bootstrap Iterations",[0,100,300,500],value=300)

    sidebar_section("Active Scenarios")
    active_sc=[]
    for sc in DEFAULT_SCENARIOS:
        badge="🟡 " if sc["type"]=="custom" else ""
        if st.checkbox(f"{badge}{sc['name']}",value=True,key=f"sc3_{sc['name']}"):
            active_sc.append(sc)

    st.markdown(f"<hr style='border:none;border-top:1px solid {PRIMARY_PALE};margin:0.9rem 0;'/>",
                unsafe_allow_html=True)
    run=st.button("▶  Run Stress Tests",use_container_width=True)

# =============================================================================
# PAGE HEADER
# =============================================================================
page_header("Stress Tests Historiques V2",
            "Historical · Custom · Duration Repricing · Factor Model · FX Decomposition · Bootstrap",
            badge="Module 03")

# =============================================================================
# LANDING
# =============================================================================
if not run:
    FEAT=[
        ("🔴","01","Proxy Substitution",       "Explicit fallback chain — no asset silently excluded"),
        ("🔴","02","Confidence Score",          "% portfolio mapped: direct / proxy / duration / factor / missing"),
        ("🔴","03","Bond Duration Repricing",   "−Dur×Δrate + −SpreadDur×Δspread per bucket (IG/HY/Sovereign)"),
        ("🟡","04","FX Decomposition",          "EUR, GBP, JPY, CHF shock per asset × scenario"),
        ("🟡","05","Diversification Haircut",   "Configurable haircut on diversification benefit (peak-to-trough)"),
        ("🟡","06","Bootstrap P10–P90",         "Block bootstrap uncertainty bands on fixed-window returns"),
        ("🟡","07","9 Scenarios",               "Dot-com · 9/11 · GFC · COVID · Rates 2022 · Taper · EU Sov · Crypto · Inflation"),
        ("🟢","08","Factor-Based Repricing",    "Equity beta × factor shocks when proxy confidence < 50%"),
        ("🟢","09","Private Asset Haircuts",    "PE & Real Estate via ETF proxy + illiquidity haircut"),
    ]
    c1,c2=st.columns(2)
    for i,(dot,num,title,desc) in enumerate(FEAT):
        col=c1 if i%2==0 else c2
        col.markdown(f"""
        <div style='border:1px solid {PRIMARY_PALE};border-left:3px solid {PRIMARY};
                    border-radius:4px;padding:0.75rem 1rem;margin-bottom:0.5rem;'>
          <div style='font-size:0.62rem;font-weight:600;color:{PRIMARY_DARK};
                      letter-spacing:0.12em;text-transform:uppercase;'>{dot} {num}</div>
          <div style='font-size:0.82rem;font-weight:500;color:{GREY_900};margin-top:0.1rem;'>{title}</div>
          <div style='font-size:0.73rem;color:{GREY_500};margin-top:0.12rem;line-height:1.5;'>{desc}</div>
        </div>""",unsafe_allow_html=True)
    st.markdown(f"""<div style='text-align:center;padding:1rem 0;'>
      <span style='font-size:0.8rem;color:{GREY_500};'>
        Configure sidebar → <strong style='color:{PRIMARY_DARK};'>Run Stress Tests</strong>
      </span></div>""",unsafe_allow_html=True)
    st.stop()

if abs(tw-1.0)>0.005:
    st.markdown(f"<div class='wp-warn'>⚠ Weights sum to {tw:.1%}. Adjust to 100%.</div>",
                unsafe_allow_html=True); st.stop()
if not active_sc:
    st.warning("Select at least one scenario."); st.stop()

# =============================================================================
# EXECUTE
# =============================================================================
ptf_key=tuple(tuple(sorted(r.items())) for r in ptf)
sc_key =tuple(tuple(sorted(s.items())) for s in active_sc)
with st.spinner("Downloading market data & running stress tests…"):
    df,prices=run_all(ptf_key,sc_key,pf_val,method,dhc,n_boot)

# Rebuild ptf_df with consistent column names
ptf_df=pd.DataFrame(ptf).set_index("ticker")
ptf_df["weight"]=ptf_df["w"]
ptf_df["asset_class"]=ptf_df["ac"]
wts=ptf_df["w"]
ns=len(df); x=np.arange(ns); scn=df["name"].tolist()

# =============================================================================
# KPI ROW
# =============================================================================
worst_w =df.loc[df["loss"].idxmax()]
worst_d =df.loc[df["dloss"].idxmax()]
best_def=df.loc[df["pr"].idxmax()]
avg_cs  =df["cs"].mean()
cols=st.columns(5)
for col,(lbl,val,sub,neg,pos) in zip(cols,[
    ("Worst Loss (Window)",   f"{worst_w['loss']:.1%}",  f"${worst_w['loss']*pf_val:,.0f} — {worst_w['name']}", True,False),
    ("Worst Loss + Haircut",  f"{worst_d['dloss']:.1%}", f"${worst_d['dloss']*pf_val:,.0f} — {worst_d['name']}",True,False),
    ("Best Defensive",        f"{best_def['pr']:+.1%}",  f"{best_def['name']}",False,best_def["pr"]>0),
    ("Avg Confidence",        f"{avg_cs:.0%}",           "Across active scenarios",False,avg_cs>=0.70),
    ("Scenarios",             str(ns),                   f"{method} · {n_boot} bootstrap",False,False),
]):
    col.markdown(kpi_card(lbl,val,sub,neg,pos),unsafe_allow_html=True)

st.markdown(f"""
<div style='display:flex;gap:0.45rem;flex-wrap:wrap;margin-top:0.8rem;'>
  <span class='wp-badge badge-n'>{'Fixed Window' if method=='window' else 'Peak-to-Trough'}</span>
  <span class='wp-badge badge-w'>Haircut {dhc:.0%}</span>
  <span class='wp-badge badge-n'>Bootstrap {n_boot} iters</span>
</div>""",unsafe_allow_html=True)
st.markdown("<hr class='wp-hr'/>",unsafe_allow_html=True)

# =============================================================================
# TABS
# =============================================================================
T1,T2,T3,T4,T5=st.tabs(["📉 Scenario Losses","🧩 Asset Contributions",
                          "🏦 Bond & FX Detail","🔍 Confidence & Sources","📋 Holdings"])

# ── T1: Scenario Losses ──────────────────────────────────────────────────────
with T1:
    section("Estimated Portfolio Loss by Scenario")
    fig,ax=plt.subplots(figsize=(14,5.8))
    wb=0.26
    for i in range(ns):
        if i%2==0: ax.axvspan(i-.5,i+.5,color=PRIMARY_WASH,alpha=0.6,zorder=0)
    b1=ax.bar(x-wb,df["loss"]*100, wb,label="Fixed Window",color=PRIMARY,  alpha=0.87,zorder=3)
    b2=ax.bar(x,   df["loss"]*100, wb,label="Peak-to-Trough (raw)",color=RED_SOFT,alpha=0.40,zorder=3)
    b3=ax.bar(x+wb,df["dloss"]*100,wb,label=f"PtT +{dhc:.0%} haircut",color="#7C3AED",alpha=0.87,zorder=3)
    for bars,col in [(b1,PRIMARY),(b3,"#7C3AED")]:
        for bar in bars:
            h=bar.get_height()
            if h>0.4: ax.text(bar.get_x()+bar.get_width()/2,h+0.25,f"{h:.1f}%",
                              ha="center",va="bottom",fontsize=7.5,color=col)
    if n_boot>0:
        for i,row in df.iterrows():
            if row["bp10"] is not None and row["bp90"] is not None:
                y_lo=max(0,-row["bp90"])*100; y_hi=max(0,-row["bp10"])*100
                ax.vlines(x[i]-wb,y_lo,y_hi,color=PRIMARY,lw=2.5,zorder=4)
                ax.hlines([y_lo,y_hi],x[i]-wb-.04,x[i]-wb+.04,color=PRIMARY,lw=1.5,zorder=4)
    for i,row in df.iterrows():
        if row["type"]=="custom":
            ax.text(x[i],-1.2,"CUSTOM",ha="center",fontsize=6.5,color=AMBER,style="italic")
    ax.set_xticks(x); ax.set_xticklabels(scn,rotation=18,ha="right",fontsize=8.5)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.set_ylabel("Estimated Loss (%)"); ax.legend(fontsize=8.5)
    ax.set_title("Portfolio Loss — Window · Peak-to-Trough · PtT + Haircut\n"
                 "Error bars = Bootstrap P10–P90" if n_boot>0 else
                 "Portfolio Loss — Window · Peak-to-Trough · PtT + Haircut")
    plt.tight_layout(); st.pyplot(fig,use_container_width=True); plt.close()

    section("Absolute Loss in USD")
    fig2,ax2=plt.subplots(figsize=(14,4))
    lw=df["loss"]*pf_val/1e3; ld=df["dloss"]*pf_val/1e3
    for i in range(ns):
        if i%2==0: ax2.axvspan(i-.5,i+.5,color=PRIMARY_WASH,alpha=0.6,zorder=0)
    bw2=ax2.bar(x-.22,lw,0.42,label="Fixed Window",color=PRIMARY,  alpha=0.87,zorder=3)
    bh2=ax2.bar(x+.22,ld,0.42,label="PtT+Haircut", color="#7C3AED",alpha=0.87,zorder=3)
    for bar,v in zip(bw2,lw):
        if v>0.5: ax2.text(bar.get_x()+bar.get_width()/2,v+.4,f"${v:,.0f}k",
                           ha="center",va="bottom",fontsize=7,color=PRIMARY)
    for bar,v in zip(bh2,ld):
        if v>0.5: ax2.text(bar.get_x()+bar.get_width()/2,v+.4,f"${v:,.0f}k",
                           ha="center",va="bottom",fontsize=7,color="#7C3AED")
    ax2.set_xticks(x); ax2.set_xticklabels(scn,rotation=18,ha="right",fontsize=8.5)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_:f"${v:,.0f}k"))
    ax2.set_ylabel("Loss (kUSD)"); ax2.legend(fontsize=8.5)
    ax2.set_title(f"USD Impact — Portfolio ${pf_val/1e6:.1f}M")
    plt.tight_layout(); st.pyplot(fig2,use_container_width=True); plt.close()

    section("Scenario Detail Table")
    rh=""
    for _,row in df.iterrows():
        nc="td-neg" if row["pr"]<0 else "td-pos"
        clab=(f" <span style='font-size:0.6rem;color:{AMBER};font-style:italic;'>CUSTOM</span>"
              if row["type"]=="custom" else "")
        bs=(f"{row['bp10']:.1%} / {row['bp90']:.1%}" if row["bp10"] is not None else "—")
        rh+=f"""<tr>
          <td>{row['name']}{clab}</td>
          <td style='text-align:left;font-size:0.72rem;color:{GREY_500};'>{row['desc']}</td>
          <td class='{nc}'>{row['pr']:+.2%}</td>
          <td class='td-neg'>{row['loss']:.2%}</td>
          <td class='td-neg'>{row['dloss']:.2%}</td>
          <td>${row['loss_usd']:,.0f}</td>
          <td>{row['cg']}</td>
          <td style='font-size:0.75rem;'>{bs}</td>
        </tr>"""
    st.markdown(f"""<table class='wp-table'><thead><tr>
      <th>Scenario</th><th style='text-align:left;'>Description</th>
      <th>Return</th><th>Loss (Window)</th><th>Loss+Haircut</th>
      <th>Loss (USD)</th><th>Confidence</th><th>Bootstrap P10/P90</th>
    </tr></thead><tbody>{rh}</tbody></table>""",unsafe_allow_html=True)

# ── T2: Asset Contributions ───────────────────────────────────────────────────
with T2:
    section("P&L Contribution by Asset Class — Stacked")
    fig3,ax3=plt.subplots(figsize=(14,5.5))
    for i in range(ns):
        if i%2==0: ax3.axvspan(i-.5,i+.5,color=PRIMARY_WASH,alpha=0.6,zorder=0)
    bp=np.zeros(ns); bn=np.zeros(ns)
    for ac,col in [("Equity",AC_COLOR["Equity"]),("Bond",AC_COLOR["Bond"]),
                   ("Alternative",AC_COLOR["Alternative"]),("Private",AC_COLOR["Private"])]:
        vals=df[f"co_{ac}"].values*100
        for i,v in enumerate(vals):
            if v>=0:
                ax3.bar(x[i],v,.55,bottom=bp[i],color=col,alpha=0.87,zorder=3,
                        label=ac if i==0 else "")
                bp[i]+=v
            else:
                ax3.bar(x[i],v,.55,bottom=bn[i],color=col,alpha=0.87,zorder=3,
                        label=ac if i==0 else "")
                bn[i]+=v
    ax3.axhline(0,color=GREY_300,lw=0.8,zorder=5)
    ax3.set_xticks(x); ax3.set_xticklabels(scn,rotation=18,ha="right",fontsize=8.5)
    ax3.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax3.set_ylabel("P&L Contribution (%)")
    ax3.legend(handles=[mpatches.Patch(color=AC_COLOR[a],label=a)
                        for a in ["Equity","Bond","Alternative","Private"]],
               fontsize=9,loc="lower right")
    ax3.set_title("Asset-class P&L contribution per scenario\n"
                  "Positive = defensive assets that rallied (Gold, Treasuries in risk-off)")
    plt.tight_layout(); st.pyplot(fig3,use_container_width=True); plt.close()

    section("Per-Position Contribution Heatmap")
    heat=pd.DataFrame([{t:row["caset"].get(t,0)*100 for t in ptf_df.index}
                        for _,row in df.iterrows()],index=scn)
    vmax=max(abs(heat.values.max()),abs(heat.values.min()),0.5)
    cmap=mcolors.LinearSegmentedColormap.from_list("wp",[RED_SOFT,WHITE,GREEN_SOFT])
    fig4,ax4=plt.subplots(figsize=(14,max(4,ns*0.62)))
    sns.heatmap(heat,ax=ax4,cmap=cmap,center=0,vmin=-vmax,vmax=vmax,
                annot=True,fmt=".1f",annot_kws={"size":7.5},
                linewidths=0.3,linecolor=GREY_100,cbar_kws={"shrink":0.6})
    ax4.tick_params(axis="x",rotation=30,labelsize=8)
    ax4.tick_params(axis="y",rotation=0, labelsize=8)
    ax4.set_title("Per-position P&L contribution (%) — Red = loss · Green = gain")
    plt.tight_layout(); st.pyplot(fig4,use_container_width=True); plt.close()

# ── T3: Bond & FX Detail ──────────────────────────────────────────────────────
with T3:
    bond_tks=[t for t in ptf_df.index if ptf_df.loc[t,"ac"]=="Bond"]
    section("[3] Bond Duration Re-Pricing")
    if bond_tks:
        rh=""
        for sc in active_sc:
            sn=sc["name"]
            if sn not in BOND_SHOCKS:
                rh+=(f"<tr><td colspan='7' style='color:{GREY_300};font-size:0.73rem;"
                     f"padding:0.4rem 0.75rem;'>{sn} — no rate shock (factor/price only)</td></tr>")
                continue
            sh=BOND_SHOCKS[sn]
            for tk in bond_tks:
                r=ptf_df.loc[tk]; dp=bond_reprice(r.to_dict(),sn) or 0.0
                ccy=r.get("bccy") or "USD"
                dr=sh.get("ru" if ccy=="USD" else "re",0)
                ds=(sh["ig"] if r.get("cbkt")=="IG" else sh["hy"] if r.get("cbkt")=="HY" else sh["sov"])
                nc="td-neg" if dp<0 else "td-pos"
                rh+=f"""<tr>
                  <td>{sn}</td><td>{tk} — {r['name']}</td>
                  <td>{r.get('cbkt','—') or '—'}</td><td>{ccy}</td>
                  <td>{r.get('dur',0) or 0:.1f}y / {r.get('sdur',0) or 0:.1f}y</td>
                  <td>{dr:+.0f}bps / {ds:+.0f}bps</td>
                  <td class='{nc}'>{dp:+.2%}</td>
                </tr>"""
        st.markdown(f"""<table class='wp-table'><thead><tr>
          <th>Scenario</th><th>Instrument</th><th>Bucket</th><th>CCY</th>
          <th>Dur/SpreadDur</th><th>Δrate/Δspread</th><th>Est. Return</th>
        </tr></thead><tbody>{rh}</tbody></table>""",unsafe_allow_html=True)
    else:
        st.info("No bond positions in portfolio.")

    section("[4] FX Decomposition")
    fx_tks=[t for t in ptf_df.index if ptf_df.loc[t,"fx"]!="USD"]
    if fx_tks:
        rh2=""
        for _,sc_row in df.iterrows():
            sn=sc_row["name"]
            for tk in fx_tks:
                ccy=ptf_df.loc[tk,"fx"]; fxi=fx_impact(ccy,sn)
                if abs(fxi)>0.001:
                    w_=wts[tk]; nc="td-neg" if fxi<0 else "td-pos"
                    rh2+=f"""<tr>
                      <td>{sn}</td><td>{tk} — {ptf_df.loc[tk,'name']}</td>
                      <td>{ccy}</td><td class='{nc}'>{fxi:+.2%}</td>
                      <td>{w_:.1%}</td><td class='{nc}'>{w_*fxi:+.3%}</td>
                    </tr>"""
        if rh2:
            st.markdown(f"""<table class='wp-table'><thead><tr>
              <th>Scenario</th><th>Asset</th><th>CCY</th>
              <th>FX Shock</th><th>Weight</th><th>Portfolio Impact</th>
            </tr></thead><tbody>{rh2}</tbody></table>""",unsafe_allow_html=True)
        else:
            st.info("FX shocks below threshold for active scenarios.")
    else:
        st.info("All positions in USD — no FX decomposition.")

# ── T4: Confidence & Sources ──────────────────────────────────────────────────
with T4:
    ca,cb=st.columns([1.6,1])
    with ca:
        section("[2] Confidence Score by Scenario")
        fig5,ax5=plt.subplots(figsize=(9,max(4,ns*0.6)))
        scores=df["cs"].values*100
        bar_c=[GREEN_SOFT if s>=80 else (AMBER if s>=55 else RED_SOFT) for s in scores]
        bh5=ax5.barh(scn[::-1],scores[::-1],color=bar_c[::-1],alpha=0.87,zorder=3)
        for bar,s in zip(bh5,scores[::-1]):
            ax5.text(s+0.5,bar.get_y()+bar.get_height()/2,f"{s:.0f}%",va="center",fontsize=9)
        ax5.axvline(80,color=GREEN_SOFT,ls="--",lw=1.1,alpha=0.6,label="High ≥80%")
        ax5.axvline(55,color=AMBER,     ls="--",lw=1.1,alpha=0.6,label="Medium ≥55%")
        ax5.set_xlim(0,112); ax5.set_xlabel("Confidence Score (%)"); ax5.legend(fontsize=8.5)
        ax5.set_title("Confidence score by scenario")
        plt.tight_layout(); st.pyplot(fig5,use_container_width=True); plt.close()

    with cb:
        section("Avg Data Sources")
        avg_bd={"Direct":df["c_dir"].mean(),"Proxy":df["c_prx"].mean(),
                "Duration":df["c_dur"].mean(),"Factor":df["c_fac"].mean(),
                "Blend":df["c_bld"].mean(),"Missing":df["c_mis"].mean()}
        labels=[k for k,v in avg_bd.items() if v>0.005]
        sizes =[v for k,v in avg_bd.items() if v>0.005]
        pal_p =[SRC_COLOR.get(k.lower(),GREY_300) for k in labels]
        fig6,ax6=plt.subplots(figsize=(4.5,4.5))
        _,_,autos=ax6.pie(sizes,labels=labels,autopct="%1.0f%%",
                          colors=pal_p,startangle=90,pctdistance=0.74,
                          wedgeprops={"linewidth":1.5,"edgecolor":WHITE})
        for at in autos: at.set_fontsize(8)
        ax6.set_title("Data sources\n(avg)",fontsize=9)
        plt.tight_layout(); st.pyplot(fig6,use_container_width=True); plt.close()

    section("Confidence Breakdown Table")
    rh3=""
    for _,row in df.iterrows():
        gc=GREEN_SOFT if row["cs"]>=0.80 else (AMBER if row["cs"]>=0.55 else RED_SOFT)
        rh3+=f"""<tr>
          <td>{row['name']}</td>
          <td style='color:{gc};font-weight:500;'>{row['cg']}</td>
          <td>{row['cs']:.0%}</td>
          <td style='color:{GREEN_SOFT};'>{row['c_dir']:.0%}</td>
          <td style='color:{AMBER};'>{row['c_prx']:.0%}</td>
          <td>{row['c_dur']:.0%}</td>
          <td style='color:#7C3AED;'>{row['c_fac']:.0%}</td>
          <td style='color:{PRIMARY_MID};'>{row['c_bld']:.0%}</td>
          <td style='color:{RED_SOFT};'>{row['c_mis']:.0%}</td>
        </tr>"""
    st.markdown(f"""<table class='wp-table'><thead><tr>
      <th>Scenario</th><th>Grade</th><th>Score</th>
      <th style='color:{GREEN_SOFT};'>Direct</th><th style='color:{AMBER};'>Proxy</th>
      <th>Duration</th><th style='color:#7C3AED;'>Factor</th>
      <th style='color:{PRIMARY_MID};'>Blend</th><th style='color:{RED_SOFT};'>Missing</th>
    </tr></thead><tbody>{rh3}</tbody></table>""",unsafe_allow_html=True)
    st.markdown(f"""<div class='wp-warn' style='margin-top:0.8rem;'>
      <strong>Reading the score</strong> —
      <span style='color:{GREEN_SOFT};'>Direct</span>: instrument's own prices (highest confidence).
      <span style='color:{AMBER};'>Proxy</span>: substitute ETF/index.
      Duration: bond re-pricing model.
      <span style='color:#7C3AED;'>Factor</span>: equity factor model.
      <span style='color:{PRIMARY_MID};'>Blend</span>: proxy + factor mixed.
      <span style='color:{RED_SOFT};'>Missing</span>: no data — return assumed 0.
    </div>""",unsafe_allow_html=True)

# ── T5: Holdings ──────────────────────────────────────────────────────────────
with T5:
    section("Portfolio Configuration")
    rh4=""
    for tk,row in ptf_df.iterrows():
        ac_c2=AC_COLOR.get(row["ac"],PRIMARY)
        dot=f"<span style='color:{ac_c2};'>●</span>"
        prx=row.get("proxy") or "—"; dur=f"{row['dur']:.1f}y" if row.get("dur") else "—"
        hc=f"{row['ilhc']:.0%}" if (row.get("ilhc") or 0)>0 else "—"
        ps=PROXY_SUB.get(tk,{}); psub=ps.get("proxy","—"); pcnf=ps.get("conf","—")
        rh4+=f"""<tr>
          <td>{dot} {tk}</td><td style='text-align:left;'>{row['name']}</td>
          <td>{row['ac']}</td><td>{row['w']:.1%}</td><td>{row.get('fx','USD')}</td>
          <td>{prx}</td><td>{psub} <span style='font-size:0.68rem;color:{GREY_500};'>({pcnf})</span></td>
          <td>{dur}</td><td>{row.get('cbkt','—') or '—'}</td>
          <td>{hc}</td><td style='font-size:0.72rem;color:{GREY_500};'>{row.get('fp','—') or '—'}</td>
        </tr>"""
    st.markdown(f"""<table class='wp-table'><thead><tr>
      <th>Ticker</th><th style='text-align:left;'>Name</th><th>Class</th>
      <th>Weight</th><th>CCY</th><th>DL Proxy</th><th>Sub. Proxy</th>
      <th>Duration</th><th>Credit</th><th>Illiq HC</th><th>Factor Profile</th>
    </tr></thead><tbody>{rh4}</tbody></table>""",unsafe_allow_html=True)

    section("[8] Active Factor Profiles")
    used_fp=ptf_df["fp"].dropna().unique()
    fp_r=""
    for fn in used_fp:
        if fn in FACTOR_PROFILES:
            b=FACTOR_PROFILES[fn]
            fp_r+=f"""<tr><td>{fn}</td>
              <td>{b['market']:+.2f}</td><td>{b['size']:+.2f}</td><td>{b['value']:+.2f}</td>
              <td>{b['em']:+.2f}</td><td>{b['commod']:+.2f}</td><td>{b['gold']:+.2f}</td>
            </tr>"""
    st.markdown(f"""<table class='wp-table'><thead><tr>
      <th>Profile</th><th>β Market</th><th>β Size</th><th>β Value</th>
      <th>β EM</th><th>β Commod</th><th>β Gold</th>
    </tr></thead><tbody>{fp_r}</tbody></table>""",unsafe_allow_html=True)

    section("[1] Proxy Substitution Table")
    ps_r=""
    for tk,info in PROXY_SUB.items():
        cc=GREEN_SOFT if info["conf"]=="high" else (AMBER if info["conf"]=="medium" else RED_SOFT)
        ps_r+=f"""<tr>
          <td>{tk}</td><td>{info['proxy']}</td>
          <td style='color:{cc};font-weight:500;'>{info['conf'].capitalize()}</td>
          <td>{CONF_SCORES[info['conf']]:.0%}</td>
          <td style='font-size:0.73rem;color:{GREY_500};'>{info['note']}</td>
        </tr>"""
    st.markdown(f"""<table class='wp-table'><thead><tr>
      <th>Ticker</th><th>Proxy</th><th>Confidence</th><th>Score</th><th>Note</th>
    </tr></thead><tbody>{ps_r}</tbody></table>""",unsafe_allow_html=True)

# =============================================================================
# DISCLAIMER
# =============================================================================
st.markdown("<hr class='wp-hr'/>",unsafe_allow_html=True)
st.markdown("""
<div class='wp-disclaimer'>
  <strong>Disclaimer</strong> — Results are indicative estimates only. Weights held constant throughout
  each scenario. Confidence score reflects data-mapping quality, not forecast precision.
  Historical scenarios do not repeat identically. Private assets and factor-based estimates
  carry material model uncertainty. Bond duration repricing is first-order only (no convexity).
  This is not investment advice.
</div>""",unsafe_allow_html=True)
