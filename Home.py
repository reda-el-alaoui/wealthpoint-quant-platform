"""
WealthPoint Platform — Home
streamlit run Home.py
"""
import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="WealthPoint",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from wealthpoint_theme import (
    inject_global_css, sidebar_brand,
    PRIMARY, PRIMARY_DARK, PRIMARY_LIGHT, PRIMARY_PALE, PRIMARY_WASH,
    GREY_900, GREY_700, GREY_500, GREY_300, GREY_100, WHITE,
    RED_SOFT, GREEN_SOFT,
)

inject_global_css()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_brand("Platform")
    st.markdown(f"""
    <div style='font-size:0.75rem;color:{GREY_500};line-height:1.7;margin-top:0.5rem;'>
      Navigate using the pages above.<br/>
      Each module is independent.
    </div>""", unsafe_allow_html=True)

# ── HOME CONTENT ──────────────────────────────────────────────────────────────
st.markdown(f"""
<div style='max-width:900px;margin:3rem auto 0 auto;padding:0 1rem;'>

  <!-- Logo mark -->
  <div style='text-align:center;margin-bottom:2.5rem;'>
    <div style='font-family:Cormorant Garamond,serif;font-size:5rem;font-weight:300;
                color:{PRIMARY_LIGHT};letter-spacing:0.08em;line-height:1;'>◈</div>
    <div style='font-family:Cormorant Garamond,serif;font-size:2.8rem;font-weight:300;
                color:{GREY_900};letter-spacing:0.06em;margin-top:0.4rem;'>WealthPoint</div>
    <div style='font-size:0.72rem;color:{GREY_500};letter-spacing:0.2em;
                text-transform:uppercase;margin-top:0.4rem;'>
      Wealth Intelligence Platform
    </div>
  </div>

  <!-- Divider -->
  <div style='border-top:1px solid {PRIMARY_PALE};margin:0 auto 2.5rem auto;width:60%;'></div>

  <!-- Feature cards — 3 modules -->
  <div style='display:grid;grid-template-columns:1fr 1fr;gap:1.4rem;max-width:880px;margin:0 auto;'>

    <!-- Module 01 -->
    <a href="/Risk_Analytics" style='text-decoration:none;'>
      <div style='background:{WHITE};border:1px solid {PRIMARY_PALE};
                  border-top:3px solid {PRIMARY};border-radius:6px;
                  padding:1.6rem 1.8rem;cursor:pointer;'>
        <div style='font-size:0.62rem;letter-spacing:0.16em;text-transform:uppercase;
                    color:{PRIMARY_DARK};font-weight:500;margin-bottom:0.6rem;'>Module 01</div>
        <div style='font-family:Cormorant Garamond,serif;font-size:1.5rem;
                    font-weight:400;color:{GREY_900};margin-bottom:0.55rem;'>Risk Analytics</div>
        <div style='font-size:0.78rem;color:{GREY_500};line-height:1.65;margin-bottom:1.1rem;'>
          Forward-looking portfolio risk from a position snapshot.
          VaR, CVaR, Monte Carlo with fat tails, crisis correlation
          regimes and liquidity-adjusted metrics.
        </div>
        <div style='display:flex;gap:0.35rem;flex-wrap:wrap;'>
          <span style='background:{PRIMARY_PALE};color:{PRIMARY_DARK};font-size:0.6rem;
                       padding:0.15rem 0.48rem;border-radius:2px;letter-spacing:0.07em;
                       text-transform:uppercase;font-weight:500;'>VaR / CVaR</span>
          <span style='background:{PRIMARY_PALE};color:{PRIMARY_DARK};font-size:0.6rem;
                       padding:0.15rem 0.48rem;border-radius:2px;letter-spacing:0.07em;
                       text-transform:uppercase;font-weight:500;'>GARCH</span>
          <span style='background:{PRIMARY_PALE};color:{PRIMARY_DARK};font-size:0.6rem;
                       padding:0.15rem 0.48rem;border-radius:2px;letter-spacing:0.07em;
                       text-transform:uppercase;font-weight:500;'>Student-t MC</span>
        </div>
      </div>
    </a>

    <!-- Module 02 -->
    <a href="/Wealth_Forecast" style='text-decoration:none;'>
      <div style='background:{WHITE};border:1px solid {PRIMARY_PALE};
                  border-top:3px solid {PRIMARY_DARK};border-radius:6px;
                  padding:1.6rem 1.8rem;cursor:pointer;'>
        <div style='font-size:0.62rem;letter-spacing:0.16em;text-transform:uppercase;
                    color:{PRIMARY_DARK};font-weight:500;margin-bottom:0.6rem;'>Module 02</div>
        <div style='font-family:Cormorant Garamond,serif;font-size:1.5rem;
                    font-weight:400;color:{GREY_900};margin-bottom:0.55rem;'>Wealth Forecast</div>
        <div style='font-size:0.78rem;color:{GREY_500};line-height:1.65;margin-bottom:1.1rem;'>
          Long-horizon Monte Carlo wealth projection. Model life events,
          cash flows, asset class assumptions and inflation over
          10-50 years.
        </div>
        <div style='display:flex;gap:0.35rem;flex-wrap:wrap;'>
          <span style='background:{PRIMARY_PALE};color:{PRIMARY_DARK};font-size:0.6rem;
                       padding:0.15rem 0.48rem;border-radius:2px;letter-spacing:0.07em;
                       text-transform:uppercase;font-weight:500;'>Fan Chart</span>
          <span style='background:{PRIMARY_PALE};color:{PRIMARY_DARK};font-size:0.6rem;
                       padding:0.15rem 0.48rem;border-radius:2px;letter-spacing:0.07em;
                       text-transform:uppercase;font-weight:500;'>Life Events</span>
          <span style='background:{PRIMARY_PALE};color:{PRIMARY_DARK};font-size:0.6rem;
                       padding:0.15rem 0.48rem;border-radius:2px;letter-spacing:0.07em;
                       text-transform:uppercase;font-weight:500;'>P10 / P50 / P90</span>
        </div>
      </div>
    </a>

    <!-- Module 03 -->
    <a href="/Stress_Tests" style='text-decoration:none;'>
      <div style='background:{WHITE};border:1px solid {PRIMARY_PALE};
                  border-top:3px solid #7C3AED;border-radius:6px;
                  padding:1.6rem 1.8rem;cursor:pointer;'>
        <div style='font-size:0.62rem;letter-spacing:0.16em;text-transform:uppercase;
                    color:{PRIMARY_DARK};font-weight:500;margin-bottom:0.6rem;'>Module 03</div>
        <div style='font-family:Cormorant Garamond,serif;font-size:1.5rem;
                    font-weight:400;color:{GREY_900};margin-bottom:0.55rem;'>Stress Tests</div>
        <div style='font-size:0.78rem;color:{GREY_500};line-height:1.65;margin-bottom:1.1rem;'>
          9 historical and custom scenarios with duration-based bond
          repricing, FX decomposition, factor model and bootstrap
          confidence bands.
        </div>
        <div style='display:flex;gap:0.35rem;flex-wrap:wrap;'>
          <span style='background:#EDE9FE;color:#5B21B6;font-size:0.6rem;
                       padding:0.15rem 0.48rem;border-radius:2px;letter-spacing:0.07em;
                       text-transform:uppercase;font-weight:500;'>9 Scenarios</span>
          <span style='background:#EDE9FE;color:#5B21B6;font-size:0.6rem;
                       padding:0.15rem 0.48rem;border-radius:2px;letter-spacing:0.07em;
                       text-transform:uppercase;font-weight:500;'>Duration</span>
          <span style='background:#EDE9FE;color:#5B21B6;font-size:0.6rem;
                       padding:0.15rem 0.48rem;border-radius:2px;letter-spacing:0.07em;
                       text-transform:uppercase;font-weight:500;'>Bootstrap P10/P90</span>
        </div>
      </div>
    </a>

    <!-- Module 04 -->
    <a href="/Debt_Engine" style='text-decoration:none;'>
      <div style='background:{WHITE};border:1px solid {PRIMARY_PALE};
                  border-top:3px solid #0F766E;border-radius:6px;
                  padding:1.6rem 1.8rem;cursor:pointer;'>
        <div style='font-size:0.62rem;letter-spacing:0.16em;text-transform:uppercase;
                    color:#0F766E;font-weight:500;margin-bottom:0.6rem;'>Module 04</div>
        <div style='font-family:Cormorant Garamond,serif;font-size:1.5rem;
                    font-weight:400;color:{GREY_900};margin-bottom:0.55rem;'>Debt Engine</div>
        <div style='font-size:0.78rem;color:{GREY_500};line-height:1.65;margin-bottom:1.1rem;'>
          Loan-level cashflow engine with fixed, variable and IO structures.
          Caps, floors, Vasicek rate paths and mathematically verified
          annuity amortization across 4 portfolios.
        </div>
        <div style='display:flex;gap:0.35rem;flex-wrap:wrap;'>
          <span style='background:#CCFBF1;color:#0F766E;font-size:0.6rem;
                       padding:0.15rem 0.48rem;border-radius:2px;letter-spacing:0.07em;
                       text-transform:uppercase;font-weight:500;'>Vasicek</span>
          <span style='background:#CCFBF1;color:#0F766E;font-size:0.6rem;
                       padding:0.15rem 0.48rem;border-radius:2px;letter-spacing:0.07em;
                       text-transform:uppercase;font-weight:500;'>IO / Caps / Floors</span>
          <span style='background:#CCFBF1;color:#0F766E;font-size:0.6rem;
                       padding:0.15rem 0.48rem;border-radius:2px;letter-spacing:0.07em;
                       text-transform:uppercase;font-weight:500;'>9 Math Tests</span>
        </div>
      </div>
    </a>

  </div>

  <!-- Footer note -->
  <div style='text-align:center;margin-top:3rem;font-size:0.7rem;
              color:{GREY_300};letter-spacing:0.08em;'>
    {datetime.today().strftime('%d %B %Y')} · For illustrative purposes only
  </div>

</div>
""", unsafe_allow_html=True)
