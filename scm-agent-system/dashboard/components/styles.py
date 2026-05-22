# dashboard/components/styles.py
import streamlit as st

BG = '#0a192f'
TX = '#ccd6f6'

def sax(ax):
    ax.tick_params(colors=TX, labelsize=7)
    for spine in ax.spines.values():
        spine.set_color('rgba(255, 255, 255, 0.12)')
    ax.yaxis.grid(True, color="rgba(255, 255, 255, 0.08)", alpha=0.5, ls=":")
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

/* Base App Deep Navy background and default text color */
.stApp {
    background: radial-gradient(circle at 50% 50%, #172a45, #0a192f) !important;
    color: #ccd6f6 !important;
}

/* Streamlit container backgrounds transparent */
[data-testid="stSidebar"],
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stAppViewContainer"] {
    background-color: transparent !important;
}

/* Glassmorphism sidebar styling */
[data-testid="stSidebar"] {
    background: rgba(10, 25, 47, 0.6) !important;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

.block-container, 
[data-testid="stMainBlockContainer"], 
[data-testid="stAppViewBlockContainer"] {
    padding: 0 1.5rem 0 1.5rem !important;
    max-width: 98% !important;
    width: 98% !important;
}

/* Glassmorphism Header */
.hdr {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding: 20px 24px;
    margin: 0 -1.5rem 1rem !important;
    border-radius: 0 0 16px 16px;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
}
.hdr-t {
    font-size: 20px;
    font-weight: 700;
    color: #64ffda;
    letter-spacing: -0.02em;
    text-shadow: 0 0 10px rgba(100, 255, 218, 0.2);
}
.hdr-s {
    font-size: 12px;
    color: #8892b0;
    margin-top: 4px;
}

/* Section Header */
.sec {
    font-size: 12px;
    font-weight: 600;
    color: #64ffda;
    text-transform: uppercase;
    letter-spacing: .08em;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 6px;
    margin: 1.2rem 0 0.6rem;
}

/* Glassmorphism Grid and Cards */
.kg {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin-bottom: 0.6rem;
}
.kc {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 12px 16px;
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
}
.kc:hover {
    border-color: rgba(100, 255, 218, 0.4);
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(100, 255, 218, 0.15);
}
.kl {
    font-size: 9.5px;
    color: #8892b0;
    text-transform: uppercase;
    letter-spacing: .05em;
    margin-bottom: 5px;
}
.kv {
    font-size: 24px;
    font-weight: 600;
    color: #ccd6f6;
    line-height: 1.1;
}
.kv.b { color: #64ffda; }
.kv.g { color: #00e5a0; }
.kv.y { color: #ffc107; }
.kv.r { color: #ff5c5c; }

.ku {
    font-size: 9.5px;
    color: #8892b0;
    margin-top: 4px;
}
.kb {
    display: inline-block;
    font-size: 9px;
    font-weight: 500;
    border-radius: 4px;
    padding: 2px 6px;
    margin-top: 6px;
    border: 1px solid;
}
.kb.ok {
    background: rgba(0, 229, 160, 0.1);
    color: #00e5a0;
    border-color: rgba(0, 229, 160, 0.3);
}
.kb.w {
    background: rgba(255, 92, 92, 0.1);
    color: #ff5c5c;
    border-color: rgba(255, 92, 92, 0.3);
}

.cc {
    background: rgba(255, 255, 255, 0.02);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 8px;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
}
.cc:hover {
    border-color: rgba(255, 255, 255, 0.15);
}
.ct {
    font-size: 12px;
    font-weight: 600;
    color: #ccd6f6;
    margin-bottom: 8px;
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

/* Glassmorphism Table */
.gt {
    background: rgba(255, 255, 255, 0.02);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 8px;
    width: 100%;
}
.gt table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}
.gt th {
    background: rgba(255, 255, 255, 0.04);
    color: #8892b0;
    font-weight: 600;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: .05em;
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.gt td {
    padding: 8px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    color: #ccd6f6;
}

.ep {
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    border-left: 4px solid;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}
.ec {
    background: rgba(255, 92, 92, 0.04);
    border-color: #ff5c5c;
}
.ew {
    background: rgba(255, 193, 7, 0.04);
    border-color: #ffc107;
}
.en {
    background: rgba(0, 229, 160, 0.04);
    border-color: #00e5a0;
}
.et {
    font-size: 12.5px;
    font-weight: 600;
    margin-bottom: 4px;
}
.eb {
    font-size: 11.5px;
    color: #8892b0;
    line-height: 1.6;
}

/* Custom styles for Streamlit widgets to fit Glassmorphism */
div[data-baseweb="select"] {
    background-color: rgba(255, 255, 255, 0.02) !important;
    border-radius: 8px !important;
}
div[role="listbox"] {
    background-color: #0a192f !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
}
button[kind="primary"] {
    background-color: #64ffda !important;
    color: #0a192f !important;
    font-weight: 600 !important;
    border: none !important;
}
button[kind="secondary"] {
    background-color: rgba(255, 255, 255, 0.04) !important;
    color: #ccd6f6 !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
}
</style>
""", unsafe_allow_html=True)

