# dashboard/components/common.py
import streamlit as st

def render_header(title: str, subtitle: str):
    """
    Renders the premium top header bar.
    """
    st.markdown(f"""
    <div class="hdr">
        <div>
            <div class="hdr-t">{title}</div>
            <div class="hdr-s">{subtitle}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_section(title: str, style_str: str = ""):
    """
    Renders a section divider header.
    """
    style_attr = f' style="{style_str}"' if style_str else ''
    st.markdown(f'<div class="sec"{style_attr}>{title}</div>', unsafe_allow_html=True)

def render_kpi_card(label: str, value: str, unit: str = None, color_class: str = ""):
    """
    Renders a premium KPI metric card.
    """
    unit_html = f'<div class="ku">{unit}</div>' if unit else ''
    st.markdown(f"""
    <div class="kc">
        <div class="kl">{label}</div>
        <div class="kv {color_class}">{value}</div>
        {unit_html}
    </div>
    """, unsafe_allow_html=True)

def render_alert_panel(title: str, body: str, severity: str = "normal"):
    """
    Renders a status alert card panel (critical, warning, normal).
    """
    sev_class = "ec" if severity == "critical" else ("ew" if severity == "warning" else "en")
    st.markdown(f"""
    <div class="ep {sev_class}">
        <div class="et">{title}</div>
        <div class="eb">{body}</div>
    </div>
    """, unsafe_allow_html=True)
