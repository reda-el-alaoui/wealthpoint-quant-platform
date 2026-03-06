# =============================================================================
# WealthPoint — Home.py  (Login + Landing)
# =============================================================================

import streamlit as st
import time
import sys
import os
from datetime import datetime

st.set_page_config(
    page_title="WealthPoint",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

sys.path.insert(0, os.path.dirname(__file__))
from wealthpoint_theme import (
    PRIMARY, PRIMARY_DARK, PRIMARY_MID, PRIMARY_LIGHT, PRIMARY_PALE, PRIMARY_WASH,
    GREY_900, GREY_700, GREY_500, GREY_300, WHITE,
    RED_SOFT, RED_PALE, GREEN_SOFT, GREEN_PALE, AMBER, AMBER_PALE,
)


# =============================================================================
# AUTH HELPERS
# =============================================================================

def _load_users() -> dict:
    try:
        return dict(st.secrets["users"])
    except Exception:
        return {
            "demo": "wealthpoint2026",
            "admin": "wp-admin-2026",
            "analyst": "quant#2026",
        }


def _is_authenticated() -> bool:
    return st.session_state.get("wp_authenticated", False)


def _do_login(username: str, password: str) -> bool:
    users = _load_users()
    if users.get(username.strip().lower()) == password:
        st.session_state["wp_authenticated"] = True
        st.session_state["wp_user"] = username.strip().lower()
        st.session_state["wp_attempts"] = 0
        return True
    return False


def _do_logout():
    for k in ["wp_authenticated", "wp_user", "wp_attempts"]:
        st.session_state.pop(k, None)


# =============================================================================
# LOGIN PAGE
# =============================================================================

def render_login():
    st.markdown(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600&family=DM+Sans:wght@300;400;500&display=swap');

      html, body, [class*="css"] {{
        font-family: 'DM Sans', sans-serif;
        background: linear-gradient(145deg, {PRIMARY_WASH} 0%, #ECE4D8 100%);
        color: {GREY_900};
      }}

      [data-testid="stSidebar"] {{
        display: none !important;
      }}

      .block-container {{
        max-width: 460px !important;
        padding-top: 8vh !important;
        padding-bottom: 0 !important;
      }}

      .wp-card {{
        background: {WHITE};
        border: 1px solid {PRIMARY_PALE};
        border-top: 4px solid {PRIMARY};
        border-radius: 8px;
        padding: 2.2rem 2rem 1.6rem;
        box-shadow: 0 8px 36px rgba(140,112,80,0.13);
      }}

      .wp-title {{
        font-family: 'Cormorant Garamond', serif;
        font-size: 2.1rem;
        font-weight: 300;
        color: {PRIMARY_DARK};
        letter-spacing: 0.08em;
        text-align: center;
        margin-bottom: 0.15rem;
      }}

      .wp-subtitle {{
        font-size: 0.65rem;
        color: {GREY_500};
        letter-spacing: 0.2em;
        text-transform: uppercase;
        text-align: center;
        margin-bottom: 1.8rem;
      }}

      .wp-label {{
        font-size: 0.7rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: {GREY_700};
        font-weight: 500;
        margin-bottom: 0.25rem;
      }}

      [data-testid="stTextInput"] input {{
        border: 1px solid {PRIMARY_PALE} !important;
        border-radius: 3px !important;
        font-size: 0.85rem !important;
        padding: 0.55rem 0.85rem !important;
        background: {WHITE} !important;
        color: {GREY_900} !important;
      }}

      [data-testid="stTextInput"] input:focus {{
        border-color: {PRIMARY} !important;
        box-shadow: 0 0 0 2px rgba(177,144,105,0.15) !important;
      }}

      .stButton > button {{
        background: {PRIMARY} !important;
        color: {WHITE} !important;
        border: none !important;
        border-radius: 3px !important;
        font-size: 0.8rem !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
        padding: 0.65rem 1.5rem !important;
        width: 100% !important;
        margin-top: 0.5rem !important;
      }}

      .stButton > button:hover {{
        background: {PRIMARY_DARK} !important;
      }}

      .wp-msg {{
        padding: 0.6rem 0.85rem;
        border-radius: 0 3px 3px 0;
        font-size: 0.78rem;
        margin-top: 0.6rem;
      }}

      .wp-err {{
        background: {RED_PALE};
        border-left: 3px solid {RED_SOFT};
        color: {RED_SOFT};
      }}

      .wp-ok {{
        background: {GREEN_PALE};
        border-left: 3px solid {GREEN_SOFT};
        color: {GREEN_SOFT};
      }}

      .wp-lock {{
        background: {AMBER_PALE};
        border-left: 3px solid {AMBER};
        color: {AMBER};
      }}

      .wp-footer {{
        font-size: 0.63rem;
        color: {GREY_300};
        text-align: center;
        margin-top: 1.2rem;
        letter-spacing: 0.07em;
      }}
    </style>
    """, unsafe_allow_html=True)

    if "wp_attempts" not in st.session_state:
        st.session_state.wp_attempts = 0

    locked = st.session_state.wp_attempts >= 5

    st.title(" ")
    st.title(" ")
    #st.markdown("<div class='wp-card'>", unsafe_allow_html=True)
    st.markdown("<div class='wp-title'>◈ WealthPoint</div>", unsafe_allow_html=True)
    st.markdown("<div class='wp-subtitle'>Analytics Platform · Accès sécurisé</div>", unsafe_allow_html=True)

    st.markdown("<div class='wp-label'>Identifiant</div>", unsafe_allow_html=True)
    username = st.text_input(
        "u",
        placeholder="Votre identifiant",
        label_visibility="collapsed",
        key="lg_user"
    )

    st.markdown("<div class='wp-label' style='margin-top:0.85rem;'>Mot de passe</div>", unsafe_allow_html=True)
    password = st.text_input(
        "p",
        placeholder="Votre mot de passe",
        type="password",
        label_visibility="collapsed",
        key="lg_pass"
    )

    if locked:
        st.markdown(
            "<div class='wp-msg wp-lock'>🔒 Trop de tentatives. Rechargez la page pour réessayer.</div>",
            unsafe_allow_html=True
        )
    else:
        if st.button("Se connecter", key="lg_btn"):
            if not username or not password:
                st.markdown(
                    "<div class='wp-msg wp-err'>Veuillez saisir votre identifiant et votre mot de passe.</div>",
                    unsafe_allow_html=True
                )
            elif _do_login(username, password):
                st.markdown(
                    "<div class='wp-msg wp-ok'>✓ Authentification réussie — redirection…</div>",
                    unsafe_allow_html=True
                )
                time.sleep(0.5)
                st.rerun()
            else:
                st.session_state.wp_attempts += 1
                rem = 5 - st.session_state.wp_attempts
                hint = f"Il vous reste {rem} tentative(s)." if rem > 0 else "Session verrouillée."
                st.markdown(
                    f"<div class='wp-msg wp-err'>Identifiant ou mot de passe incorrect.<br><span style='opacity:0.8;font-size:0.74rem;'>{hint}</span></div>",
                    unsafe_allow_html=True
                )

    st.markdown(
        f"<div class='wp-footer'>2026 · WealthPoint Analytics · Usage interne uniquement</div>",
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# LANDING PAGE (post-login)
# =============================================================================

def render_landing():
    st.markdown(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300&family=DM+Sans:wght@300;400;500&display=swap');

      html, body, [class*="css"] {{
        font-family: 'DM Sans', sans-serif;
        background-color: {WHITE};
        color: {GREY_900};
      }}

      .block-container {{ padding: 2rem 3rem 3rem 3rem; max-width: 1200px; }}

      [data-testid="stSidebar"] {{
        background-color: {PRIMARY_WASH} !important;
        border-right: 1px solid {PRIMARY_PALE};
      }}
      [data-testid="stSidebarNav"] a {{
        border-radius: 4px; color: {GREY_700} !important;
        font-size: 0.82rem !important; padding: 0.45rem 0.9rem !important;
      }}
      [data-testid="stSidebarNav"] a:hover {{
        background: {PRIMARY_PALE} !important; color: {PRIMARY_DARK} !important;
      }}
      [data-testid="stSidebarNav"] [aria-current="page"] {{
        background: {PRIMARY_PALE} !important; color: {PRIMARY_DARK} !important;
        font-weight: 500 !important; border-left: 3px solid {PRIMARY};
      }}

      .mc {{
        background: {WHITE};
        border: 1px solid {PRIMARY_PALE};
        border-radius: 6px;
        padding: 1.6rem 1.8rem;
        cursor: pointer;
        transition: box-shadow 0.2s, transform 0.15s;
        text-decoration: none !important;
        display: block;
      }}
      .mc:hover {{
        box-shadow: 0 4px 18px rgba(177,144,105,0.15);
        transform: translateY(-2px);
      }}
      .mc-num {{
        font-size: 0.62rem; letter-spacing: 0.16em;
        text-transform: uppercase; font-weight: 500; margin-bottom: 0.6rem;
      }}
      .mc-title {{
        font-family: 'Cormorant Garamond', serif; font-size: 1.5rem;
        font-weight: 400; color: {GREY_900}; margin-bottom: 0.55rem;
      }}
      .mc-desc {{
        font-size: 0.78rem; color: {GREY_500};
        line-height: 1.7; margin-bottom: 1.1rem;
      }}
      .mc-tags {{ display: flex; gap: 0.35rem; flex-wrap: wrap; }}
      .tag {{
        font-size: 0.6rem; padding: 0.15rem 0.5rem; border-radius: 2px;
        letter-spacing: 0.07em; text-transform: uppercase; font-weight: 500;
      }}

      .stButton > button {{
        background: transparent !important;
        color: {GREY_700} !important;
        border: 1px solid {PRIMARY_PALE} !important;
        border-radius: 3px !important;
        font-size: 0.78rem !important;
        letter-spacing: 0.06em !important;
        padding: 0.4rem 1rem !important;
        width: 100% !important;
        transition: all 0.15s !important;
      }}
      .stButton > button:hover {{
        background: {RED_PALE} !important;
        color: {RED_SOFT} !important;
        border-color: {RED_SOFT} !important;
      }}
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(f"""
        <div style='padding:0.3rem 0 1rem 0;'>
          <div style='font-family:Cormorant Garamond,serif;font-size:1.55rem;
                      font-weight:300;color:{PRIMARY_DARK};letter-spacing:0.08em;'>
            ◈ WealthPoint
          </div>
          <div style='font-size:0.62rem;color:{GREY_500};letter-spacing:0.18em;
                      text-transform:uppercase;margin-top:0.12rem;'>Analytics Platform</div>
        </div>
        <hr style='border:none;border-top:1px solid {PRIMARY_PALE};margin:0 0 1rem 0;'/>
        <div style='font-size:0.7rem;color:{GREY_500};margin-bottom:0.25rem;'>Connecté en tant que</div>
        <div style='font-size:0.82rem;color:{PRIMARY_DARK};font-weight:500;margin-bottom:1.3rem;'>
          ◉ {st.session_state.get('wp_user', '')}
        </div>
        """, unsafe_allow_html=True)
        if st.button("← Se déconnecter"):
            _do_logout()
            st.rerun()

    st.markdown(f"""
    <div style='text-align:center;padding:2.5rem 0 1.4rem 0;'>
      <div style='font-family:Cormorant Garamond,serif;font-size:3rem;font-weight:300;
                  color:{GREY_900};letter-spacing:0.06em;line-height:1;'>
        ◈ WealthPoint
      </div>
      <div style='font-size:0.74rem;color:{GREY_500};letter-spacing:0.22em;
                  text-transform:uppercase;margin-top:0.65rem;'>
        Quantitative Analytics Platform &nbsp;·&nbsp; Wealth Management
      </div>
    </div>
    <div style='border-top:1px solid {PRIMARY_PALE};margin:0 auto 2.5rem auto;width:50%;'></div>
    """, unsafe_allow_html=True)

    r1c1, r1c2 = st.columns(2, gap="medium")
    st.text("")
    r2c1, r2c2 = st.columns(2, gap="medium")

    with r1c1:
        st.markdown(f"""
        <a href="/Risk_Analytics" class='mc' style='border-top:3px solid {PRIMARY};'>
          <div class='mc-num' style='color:{PRIMARY_DARK};'>Module 01</div>
          <div class='mc-title'>Risk Analytics</div>
          <div class='mc-desc'>
            Analyse de risque court terme à partir d'un snapshot de positions.
            VaR, CVaR, Monte Carlo avec fat tails, GARCH et corrélations de crise.
          </div>
          <div class='mc-tags'>
            <span class='tag' style='background:{PRIMARY_PALE};color:{PRIMARY_DARK};'>VaR / CVaR</span>
            <span class='tag' style='background:{PRIMARY_PALE};color:{PRIMARY_DARK};'>GARCH(1,1)</span>
            <span class='tag' style='background:{PRIMARY_PALE};color:{PRIMARY_DARK};'>Student-t MC</span>
          </div>
        </a>
        """, unsafe_allow_html=True)

    with r1c2:
        st.markdown(f"""
        <a href="/Wealth_Forecast" class='mc' style='border-top:3px solid {PRIMARY_DARK};'>
          <div class='mc-num' style='color:{PRIMARY_DARK};'>Module 02</div>
          <div class='mc-title'>Wealth Forecast</div>
          <div class='mc-desc'>
            Projection patrimoniale Monte Carlo sur 10 à 50 ans.
            Modélisation des cash-flows, événements de vie et inflation.
          </div>
          <div class='mc-tags'>
            <span class='tag' style='background:{PRIMARY_PALE};color:{PRIMARY_DARK};'>Fan Chart</span>
            <span class='tag' style='background:{PRIMARY_PALE};color:{PRIMARY_DARK};'>Life Events</span>
            <span class='tag' style='background:{PRIMARY_PALE};color:{PRIMARY_DARK};'>P10 / P50 / P90</span>
          </div>
        </a>
        """, unsafe_allow_html=True)

    with r2c1:
        st.markdown("""
        <a href="/Stress_Tests" class='mc' style='border-top:3px solid #7C3AED;'>
          <div class='mc-num' style='color:#5B21B6;'>Module 03</div>
          <div class='mc-title'>Stress Tests V2</div>
          <div class='mc-desc'>
            9 scénarios historiques et custom avec duration repricing,
            FX decomposition, factor model et bootstrap P10/P90.
          </div>
          <div class='mc-tags'>
            <span class='tag' style='background:#EDE9FE;color:#5B21B6;'>9 Scénarios</span>
            <span class='tag' style='background:#EDE9FE;color:#5B21B6;'>Duration</span>
            <span class='tag' style='background:#EDE9FE;color:#5B21B6;'>Bootstrap P10/P90</span>
          </div>
        </a>
        """, unsafe_allow_html=True)

    with r2c2:
        st.markdown("""
        <a href="/Debt_Engine" class='mc' style='border-top:3px solid #0F766E;'>
          <div class='mc-num' style='color:#0F766E;'>Module 04</div>
          <div class='mc-title'>Debt Engine</div>
          <div class='mc-desc'>
            Moteur d'amortissement de dette. Prêts fixed, variable et IO.
            Caps, floors, trajectoires Vasicek et 9 tests mathématiques vérifiés.
          </div>
          <div class='mc-tags'>
            <span class='tag' style='background:#CCFBF1;color:#0F766E;'>Vasicek</span>
            <span class='tag' style='background:#CCFBF1;color:#0F766E;'>IO / Caps / Floors</span>
            <span class='tag' style='background:#CCFBF1;color:#0F766E;'>9 Math Tests</span>
          </div>
        </a>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style='text-align:center;margin-top:3rem;font-size:0.7rem;
                color:{GREY_300};letter-spacing:0.08em;'>
      {datetime.today().strftime('%d %B %Y')} &nbsp;·&nbsp; Pour usage illustratif uniquement
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# ROUTER
# =============================================================================

if _is_authenticated():
    render_landing()
else:
    render_login()