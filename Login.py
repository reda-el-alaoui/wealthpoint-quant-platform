# =============================================================================
# WealthPoint — Login Page
# =============================================================================
# Utilisation :
#   mv Home.py Home_app.py
#   cp Login.py Home.py
#   streamlit run Home.py
#
# Credentials dans .streamlit/secrets.toml :
#   [users]
#   demo    = "wealthpoint2026"
#   admin   = "wp-admin-2026"
#   analyst = "quant#2026"
# =============================================================================

import streamlit as st
import time

st.set_page_config(
    page_title="WealthPoint · Login",
    page_icon="◈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Couleurs (inline pour que Login soit standalone, sans dépendance theme) ──
PRIMARY      = "#B19069"
PRIMARY_DARK = "#8C7050"
PRIMARY_PALE = "#EDE5D8"
PRIMARY_WASH = "#F7F3EE"
GREY_900     = "#1A1A1A"
GREY_700     = "#4A4A4A"
GREY_500     = "#7A7A7A"
GREY_300     = "#C4C4C4"
WHITE        = "#FFFFFF"
RED_SOFT     = "#C0392B"
RED_PALE     = "#FDEDEC"
GREEN_SOFT   = "#27825A"
GREEN_PALE   = "#E9F7EF"

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300&family=DM+Sans:wght@300;400;500&display=swap');

  html, body, [class*="css"] {{
    font-family: 'DM Sans', sans-serif;
    background-color: {PRIMARY_WASH};
    color: {GREY_900};
  }}
  #MainMenu, footer, header {{ visibility: hidden; }}
  [data-testid="stSidebar"],
  [data-testid="collapsedControl"] {{ display: none !important; }}
  .block-container {{ padding: 3rem 1rem !important; max-width: 100% !important; }}

  /* ── Inputs ── */
  [data-testid="stTextInput"] input {{
    border: 1px solid {PRIMARY_PALE} !important;
    border-radius: 3px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
    background: {WHITE} !important;
    color: {GREY_900} !important;
  }}
  [data-testid="stTextInput"] input:focus {{
    border-color: {PRIMARY} !important;
    box-shadow: 0 0 0 2px rgba(177,144,105,0.15) !important;
  }}

  /* ── Button ── */
  .stButton > button {{
    background: {PRIMARY} !important;
    color: {WHITE} !important;
    border: none !important;
    border-radius: 3px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1.5rem !important;
    width: 100% !important;
    margin-top: 0.5rem !important;
  }}
  .stButton > button:hover {{ background: {PRIMARY_DARK} !important; }}

  /* ── Card ── */
  .login-card {{
    background: {WHITE};
    border: 1px solid {PRIMARY_PALE};
    border-top: 4px solid {PRIMARY};
    border-radius: 8px;
    padding: 2.6rem 2.4rem 2.2rem;
    max-width: 420px;
    margin: 0 auto;
    box-shadow: 0 4px 24px rgba(177,144,105,0.10);
  }}
  .login-logo {{
    font-family: 'Cormorant Garamond', serif;
    font-size: 2rem;
    font-weight: 300;
    color: {PRIMARY_DARK};
    letter-spacing: 0.08em;
    text-align: center;
    margin-bottom: 0.15rem;
  }}
  .login-tag {{
    font-size: 0.66rem;
    color: {GREY_500};
    letter-spacing: 0.18em;
    text-transform: uppercase;
    text-align: center;
    margin-bottom: 1.8rem;
  }}
  .login-lbl {{
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {GREY_700};
    font-weight: 500;
    margin-bottom: 0.25rem;
  }}
  .alert-err {{
    background: {RED_PALE};
    border-left: 3px solid {RED_SOFT};
    color: {RED_SOFT};
    padding: 0.6rem 0.85rem;
    border-radius: 0 3px 3px 0;
    font-size: 0.79rem;
    margin-top: 0.6rem;
  }}
  .alert-ok {{
    background: {GREEN_PALE};
    border-left: 3px solid {GREEN_SOFT};
    color: {GREEN_SOFT};
    padding: 0.6rem 0.85rem;
    border-radius: 0 3px 3px 0;
    font-size: 0.79rem;
    margin-top: 0.6rem;
  }}
  .demo-box {{
    background: {PRIMARY_WASH};
    border: 1px solid {PRIMARY_PALE};
    border-radius: 4px;
    padding: 0.65rem 0.85rem;
    font-size: 0.73rem;
    color: {GREY_700};
    line-height: 1.75;
    margin-top: 1.2rem;
  }}
  .demo-box code {{
    font-family: 'Courier New', monospace;
    color: {PRIMARY_DARK};
    font-size: 0.71rem;
  }}
  .login-footer {{
    font-size: 0.67rem;
    color: {GREY_300};
    text-align: center;
    margin-top: 1.4rem;
    letter-spacing: 0.06em;
  }}
  hr.lhr {{
    border: none;
    border-top: 1px solid {PRIMARY_PALE};
    margin: 1.4rem 0 1.2rem;
  }}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# AUTH HELPERS
# =============================================================================

def _load_users() -> dict:
    try:
        return dict(st.secrets["users"])
    except Exception:
        # Fallback demo credentials si secrets.toml absent
        return {
            "demo":    "wealthpoint2026",
            "admin":   "wp-admin-2026",
            "analyst": "quant#2026",
        }


def _check(username: str, password: str) -> bool:
    return _load_users().get(username.strip().lower()) == password


def is_authenticated() -> bool:
    return st.session_state.get("wp_authenticated", False)


# =============================================================================
# REDIRECT SI DÉJÀ CONNECTÉ
# =============================================================================
if is_authenticated():
    try:
        import Home_app  # noqa: F401 — affiche la landing page principale
    except ModuleNotFoundError:
        st.success(f"✅ Connecté : **{st.session_state.get('wp_user', '')}**")
        st.info("Renommez `Home.py` → `Home_app.py` pour activer la redirection.")
        if st.button("Se déconnecter"):
            st.session_state["wp_authenticated"] = False
            st.session_state.pop("wp_user", None)
            st.rerun()
    st.stop()


# =============================================================================
# LOGIN FORM
# =============================================================================
st.markdown("<div class='login-card'>", unsafe_allow_html=True)

st.markdown("""
<div class='login-logo'>◈ WealthPoint</div>
<div class='login-tag'>Analytics Platform · Accès sécurisé</div>
<hr class='lhr'/>
""", unsafe_allow_html=True)

if "wp_attempts" not in st.session_state:
    st.session_state.wp_attempts = 0

locked = st.session_state.wp_attempts >= 5

st.markdown("<div class='login-lbl'>Identifiant</div>", unsafe_allow_html=True)
username = st.text_input("u", placeholder="Votre identifiant",
                         label_visibility="collapsed", key="li_user")

st.markdown("<div class='login-lbl' style='margin-top:0.8rem;'>Mot de passe</div>",
            unsafe_allow_html=True)
password = st.text_input("p", placeholder="Votre mot de passe", type="password",
                         label_visibility="collapsed", key="li_pass")

if locked:
    st.markdown("""
    <div class='alert-err'>
      🔒 Trop de tentatives incorrectes. Rechargez la page pour réessayer.
    </div>""", unsafe_allow_html=True)
else:
    if st.button("Se connecter", key="li_btn"):
        if not username or not password:
            st.markdown("<div class='alert-err'>Veuillez remplir les deux champs.</div>",
                        unsafe_allow_html=True)
        elif _check(username, password):
            st.session_state["wp_authenticated"] = True
            st.session_state["wp_user"]          = username.strip().lower()
            st.session_state.wp_attempts         = 0
            st.markdown("<div class='alert-ok'>✓ Authentification réussie — redirection…</div>",
                        unsafe_allow_html=True)
            time.sleep(0.5)
            st.rerun()
        else:
            st.session_state.wp_attempts += 1
            rem = 5 - st.session_state.wp_attempts
            msg = f"Identifiant ou mot de passe incorrect. {rem} tentative(s) restante(s)." \
                  if rem > 0 else "Identifiant ou mot de passe incorrect."
            st.markdown(f"<div class='alert-err'>{msg}</div>", unsafe_allow_html=True)

st.markdown(f"""
<div class='demo-box'>
  <strong>Accès démo</strong><br/>
  <code>demo</code> / <code>wealthpoint2026</code><br/>
  <code>admin</code> / <code>wp-admin-2026</code><br/>
  <code>analyst</code> / <code>quant#2026</code>
</div>
<div class='login-footer'>
  2026 · WealthPoint Analytics · Usage interne uniquement
</div>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
