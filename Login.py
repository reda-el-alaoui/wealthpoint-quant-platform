import streamlit as st
import time

st.set_page_config(
    page_title="WealthPoint · Connexion",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
def _users():
    try:
        return dict(st.secrets["users"])
    except Exception:
        return {
            "demo": "wealthpoint2026",
            "admin": "wp-admin-2026",
            "analyst": "quant#2026",
        }

def _check(u, p):
    return _users().get(u.strip().lower()) == p

def authed():
    return st.session_state.get("wp_authenticated", False)

if "wp_attempts" not in st.session_state:
    st.session_state.wp_attempts = 0

if authed():
    try:
        import Home_app  # noqa: F401
    except ModuleNotFoundError:
        st.success(f"Connecté : {st.session_state.get('wp_user', '')}")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("Déconnexion", use_container_width=True):
                st.session_state.update(wp_authenticated=False)
                st.session_state.pop("wp_user", None)
                st.rerun()
    st.stop()

locked = st.session_state.wp_attempts >= 5

# ─────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────
top_space = st.container()
main = st.container()
bottom = st.container()

with top_space:
    st.write("")
    st.write("")

with main:
    left, center, right = st.columns([1.1, 0.9, 1.1], vertical_alignment="center")

    with left:
        st.caption("WEALTHPOINT · ANALYTICS PLATFORM")
        st.title("Connexion sécurisée")
        st.write(
            "Accédez à votre environnement WealthPoint pour consulter vos analyses, "
            "vos données patrimoniales et vos espaces de travail."
        )
        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Accès", "Privé")
        with c2:
            st.metric("Usage", "Interne")

        st.info(
            "Precision analytics for modern wealth management."
        )

    with center:
        with st.container(border=True):
            st.subheader("Se connecter")
            st.caption("Veuillez renseigner vos identifiants.")

            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Identifiant", placeholder="Votre identifiant")
                password = st.text_input(
                    "Mot de passe",
                    placeholder="Votre mot de passe",
                    type="password",
                )

                submitted = st.form_submit_button(
                    "Se connecter",
                    use_container_width=True
                )

            if locked:
                st.error("Compte verrouillé — rechargez la page.")
            elif submitted:
                if not username or not password:
                    st.error("Merci de renseigner l’identifiant et le mot de passe.")
                elif _check(username, password):
                    st.session_state.update(
                        wp_authenticated=True,
                        wp_user=username.strip().lower(),
                        wp_attempts=0,
                    )
                    st.success("Authentification réussie…")
                    time.sleep(0.35)
                    st.rerun()
                else:
                    st.session_state.wp_attempts += 1
                    rem = max(0, 5 - st.session_state.wp_attempts)
                    if rem > 0:
                        st.error(f"Identifiants incorrects — {rem} tentative(s) restante(s).")
                    else:
                        st.error("Identifiants incorrects.")

            with st.expander("Accès démo"):
                st.code(
                    "demo     / wealthpoint2026\n"
                    "admin    / wp-admin-2026\n"
                    "analyst  / quant#2026"
                )

    with right:
        st.caption("ENVIRONNEMENT")
        st.subheader("Un accès simple")
        st.write(
            "Cette version privilégie une structure native Streamlit : plus légère, "
            "plus robuste, et plus facile à maintenir qu’une page pilotée par du HTML/CSS injecté."
        )
        st.divider()
        st.write("• Menu Streamlit visible")
        st.write("• Pas de scroll artificiel")
        st.write("• Structure centrée")
        st.write("• Formulaire stable")

with bottom:
    st.write("")
    st.caption("2026 · WealthPoint Analytics · Usage interne uniquement")