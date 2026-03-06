# ── wealthpoint_theme.py ─────────────────────────────────────────────────────
# Shared design tokens, CSS, and helpers for the WealthPoint platform

import streamlit as st

# ── COLOUR PALETTE ────────────────────────────────────────────────────────────
PRIMARY       = "#B19069"
PRIMARY_DARK  = "#8C7050"
PRIMARY_MID   = "#9E7F5A"
PRIMARY_LIGHT = "#CDB898"
PRIMARY_PALE  = "#EDE5D8"
PRIMARY_WASH  = "#F7F3EE"

GREY_900 = "#1A1A1A"
GREY_700 = "#4A4A4A"
GREY_500 = "#7A7A7A"
GREY_300 = "#C4C4C4"
GREY_150 = "#E8E8E8"
GREY_100 = "#F2F2F2"
WHITE    = "#FFFFFF"

RED_SOFT   = "#C0392B"
RED_PALE   = "#FDEDEC"
GREEN_SOFT = "#27825A"
GREEN_PALE = "#E9F7EF"
AMBER      = "#A04000"
AMBER_PALE = "#FDF2E9"

PALETTE_AC = {
    "Equity":       PRIMARY,
    "Fixed Income": PRIMARY_DARK,
    "Alternatives": PRIMARY_LIGHT,
}

# ── MATPLOTLIB DEFAULTS ────────────────────────────────────────────────────────
def apply_mpl_style():
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor":   WHITE,
        "axes.facecolor":     WHITE,
        "axes.edgecolor":     GREY_300,
        "axes.labelcolor":    GREY_700,
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "axes.grid":          True,
        "grid.color":         GREY_100,
        "grid.linewidth":     0.6,
        "xtick.color":        GREY_500,
        "ytick.color":        GREY_500,
        "xtick.labelsize":    8,
        "ytick.labelsize":    8,
        "axes.labelsize":     8.5,
        "axes.titlesize":     9.5,
        "axes.titlecolor":    GREY_900,
        "axes.titleweight":   "normal",
        "font.family":        "sans-serif",
        "font.size":          8.5,
        "legend.fontsize":    8,
        "legend.frameon":     False,
        "figure.dpi":         120,
    })

# ── GLOBAL CSS ─────────────────────────────────────────────────────────────────
def inject_global_css():
    st.markdown(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300&family=DM+Sans:wght@300;400;500&display=swap');

      html, body, [class*="css"] {{
        font-family: 'DM Sans', sans-serif;
        background-color: {WHITE};
        color: {GREY_900};
      }}


      .block-container {{ padding: 1.8rem 2.8rem 3rem 2.8rem; max-width: 1440px; }}

      /* ── Sidebar ── */
      [data-testid="stSidebar"] {{
        background-color: {PRIMARY_WASH} !important;
        border-right: 1px solid {PRIMARY_PALE};
      }}
      [data-testid="stSidebar"] label,
      [data-testid="stSidebar"] p {{
        color: {GREY_700} !important;
        font-size: 0.82rem !important;
      }}
      [data-testid="stSidebar"] .stSelectbox > div > div {{
        background: {WHITE};
        border-color: {PRIMARY_PALE} !important;
      }}

      /* ── Nav pills in sidebar ── */
      [data-testid="stSidebarNav"] {{
        padding-top: 0.5rem;
      }}
      [data-testid="stSidebarNav"] a {{
        border-radius: 4px;
        color: {GREY_700} !important;
        font-size: 0.82rem !important;
        padding: 0.45rem 0.9rem !important;
        letter-spacing: 0.03em;
      }}
      [data-testid="stSidebarNav"] a:hover {{
        background: {PRIMARY_PALE} !important;
        color: {PRIMARY_DARK} !important;
      }}
      [data-testid="stSidebarNav"] [aria-current="page"] {{
        background: {PRIMARY_PALE} !important;
        color: {PRIMARY_DARK} !important;
        font-weight: 500 !important;
        border-left: 3px solid {PRIMARY};
      }}

      /* ── Tabs ── */
      .stTabs [data-baseweb="tab-list"] {{
        gap: 0;
        border-bottom: 2px solid {PRIMARY_PALE};
        background: transparent;
      }}
      .stTabs [data-baseweb="tab"] {{
        font-family: 'DM Sans', sans-serif;
        font-size: 0.77rem;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: {GREY_500};
        background: transparent;
        border: none;
        padding: 0.65rem 1.2rem;
      }}
      .stTabs [aria-selected="true"] {{
        color: {PRIMARY_DARK} !important;
        border-bottom: 2px solid {PRIMARY} !important;
        font-weight: 500 !important;
        background: transparent !important;
      }}

      /* ── Buttons ── */
      .stButton > button {{
        background: {PRIMARY};
        color: {WHITE};
        border: none;
        border-radius: 3px;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.82rem;
        letter-spacing: 0.06em;
        padding: 0.5rem 1.4rem;
        transition: background 0.18s ease;
      }}
      .stButton > button:hover {{ background: {PRIMARY_DARK} !important; color: {WHITE} !important; }}

      /* ── Metrics ── */
      div[data-testid="stMetricValue"] {{
        color: {PRIMARY_DARK};
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.7rem !important;
        font-weight: 600;
      }}
      div[data-testid="stMetricLabel"] {{
        font-size: 0.7rem !important;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: {GREY_500} !important;
      }}

      /* ── DataFrames ── */
      .stDataFrame {{ border: 1px solid {PRIMARY_PALE}; border-radius: 4px; }}

      /* ── Spinner ── */
      .stSpinner > div {{ border-top-color: {PRIMARY} !important; }}

      /* ── Expander ── */
      details summary {{ color: {GREY_700} !important; font-size: 0.82rem; }}

      /* ── Sliders ── */
      [data-testid="stSlider"] [data-baseweb="slider"] [data-baseweb="thumb"] {{
        background: {PRIMARY} !important;
        border-color: {PRIMARY} !important;
      }}
      [data-testid="stSlider"] [data-baseweb="slider"] [data-baseweb="track-fill"] {{
        background: {PRIMARY_LIGHT} !important;
      }}

      /* ── Shared component classes ── */
      .wp-page-header {{
        border-bottom: 2px solid {PRIMARY};
        padding-bottom: 1.1rem;
        margin-bottom: 1.8rem;
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
      }}
      .wp-page-title {{
        font-family: 'Cormorant Garamond', serif;
        font-size: 2.2rem;
        font-weight: 300;
        color: {GREY_900};
        letter-spacing: 0.04em;
        margin: 0; line-height: 1;
      }}
      .wp-page-subtitle {{
        font-size: 0.74rem;
        color: {GREY_500};
        letter-spacing: 0.13em;
        text-transform: uppercase;
        margin-top: 0.25rem;
      }}
      .wp-feature-badge {{
        font-size: 0.65rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: {PRIMARY_DARK};
        background: {PRIMARY_PALE};
        border: 1px solid {PRIMARY_LIGHT};
        border-radius: 2px;
        padding: 0.2rem 0.6rem;
        font-weight: 500;
      }}
      .wp-section {{
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.2rem;
        font-weight: 400;
        color: {GREY_900};
        letter-spacing: 0.05em;
        border-left: 3px solid {PRIMARY};
        padding-left: 0.65rem;
        margin: 1.6rem 0 0.9rem 0;
      }}
      .kpi-card {{
        background: {WHITE};
        border: 1px solid {PRIMARY_PALE};
        border-top: 3px solid {PRIMARY};
        border-radius: 4px;
        padding: 1rem 1.2rem;
      }}
      .kpi-label {{
        font-size: 0.68rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: {GREY_500};
        margin-bottom: 0.35rem;
      }}
      .kpi-value {{
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.75rem;
        font-weight: 600;
        color: {PRIMARY_DARK};
        line-height: 1;
      }}
      .kpi-sub {{ font-size: 0.72rem; color: {GREY_500}; margin-top: 0.25rem; }}
      .kpi-neg {{ color: {RED_SOFT}; }}
      .kpi-pos {{ color: {GREEN_SOFT}; }}

      .wp-table {{ width:100%; border-collapse:collapse; font-size:0.81rem; }}
      .wp-table th {{
        background: {PRIMARY_WASH};
        color: {GREY_700};
        font-size: 0.67rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        padding: 0.5rem 0.75rem;
        text-align: right;
        border-bottom: 1px solid {PRIMARY_PALE};
      }}
      .wp-table th:first-child {{ text-align: left; }}
      .wp-table td {{
        padding: 0.45rem 0.75rem;
        border-bottom: 1px solid {GREY_100};
        text-align: right;
        color: {GREY_700};
      }}
      .wp-table td:first-child {{ text-align:left; color:{GREY_900}; font-weight:500; }}
      .wp-table tr:hover td {{ background: {PRIMARY_WASH}; }}
      .td-neg {{ color:{RED_SOFT}; font-weight:500; }}
      .td-pos {{ color:{GREEN_SOFT}; font-weight:500; }}

      .wp-badge {{ display:inline-block; padding:0.22rem 0.65rem; border-radius:2px;
                   font-size:0.68rem; letter-spacing:0.08em; text-transform:uppercase; font-weight:500; }}
      .badge-n  {{ background:{PRIMARY_PALE}; color:{PRIMARY_DARK}; }}
      .badge-w  {{ background:{AMBER_PALE}; color:{AMBER}; }}
      .badge-c  {{ background:{RED_PALE}; color:{RED_SOFT}; }}

      .wp-disclaimer {{
        background: {PRIMARY_WASH};
        border-left: 3px solid {PRIMARY_LIGHT};
        padding: 0.75rem 1rem;
        font-size: 0.72rem;
        color: {GREY_500};
        border-radius: 0 4px 4px 0;
        margin-top: 0.8rem;
        line-height: 1.55;
      }}
      .wp-warn {{
        background: {AMBER_PALE};
        border-left: 3px solid {AMBER};
        padding: 0.7rem 1rem;
        font-size: 0.75rem;
        color: {GREY_700};
        border-radius: 0 4px 4px 0;
        margin: 0.8rem 0;
        line-height: 1.5;
      }}
      hr.wp-hr {{
        border: none;
        border-top: 1px solid {PRIMARY_PALE};
        margin: 1.4rem 0;
      }}
    </style>
    """, unsafe_allow_html=True)


def sidebar_brand(subtitle: str):
    """Render the WealthPoint logo block in the sidebar."""
    st.markdown(f"""
    <div style='padding:0.2rem 0 1.1rem 0;'>
      <div style='font-family:Cormorant Garamond,serif;font-size:1.6rem;
                  font-weight:300;color:{PRIMARY_DARK};letter-spacing:0.08em;'>
        ◈ WealthPoint
      </div>
      <div style='font-size:0.62rem;color:{GREY_500};letter-spacing:0.18em;
                  text-transform:uppercase;margin-top:0.15rem;'>{subtitle}</div>
    </div>
    <hr style='border:none;border-top:1px solid {PRIMARY_PALE};margin:0 0 1rem 0;'/>
    """, unsafe_allow_html=True)


def sidebar_section(label: str):
    st.markdown(f"""
    <div style='font-size:0.65rem;letter-spacing:0.14em;text-transform:uppercase;
                color:{PRIMARY_DARK};font-weight:500;margin:1.1rem 0 0.4rem 0;
                padding-bottom:0.3rem;border-bottom:1px solid {PRIMARY_PALE};'>
      {label}
    </div>""", unsafe_allow_html=True)


def page_header(title: str, subtitle: str, badge: str = ""):
    badge_html = f"<span class='wp-feature-badge'>{badge}</span>" if badge else ""
    st.markdown(f"""
    <div class='wp-page-header'>
      <div>
        <div class='wp-page-title'>{title}</div>
        <div class='wp-page-subtitle'>{subtitle}</div>
      </div>
      {badge_html}
    </div>""", unsafe_allow_html=True)


def section(label: str):
    st.markdown(f"<div class='wp-section'>{label}</div>", unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str = "", neg: bool = False, pos: bool = False):
    val_cls = "kpi-neg" if neg else ("kpi-pos" if pos else "")
    return f"""<div class='kpi-card'>
      <div class='kpi-label'>{label}</div>
      <div class='kpi-value {val_cls}'>{value}</div>
      {'<div class="kpi-sub">'+sub+'</div>' if sub else ''}
    </div>"""


def fmt_chf(v: float) -> str:
    if abs(v) >= 1e6: return f"CHF {v/1e6:,.1f}M"
    if abs(v) >= 1e3: return f"CHF {v/1e3:,.0f}k"
    return f"CHF {v:,.0f}"
