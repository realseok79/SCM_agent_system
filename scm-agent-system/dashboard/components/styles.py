import streamlit as st
import matplotlib as mpl
import matplotlib.font_manager as fm

try:
    mpl.rcParams['axes.unicode_minus'] = False
    installed_fonts = {f.name for f in fm.fontManager.ttflist}
    korean_fonts = ['NanumGothic', 'NanumBarunGothic', 'AppleGothic', 'Malgun Gothic']
    selected_font = next((font for font in korean_fonts if font in installed_fonts), None)
    if selected_font:
        mpl.rcParams['font.family'] = selected_font
    else:
        mpl.rcParams['font.family'] = 'sans-serif'
except Exception:
    pass

BG = '#0d1117'
TX = '#c9d1d9'

def sax(ax):
    ax.tick_params(colors=TX, labelsize=7)
    for spine in ax.spines.values():
        spine.set_color('#30363d')
    ax.yaxis.grid(True, color='#30363d', alpha=0.3, ls=":")
    ax.xaxis.grid(False)

def inject_custom_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Font application and FOUT prevention */
html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif !important;
    font-display: swap;
}

/* Base App style with GitHub dark theme canvas */
.stApp {
    background-color: #0d1117 !important;
    color: #c9d1d9 !important;
}

/* Streamlit native block overrides for structural alignment */
[data-testid="stSidebar"],
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stAppViewContainer"] {
    background-color: #0d1117 !important;
}

/* GitHub-style Sidebar layout separation */
[data-testid="stSidebar"] {
    background-color: #0d1117 !important;
    border-right: 1px solid #30363d !important;
    padding-top: 2rem !important;
}

.block-container, 
[data-testid="stMainBlockContainer"], 
[data-testid="stAppViewBlockContainer"] {
    padding: 0 2rem 0 2rem !important;
    max-width: 98% !important;
    width: 98% !important;
}

/* GitHub Premium Header section */
.hdr {
    background: #161b22 !important;
    border-bottom: 1px solid #30363d !important;
    padding: 24px 32px !important;
    margin: 0 -2rem 1.5rem !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}
.hdr-t {
    font-size: 22px !important;
    font-weight: 600 !important;
    color: #f0f6fc !important;
    letter-spacing: -0.01em;
}
.hdr-s {
    font-size: 13px !important;
    color: #8b949e !important;
    margin-top: 6px !important;
}

/* Structured Section Header */
.sec {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #c9d1d9 !important;
    text-transform: none !important;
    letter-spacing: normal !important;
    border-bottom: 1px solid #30363d !important;
    padding-bottom: 8px !important;
    margin: 1.6rem 0 1rem !important;
}

/* KPI Card Grid and GitHub Cards */
.kpi-grid, .kg {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-bottom: 1rem;
}
.kpi-card, .kc {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    padding: 16px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    box-shadow: none !important;
}
.kpi-card:hover, .kc:hover {
    border-color: #58a6ff !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}
.kpi-label, .kl {
    font-size: 10px !important;
    color: #8b949e !important;
    text-transform: uppercase;
    letter-spacing: .05em;
    margin-bottom: 6px;
}
.kpi-value, .kv {
    font-size: 22px !important;
    font-weight: 600 !important;
    color: #f0f6fc !important;
    line-height: 1.2;
}
.kpi-value--blue, .kv.b { color: #58a6ff !important; }
.kpi-value--green, .kv.g { color: #3fb950 !important; }
.kpi-value--yellow, .kv.y { color: #d29922 !important; }
.kpi-value--red, .kv.r { color: #f85149 !important; }

.kpi-unit, .ku {
    font-size: 10px !important;
    color: #8b949e !important;
    margin-top: 6px;
}
.kpi-badge, .kb {
    display: inline-block;
    font-size: 10px !important;
    font-weight: 500 !important;
    border-radius: 4px !important;
    padding: 2px 8px !important;
    margin-top: 8px !important;
    border: 1px solid !important;
}
.kpi-badge--ok, .kb.ok {
    background: rgba(56, 139, 253, 0.1) !important;
    color: #58a6ff !important;
    border-color: rgba(56, 139, 253, 0.4) !important;
}
.kpi-badge--warning, .kb.w {
    background: rgba(248, 81, 73, 0.1) !important;
    color: #f85149 !important;
    border-color: rgba(248, 81, 73, 0.4) !important;
}

/* Structured Functional Area Card Containers */
.cc {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    padding: 20px !important;
    margin-bottom: 12px !important;
    box-shadow: none !important;
    transition: border-color 0.2s ease !important;
}
.cc:hover {
    border-color: #30363d !important;
}
.ct {
    font-size: 14px !important;
    font-weight: 600 !important;
    color: #f0f6fc !important;
    margin-bottom: 12px !important;
    display: flex;
    align-items: center;
    gap: 8px;
}
.dt {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}

/* Premium Structured Table (GitHub Dark-styled) */
.gt {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    overflow: hidden;
    margin-bottom: 12px;
    width: 100%;
}
.gt table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}
.gt th {
    background: #161b22 !important;
    color: #8b949e !important;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .05em;
    padding: 10px 14px;
    text-align: left;
    border-bottom: 1px solid #30363d !important;
}
.gt td {
    padding: 10px 14px;
    border-bottom: 1px solid #21262d !important;
    color: #c9d1d9 !important;
}

/* Status block indicators */
.alert-panel, .ep {
    border-radius: 6px !important;
    padding: 14px 18px !important;
    margin-bottom: 12px !important;
    border: 1px solid #30363d !important;
    border-left: 4px solid !important;
    box-shadow: none !important;
}
.alert-panel--critical, .ec {
    background: rgba(248, 81, 73, 0.05) !important;
    border-left-color: #f85149 !important;
}
.alert-panel--warning, .ew {
    background: rgba(210, 153, 34, 0.05) !important;
    border-left-color: #d29922 !important;
}
.alert-panel--normal, .en {
    background: rgba(63, 185, 80, 0.05) !important;
    border-left-color: #3fb950 !important;
}
.alert-title, .et {
    font-size: 13px !important;
    font-weight: 600 !important;
    margin-bottom: 6px !important;
}
.alert-body, .eb {
    font-size: 12px !important;
    color: #8b949e !important;
    line-height: 1.6 !important;
}

/* Premium Sidebar Menu Navigation */
div[data-testid="stRadio"] > label {
    display: none !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px 0;
}
div[data-testid="stRadio"] div[role="radiogroup"] label {
    background: transparent !important;
    border: 1px solid transparent !important;
    padding: 6px 12px !important;
    border-radius: 6px !important;
    color: #8b949e !important;
    cursor: pointer;
    transition: all 0.15s ease !important;
    display: flex;
    align-items: center;
    font-size: 13.5px !important;
    font-weight: 500 !important;
}
/* Hide standard Streamlit radio UI indicators */
div[data-testid="stRadio"] div[role="radiogroup"] label [data-testid="stWidgetSelectedBorder"],
div[data-testid="stRadio"] div[role="radiogroup"] label [data-testid="stWidgetUnselectedBorder"],
div[data-testid="stRadio"] div[role="radiogroup"] label input[type="radio"] {
    display: none !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] label:hover {
    background: #161b22 !important;
    color: #c9d1d9 !important;
    border-color: #30363d !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input[checked]) {
    background: #21262d !important;
    color: #ffffff !important;
    border: 1px solid #30363d !important;
    border-left: 3px solid #58a6ff !important;
    border-radius: 3px 6px 6px 3px !important;
    font-weight: 600 !important;
}

/* Premium UI Controls Form Inputs */
div[data-baseweb="select"],
div[data-baseweb="input"],
div[data-baseweb="textarea"] {
    background-color: #0d1117 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
}
div[role="listbox"] {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
}
/* Primary button (GitHub-style active green) */
button[kind="primary"] {
    background-color: #238636 !important;
    color: #ffffff !important;
    font-weight: 500 !important;
    border: 1px solid #2ea44f !important;
    border-radius: 6px !important;
    padding: 6px 16px !important;
    transition: background-color 0.2s ease !important;
}
button[kind="primary"]:hover {
    background-color: #2ea44f !important;
    border-color: #3fb950 !important;
}
/* Secondary button (GitHub-style flat grey button) */
button[kind="secondary"] {
    background-color: #21262d !important;
    color: #c9d1d9 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    padding: 6px 16px !important;
    transition: all 0.2s ease !important;
}
button[kind="secondary"]:hover {
    background-color: #30363d !important;
    border-color: #8b949e !important;
}

/* Responsive adjustments for mobile/tablet devices */
@media (max-width: 992px) {
    .kpi-grid, .kg {
        grid-template-columns: repeat(3, 1fr) !important;
    }
}
@media (max-width: 768px) {
    .kpi-grid, .kg {
        grid-template-columns: repeat(2, 1fr) !important;
    }
    .block-container, 
    [data-testid="stMainBlockContainer"], 
    [data-testid="stAppViewBlockContainer"] {
        padding: 0 1rem 0 1rem !important;
    }
}
@media (max-width: 480px) {
    .kpi-grid, .kg {
        grid-template-columns: 1fr !important;
    }
}
</style>
<meta name="google" content="notranslate">
<script>
    // React/Streamlit Google Translate DOM Reconciliation Conflict Prevention
    document.documentElement.setAttribute('translate', 'no');
    document.documentElement.classList.add('notranslate');
</script>
""", unsafe_allow_html=True)

