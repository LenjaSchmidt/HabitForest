# HabitForest — minimal habit tracker with a visible forest
# Ugly on purpose. The first AI prompt turns the emoji forest into real SVG.

import json
import sqlite3
import secrets
from datetime import date, timedelta
from html import escape
from pathlib import Path
from textwrap import dedent

import streamlit as st
from integrations.step_tracker import (
    GoogleFitOAuthError,
    GoogleFitStepTrackerProvider,
    GOOGLE_FIT_ESTIMATED_STEPS_SOURCE,
    SimulatedStepTrackerProvider,
    build_google_fit_auth_url,
    exchange_google_fit_code,
)

st.set_page_config(page_title="HabitForest", layout="centered")

if "google_fit_connected" not in st.session_state:
    st.session_state["google_fit_connected"] = False

DB_PATH = "habits.db"
DEMO_WALK_HABIT = "Walk 10,000 Steps"
LEGACY_WALK_HABIT = "Walk 10,000 steps"
USE_STEP_DEMO_DATA = True
STEP_DEMO_FILE = "step_demo_data.json"
STEP_TARGET = 10000
AUTO_STEP_NOTE = "Automatically completed via external step integration"
CATEGORY_CHOICES = ["fitness", "health", "mindfulness", "learning", "productivity", "sleep", "nutrition", "social", "custom", "hydration", "focus", "home"]
CATEGORY_ICONS = {category: "" for category in CATEGORY_CHOICES}
CATEGORY_MARKS = {
    "fitness": "path d='M5 15 L9 11 L13 14 L18 7' stroke-linecap='round' stroke-linejoin='round'",
    "health": "path d='M12 4 C9 1 4 2.5 4 7 c0 5 8 11 8 11 s8-6 8-11 c0-4.5-5-6-8-3z' stroke-linecap='round' stroke-linejoin='round'",
    "mindfulness": "circle cx='12' cy='12' r='4' /><path d='M12 2 v3 M12 19 v3 M2 12 h3 M19 12 h3' stroke-linecap='round'",
    "learning": "path d='M5 6.5 C7 5.5 9 5 12 5 c3 0 5 0.5 7 1.5 v11 C17 16.5 15 16 12 16 c-3 0-5 0.5-7 1.5z' stroke-linejoin='round'",
    "productivity": "path d='M13 2 L5 13 h5 l-1 9 8-11 h-5z' stroke-linejoin='round'",
    "sleep": "path d='M15.5 4.5 A7.5 7.5 0 1 0 19 18 A6.5 6.5 0 1 1 15.5 4.5z' stroke-linejoin='round'",
    "nutrition": "path d='M8 4 v6 M12 4 v6 M8 10 c0 5-2 7-2 10 M12 10 c0 5 2 7 2 10 M17 4 c0 5-1 8-1 16' stroke-linecap='round'",
    "social": "circle cx='8' cy='9' r='3' /><circle cx='16' cy='8' r='2.5' /><path d='M3.5 19 c1-3 3.5-4.5 6.5-4.5 S15 16 16 19 M13 18 c.7-2 2.2-3.2 4.5-3.2 1.2 0 2.2.3 3 .8' stroke-linecap='round'",
    "hydration": "path d='M12 3 C9 7 6 10 6 13.2 A6 6 0 0 0 18 13.2 C18 10 15 7 12 3z' stroke-linejoin='round'",
    "focus": "circle cx='12' cy='12' r='7' /><circle cx='12' cy='12' r='2.5' /><path d='M12 1 v3 M12 20 v3 M1 12 h3 M20 12 h3' stroke-linecap='round'",
    "home": "path d='M4 10.5 L12 4 l8 6.5 M6.5 9.5 V20 h11 V9.5' stroke-linejoin='round'",
    "custom": "path d='M12 3 v18 M3 12 h18' stroke-linecap='round'",
}
COMPLETION_EFFECTS = {
    "fitness": "Movement logged",
    "hydration": "Hydration refreshed",
    "sleep": "Recovery protected",
    "mindfulness": "Calm extended",
    "productivity": "Focus locked in",
}
MOCK_FRIENDS = [
    {"name": "Maya", "streak": 12, "message": "You're right behind me. Keep the canopy dense."},
    {"name": "Jonas", "streak": 9, "message": "I checked in already. Don't let the group streak slip."},
    {"name": "Lea", "streak": 15, "message": "Your focus habit is carrying the squad this week."},
]
CATEGORY_ICONS = {category: "" for category in CATEGORY_CHOICES}
COMPLETION_EFFECTS = {
    "fitness": "Movement logged",
    "hydration": "Hydration refreshed",
    "sleep": "Recovery protected",
    "mindfulness": "Calm extended",
    "productivity": "Focus locked in",
}
MOCK_FRIENDS = [
    {"name": "Maya", "streak": 12, "message": "You're right behind me. Keep the canopy dense."},
    {"name": "Jonas", "streak": 9, "message": "I checked in already. Don't let the group streak slip."},
    {"name": "Lea", "streak": 15, "message": "Your focus habit is carrying the squad this week."},
]
NGO_PARTNERS = [
    {"name": "GreenRoots Foundation", "focus": "Reforestation pilots"},
    {"name": "Urban Canopy Lab", "focus": "City tree restoration"},
    {"name": "Watershed Collective", "focus": "Forest-water resilience"},
]
PAGE_CSS = """
<style>
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"] {
        display: none;
    }
    #MainMenu,
    footer {
        visibility: hidden;
    }
    :root {
        --bg: #f7f4ea;
        --card: #fffdf6;
        --card-soft: #ffffff;
        --primary: #7fbf4d;
        --moss: #6fa64a;
        --lime: #a9cf79;
        --pine: #123322;
        --accent: #7fbf4d;
        --danger: #d97070;
        --text: #123322;
        --muted: #6f7d6a;
        --border: rgba(111, 166, 74, 0.18);
        --shadow: 0 18px 44px rgba(62, 88, 54, 0.12);
        --phone-nav-height: 64px;
        --phone-nav-bottom-gap: 14px;
        --phone-nav-side-gap: 0.95rem;
        --phone-content-bottom-padding: calc(var(--phone-nav-height) + var(--phone-nav-bottom-gap) + 1rem);
    }
    html, body {
        min-height: 100%;
        overflow-y: auto;
        background: #ffffff;
    }
    .stApp,
    [data-testid="stApp"] {
        background: linear-gradient(180deg, #ffffff 0%, #f5f5f3 100%);
        color: var(--text);
        min-height: 100vh;
        overflow-y: auto;
    }
    [data-testid="stAppViewContainer"] {
        width: 100%;
        background: transparent;
        min-height: 100vh;
        padding: 48px 16px 96px !important;
        display: flex;
        justify-content: center;
        align-items: flex-start;
        overflow: visible !important;
        box-sizing: border-box;
    }
    section.main,
    section[data-testid="stMain"],
    [data-testid="stAppViewContainer"] > .main {
        width: 430px !important;
        max-width: calc(100vw - 32px) !important;
        min-width: min(390px, calc(100vw - 32px)) !important;
        margin-left: auto !important;
        margin-right: auto !important;
        margin-top: 0 !important;
        display: block !important;
        height: 880px !important;
        background: #050505 !important;
        border-radius: 56px !important;
        padding: 14px !important;
        box-shadow: 0 32px 90px rgba(0,0,0,0.28) !important;
        overflow: hidden !important;
        box-sizing: border-box !important;
        flex-shrink: 0 !important;
        position: relative !important;
    }
    section.main::before,
    section[data-testid="stMain"]::before,
    [data-testid="stAppViewContainer"] > .main::before {
        content: "";
        position: absolute;
        top: 12px;
        left: 50%;
        transform: translateX(-50%);
        width: 150px;
        height: 42px;
        background: #000000;
        border-radius: 0 0 22px 22px;
        z-index: 100;
        pointer-events: none;
        box-shadow: 0 8px 18px rgba(0, 0, 0, 0.34);
    }
    section.main .block-container,
    section[data-testid="stMain"] .block-container,
    [data-testid="stAppViewBlockContainer"],
    .main .block-container {
        padding-top: 30px;
        padding-bottom: var(--phone-nav-bottom-gap);
        padding-left: 0.95rem;
        padding-right: 0.95rem;
        width: 100% !important;
        max-width: 100% !important;
        min-width: 0 !important;
        height: 100% !important;
        max-height: 100% !important;
        overflow: hidden !important;
        margin: 0 !important;
        min-height: 100%;
        border-radius: 44px;
        display: flex;
        flex-direction: column;
        background:
            radial-gradient(circle at top right, rgba(169, 207, 121, 0.22), transparent 22%),
            radial-gradient(circle at 14% 10%, rgba(127, 191, 77, 0.16), transparent 18%),
            linear-gradient(180deg, #faf8f0 0%, #f7f4ea 48%, #f4f0e4 100%);
        box-shadow:
            inset 0 0 0 1px rgba(255,255,255,0.38),
            0 18px 40px rgba(62, 88, 54, 0.08);
        border: none;
        position: relative;
    }
    .content-scroll-marker,
    .bottom-nav-marker {
        display: none;
    }
    div[data-testid="element-container"]:has(.content-scroll-marker) {
        display: none !important;
    }
    section.main .block-container > div[data-testid="stVerticalBlock"],
    section[data-testid="stMain"] .block-container > div[data-testid="stVerticalBlock"],
    [data-testid="stAppViewBlockContainer"] > div[data-testid="stVerticalBlock"],
    .main .block-container > div[data-testid="stVerticalBlock"] {
        height: 100% !important;
        min-height: 0 !important;
        display: flex !important;
        flex-direction: column !important;
    }
    section.main .block-container > div[data-testid="stVerticalBlock"] > div,
    section[data-testid="stMain"] .block-container > div[data-testid="stVerticalBlock"] > div,
    [data-testid="stAppViewBlockContainer"] > div[data-testid="stVerticalBlock"] > div,
    .main .block-container > div[data-testid="stVerticalBlock"] > div {
        min-height: 0 !important;
    }
    div[data-testid="stVerticalBlock"] > div:has(.content-scroll-marker),
    div[data-testid="element-container"]:has(.content-scroll-marker) {
        flex: 1 1 auto !important;
        min-height: 0 !important;
        height: 100% !important;
        max-height: 100% !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        -webkit-overflow-scrolling: touch;
        padding-bottom: var(--phone-content-bottom-padding) !important;
        margin: 0 !important;
        position: relative !important;
        z-index: 1 !important;
    }
    div[data-testid="stVerticalBlock"] > div:has(.bottom-nav-marker),
    div[data-testid="element-container"]:has(.bottom-nav-marker) {
        position: absolute !important;
        left: var(--phone-nav-side-gap) !important;
        right: var(--phone-nav-side-gap) !important;
        bottom: var(--phone-nav-bottom-gap) !important;
        top: auto !important;
        transform: none !important;
        z-index: 25 !important;
        width: auto !important;
        max-width: none !important;
        height: auto !important;
        min-height: 0 !important;
        margin: 0 !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        padding: 0 !important;
        padding-bottom: 0 !important;
        pointer-events: auto !important;
    }
    div[data-testid="stVerticalBlock"] > div:has(.bottom-nav-marker) > div[data-testid="stVerticalBlock"],
    div[data-testid="element-container"]:has(.bottom-nav-marker) > div[data-testid="stVerticalBlock"] {
        background: rgba(255, 253, 246, 0.92);
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 0.3rem !important;
        box-shadow: 0 18px 44px rgba(62, 88, 54, 0.18);
        backdrop-filter: blur(12px);
        gap: 0.25rem !important;
        margin: 0 !important;
        pointer-events: auto !important;
        height: 64px !important;
        min-height: 64px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div[data-testid="stVerticalBlock"] > div:has(.bottom-nav-marker) div[data-testid="stHorizontalBlock"],
    div[data-testid="element-container"]:has(.bottom-nav-marker) div[data-testid="stHorizontalBlock"] {
        gap: 0.25rem !important;
        align-items: center !important;
    }
    div[data-testid="stVerticalBlock"] > div:has(.bottom-nav-marker) div[data-testid="column"],
    div[data-testid="element-container"]:has(.bottom-nav-marker) div[data-testid="column"] {
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
    }
    div[data-testid="stVerticalBlock"] > div:has(.bottom-nav-marker) div[data-testid="stButton"],
    div[data-testid="element-container"]:has(.bottom-nav-marker) div[data-testid="stButton"] {
        margin: 0 !important;
        height: 44px !important;
        min-height: 44px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transform: translateY(2px) !important;
    }
    div[data-testid="stVerticalBlock"] > div:has(.bottom-nav-marker) div[data-testid="stButton"] > button,
    div[data-testid="element-container"]:has(.bottom-nav-marker) div[data-testid="stButton"] > button {
        width: 100%;
        min-height: 42px !important;
        height: 42px !important;
        margin: 0 !important;
        padding: 0 1rem !important;
        border-radius: 999px !important;
        font-size: 0.92rem !important;
        font-weight: 600 !important;
        box-shadow: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        line-height: 1 !important;
        vertical-align: middle !important;
        box-sizing: border-box !important;
    }
    div[data-testid="stVerticalBlock"] > div:has(.bottom-nav-marker) div[data-testid="stButton"] > button p,
    div[data-testid="element-container"]:has(.bottom-nav-marker) div[data-testid="stButton"] > button p,
    div[data-testid="stVerticalBlock"] > div:has(.bottom-nav-marker) div[data-testid="stButton"] > button span,
    div[data-testid="element-container"]:has(.bottom-nav-marker) div[data-testid="stButton"] > button span {
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div[data-testid="stVerticalBlock"] > div:has(.bottom-nav-marker) div[data-testid="stButton"] > button[kind="secondary"],
    div[data-testid="element-container"]:has(.bottom-nav-marker) div[data-testid="stButton"] > button[kind="secondary"] {
        background: transparent !important;
        color: var(--muted) !important;
        border: none !important;
    }
    div[data-testid="stVerticalBlock"] > div:has(.bottom-nav-marker) div[data-testid="stButton"] > button[kind="primary"],
    div[data-testid="element-container"]:has(.bottom-nav-marker) div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(180deg, #eef7e4, #e6f1d7) !important;
        color: var(--pine) !important;
        border: none !important;
        box-shadow: inset 0 0 0 1px rgba(111, 166, 74, 0.32), 0 0 12px rgba(111, 166, 74, 0.12) !important;
    }
    section.main .block-container::before,
    section[data-testid="stMain"] .block-container::before,
    [data-testid="stAppViewBlockContainer"]::before,
    .main .block-container::before {
        display: none;
    }
    section.main .block-container::after,
    section[data-testid="stMain"] .block-container::after,
    [data-testid="stAppViewBlockContainer"]::after,
    .main .block-container::after {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 44px;
        box-shadow:
            inset 0 0 0 1px rgba(255,255,255,0.32),
            inset 0 18px 30px rgba(255,255,255,0.2);
        pointer-events: none;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 253, 246, 0.96));
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 0.9rem 1rem;
        box-shadow: var(--shadow);
        box-sizing: border-box;
    }
    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
        color: var(--muted);
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--text);
    }
    .hero-card,
    .section-card,
    .forest-card,
    .celebration-card {
        background:
            radial-gradient(circle at top right, rgba(169, 207, 121, 0.14), transparent 24%),
            linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 253, 246, 0.98));
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 0.9rem 1rem;
        box-shadow: var(--shadow);
        backdrop-filter: blur(10px);
        transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
        box-sizing: border-box;
    }
    .hero-card:hover,
    .section-card:hover,
    .forest-card:hover,
    .celebration-card:hover,
    .profile-card:hover,
    .dashboard-habit-card:hover,
    .overview-tree-card:hover,
    .achievement-card:hover,
    .comparison-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 24px 52px rgba(0, 0, 0, 0.28);
    }
    .celebration-card {
        border-color: rgba(166, 217, 106, 0.28);
        background:
            radial-gradient(circle at top, rgba(169, 207, 121, 0.18), transparent 38%),
            linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 253, 246, 0.98));
        text-align: center;
        margin-bottom: 1rem;
    }
    .app-header {
        display: grid;
        gap: 0.8rem;
        background:
            radial-gradient(circle at top right, rgba(169, 207, 121, 0.16), transparent 30%),
            linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 253, 246, 0.96));
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 0.85rem 0.95rem;
        box-shadow: var(--shadow);
        margin-bottom: 0.85rem;
    }
    .page-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        padding: 0.2rem 0 0.1rem 0;
        margin-bottom: 0.25rem;
    }
    .page-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text);
        letter-spacing: -0.02em;
        margin: 0;
    }
    .page-subtitle {
        font-size: 0.78rem;
        color: var(--muted);
        margin-top: 0.08rem;
    }
    .page-indicator {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 30px;
        padding: 0 0.7rem;
        border-radius: 999px;
        background: rgba(127, 191, 77, 0.12);
        border: 1px solid rgba(111,166,74,0.14);
        color: var(--text);
        font-size: 0.76rem;
        font-weight: 600;
        white-space: nowrap;
    }
    .app-header-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.8rem;
    }
    .app-logo {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .app-icon {
        width: 44px;
        height: 44px;
        border-radius: 16px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 1.35rem;
        background: linear-gradient(180deg, rgba(127, 191, 77, 0.18), rgba(111, 166, 74, 0.06));
        border: 1px solid rgba(111,166,74,0.12);
    }
    .app-title {
        color: var(--text);
        font-size: 1.05rem;
        font-weight: 700;
        line-height: 1.1;
    }
    .app-subtitle {
        color: var(--muted);
        font-size: 0.82rem;
        margin-top: 0.1rem;
    }
    .app-streak {
        text-align: right;
    }
    .app-streak .metric-value {
        font-size: 1.1rem;
    }
    .header-metrics {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.6rem;
    }
    .section-card,
    .forest-card {
        margin-top: 0.75rem;
    }
    .eyebrow {
        font-size: 0.76rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--primary);
        margin-bottom: 0.2rem;
    }
    .hero-title {
        font-size: 2.15rem;
        font-weight: 700;
        line-height: 1.1;
        margin: 0;
        color: var(--text);
    }
    .hero-copy,
    .section-copy,
    .forest-copy {
        color: var(--muted);
        margin: 0.2rem 0 0 0;
    }
    .section-heading,
    .forest-heading {
        font-size: 1.15rem;
        font-weight: 650;
        color: var(--text);
        margin: 0;
    }
    .habit-card {
        background:
            radial-gradient(circle at top right, rgba(169, 207, 121, 0.1), transparent 28%),
            linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 253, 246, 0.96));
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 0.75rem 0.9rem;
        margin-top: 0.45rem;
        box-shadow: var(--shadow);
        box-sizing: border-box;
    }
    .forest-overview-grid {
        margin-bottom: 0.3rem;
    }
    .forest-selector-label {
        color: #5f6f5b;
        font-size: 0.78rem;
        font-weight: 600;
        margin: 0.15rem 0 0.25rem 0;
        letter-spacing: 0.01em;
    }
    .habit-name {
        font-size: 1.03rem;
        font-weight: 600;
        color: var(--text);
        margin: 0;
    }
    .habit-status {
        color: var(--primary);
        font-size: 0.9rem;
        margin-top: 0.2rem;
    }
    .habit-meta {
        color: var(--muted);
        font-size: 0.82rem;
        margin-top: 0.35rem;
    }
    .add-habit-panel {
        background:
            radial-gradient(circle at top right, rgba(169, 207, 121, 0.14), transparent 30%),
            linear-gradient(180deg, rgba(255,255,255,0.98), rgba(244,250,236,0.96));
        border: 1px solid rgba(111,166,74,0.12);
        border-radius: 22px;
        padding: 0.9rem 0.95rem;
        box-shadow: 0 18px 36px rgba(17, 42, 30, 0.08);
        margin-top: 0.15rem;
        margin-bottom: 0.55rem;
    }
    .add-habit-copy {
        color: #6f7d6a;
        font-size: 0.84rem;
        line-height: 1.45;
        margin-top: 0.28rem;
    }
    div[data-testid="stForm"] {
        background:
            linear-gradient(180deg, rgba(255,255,255,0.98), rgba(255,253,246,0.96));
        border: 1px solid rgba(111,166,74,0.1);
        border-radius: 22px;
        padding: 0.95rem 0.95rem 0.65rem 0.95rem;
        box-shadow: 0 16px 32px rgba(17, 42, 30, 0.06);
        margin-top: 0.1rem;
    }
    div[data-testid="stForm"] label {
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        color: #123322 !important;
        letter-spacing: 0.01em;
    }
    div[data-testid="stForm"] [data-testid="stHorizontalBlock"] {
        gap: 0.65rem !important;
    }
    div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] {
        margin-top: 0.25rem;
    }
    div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] > button {
        min-height: 46px;
        box-shadow: 0 14px 30px rgba(111, 166, 74, 0.18);
    }
    div[data-testid="stTextInputRootElement"] > div,
    div[data-testid="stNumberInputContainer"] > div,
    div[data-testid="stSelectbox"] > div[data-baseweb="select"] > div,
    div[data-testid="stColorPicker"] input {
        background: rgba(255, 253, 246, 0.98);
        border-color: var(--border);
        color: var(--text);
    }
    div[data-testid="stTextInputRootElement"] input,
    div[data-testid="stNumberInputContainer"] input,
    div[data-testid="stColorPicker"] input,
    textarea {
        color: var(--text);
    }
    div[data-testid="stSelectbox"] [data-baseweb="select"] *,
    div[data-testid="stSelectbox"] [data-baseweb="select"] input,
    div[data-testid="stSelectbox"] [data-baseweb="select"] span,
    div[data-testid="stSelectbox"] [data-baseweb="select"] div,
    div[data-testid="stMultiSelect"] [data-baseweb="select"] *,
    div[data-testid="stMultiSelect"] [data-baseweb="select"] input,
    div[data-testid="stMultiSelect"] [data-baseweb="select"] span,
    div[data-testid="stMultiSelect"] [data-baseweb="select"] div {
        color: #111111 !important;
        opacity: 1 !important;
        -webkit-text-fill-color: #111111 !important;
    }
    div[data-testid="stSelectbox"] [data-baseweb="select"] svg,
    div[data-testid="stMultiSelect"] [data-baseweb="select"] svg {
        fill: #123322 !important;
        color: #123322 !important;
    }
    div[data-testid="stTextInputRootElement"] input::placeholder,
    div[data-testid="stNumberInputContainer"] input::placeholder,
    div[data-testid="stSelectbox"] [data-baseweb="select"] input::placeholder,
    div[data-testid="stMultiSelect"] [data-baseweb="select"] input::placeholder,
    textarea::placeholder {
        color: #7c8975 !important;
        opacity: 1 !important;
        -webkit-text-fill-color: #7c8975 !important;
    }
    label, .stMarkdown, .stCaption, .stRadio, .stSelectbox, .stNumberInput, .stColorPicker {
        color: var(--text);
    }
    div[data-testid="stButton"] > button,
    div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(180deg, #7fbf4d, #6fa64a);
        color: #fffdf6;
        border: none;
        border-radius: 999px;
        font-weight: 650;
        min-height: 44px;
        box-shadow: 0 12px 28px rgba(111, 166, 74, 0.18);
        padding: 0 18px;
        line-height: 1.15;
        box-sizing: border-box;
    }
    div[data-testid="stButton"] > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        background: linear-gradient(180deg, #8bc95b, #74ae4f);
        color: #fffdf6;
    }
    div[data-testid="stButton"] > button:disabled {
        background: linear-gradient(180deg, rgba(154, 183, 173, 0.4), rgba(110, 130, 127, 0.36));
        color: rgba(248, 246, 238, 0.92);
    }
    div[data-testid="stButton"] > button *,
    div[data-testid="stFormSubmitButton"] > button * {
        color: inherit !important;
        opacity: 1 !important;
    }
    .forest-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin: 0.55rem 0 0.7rem 0;
    }
    .forest-pill {
        padding: 0.3rem 0.65rem;
        border-radius: 999px;
        background: rgba(122, 201, 67, 0.08);
        border: 1px solid var(--border);
        color: var(--text);
        font-size: 0.82rem;
    }
    .forest-grid {
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }
    .forest-row,
    .forest-labels {
        display: flex;
        gap: 6px;
        flex-wrap: nowrap;
        overflow-x: auto;
    }
    .forest-tree,
    .forest-label {
        min-width: 56px;
        width: 56px;
        text-align: center;
        flex: 0 0 auto;
    }
    .forest-tree {
        display: flex;
        align-items: flex-end;
        justify-content: center;
        height: 82px;
        padding-bottom: 0;
    }
    .forest-label {
        color: var(--muted);
        font-size: 0.75rem;
    }
    .forest-grid .forest-label,
    .forest-labels .forest-label {
        color: #e8f2e3 !important;
        font-weight: 600;
        line-height: 1.35;
        text-shadow: 0 1px 1px rgba(0, 0, 0, 0.12);
    }
    div[data-testid="stSlider"] {
        padding: 0.3rem 0 1rem 0;
    }
    .profile-card {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 253, 246, 0.96));
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 0.75rem 0.9rem;
        box-shadow: var(--shadow);
        margin-top: 0.45rem;
        box-sizing: border-box;
    }
    .profile-line {
        color: var(--text);
        margin-top: 0.45rem;
    }
    .user-card {
        background:
            radial-gradient(circle at top right, rgba(169, 207, 121, 0.16), transparent 28%),
            radial-gradient(circle at bottom left, rgba(127, 191, 77, 0.12), transparent 24%),
            linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 253, 246, 0.98));
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 0.8rem 0.95rem;
        box-shadow: var(--shadow);
        margin-top: 0.45rem;
        box-sizing: border-box;
    }
    .user-top {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: center;
    }
    .user-name {
        font-size: 1.45rem;
        font-weight: 700;
        color: var(--text);
        margin: 0;
    }
    .user-meta {
        color: var(--muted);
        margin-top: 0.2rem;
        font-size: 0.92rem;
    }
    .xp-wrap {
        margin-top: 0.75rem;
    }
    .xp-bar {
        height: 12px;
        background: rgba(201, 216, 190, 0.45);
        border-radius: 999px;
        overflow: hidden;
        border: 1px solid rgba(111,166,74,0.14);
    }
    .xp-fill {
        height: 100%;
        background: linear-gradient(90deg, #a9cf79, #6fa64a);
        border-radius: 999px;
    }
    .xp-label {
        display: flex;
        justify-content: space-between;
        color: var(--muted);
        font-size: 0.84rem;
        margin-top: 0.45rem;
    }
    .habit-scroll {
        display: flex;
        gap: 0.9rem;
        overflow-x: auto;
        padding: 0.2rem 0 0.35rem 0;
        margin-top: 0.65rem;
        scroll-snap-type: x proximity;
    }
    .dashboard-habit-card {
        min-width: 220px;
        max-width: 220px;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 253, 246, 0.96));
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 0.85rem;
        box-shadow: var(--shadow);
        flex: 0 0 auto;
        scroll-snap-align: start;
        box-sizing: border-box;
    }
    .habit-card-top {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 0.75rem;
    }
    .habit-icon {
        width: 42px;
        height: 42px;
        border-radius: 14px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
        background: rgba(127, 191, 77, 0.08);
        border: 1px solid rgba(111, 166, 74, 0.08);
    }
    .streak-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.3rem 0.55rem;
        border-radius: 999px;
        background: rgba(127, 191, 77, 0.12);
        color: #41612e;
        font-size: 0.76rem;
        white-space: nowrap;
    }
    .dashboard-habit-name {
        font-size: 1rem;
        font-weight: 650;
        color: var(--text);
        margin: 0.5rem 0 0 0;
    }
    .dashboard-habit-meta {
        color: var(--muted);
        font-size: 0.8rem;
        margin-top: 0.2rem;
    }
    .tree-wrap {
        display: flex;
        justify-content: center;
        align-items: flex-end;
        min-height: 108px;
        margin-top: 0.5rem;
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(127, 191, 77, 0.08), rgba(247, 244, 234, 0.1));
    }
    .health-row {
        display: flex;
        justify-content: space-between;
        color: var(--muted);
        font-size: 0.8rem;
        margin-top: 0.55rem;
    }
    .health-bar {
        height: 10px;
        background: rgba(201, 216, 190, 0.44);
        border-radius: 999px;
        overflow: hidden;
        margin-top: 0.3rem;
    }
    .health-fill {
        height: 100%;
        background: linear-gradient(90deg, #7fbf4d, #6fa64a);
        border-radius: 999px;
    }
    .status-pill {
        display: inline-flex;
        margin-top: 0.5rem;
        padding: 0.32rem 0.68rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .status-done {
        color: #fffdf6;
        background: linear-gradient(180deg, #7fbf4d, #6fa64a);
    }
    .status-pending {
        color: var(--pine);
        background: rgba(217, 112, 112, 0.12);
        border: 1px solid rgba(217, 112, 112, 0.14);
    }
    .add-habit-panel {
        background:
            radial-gradient(circle at top right, rgba(169, 207, 121, 0.14), transparent 30%),
            linear-gradient(180deg, rgba(255,255,255,0.98), rgba(244,250,236,0.96));
        border: 1px solid rgba(111,166,74,0.12);
        border-radius: 22px;
        padding: 0.9rem 0.95rem;
        margin-top: 0.15rem;
        box-shadow: 0 18px 36px rgba(17, 42, 30, 0.08);
    }
    .add-habit-action {
        margin-top: 0.55rem;
        margin-bottom: 0.2rem;
    }
    .achievement-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 0.65rem;
        margin-top: 0.6rem;
    }
    .achievement-card {
        border-radius: 22px;
        padding: 0.85rem;
        border: 1px solid var(--border);
        background: linear-gradient(180deg, #fffdf6 0%, #f7f4ea 100%);
        box-shadow: var(--shadow);
        box-sizing: border-box;
        transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
    }
    .achievement-card.unlocked {
        background: linear-gradient(180deg, #fffdf6 0%, #f4faec 100%);
        border: 1px solid #b8d98b;
        box-shadow: 0 8px 24px rgba(120, 184, 70, 0.12);
    }
    .achievement-card.locked {
        background: #f3f2ec;
        border: 1px solid #e1e5da;
        box-shadow: none;
        filter: saturate(0.82);
    }
    .achievement-icon {
        width: 44px;
        height: 44px;
        border-radius: 999px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 14px;
        font-size: 1.45rem;
    }
    .achievement-card.unlocked .achievement-icon {
        background: #e4f4d4;
        color: #5fae3f;
        border: 1px solid #b8d98b;
        box-shadow: 0 6px 18px rgba(120, 184, 70, 0.22);
    }
    .achievement-card.locked .achievement-icon {
        background: #e4e7df;
        color: #879280;
        border: 1px solid #d1d7ca;
    }
    .achievement-card.unlocked .achievement-icon svg {
        stroke: #5fae3f;
        fill: none;
        opacity: 1;
    }
    .achievement-card.locked .achievement-icon svg {
        stroke: #879280;
        fill: none;
        opacity: 1;
    }
    .achievement-title {
        font-size: 0.98rem;
        font-weight: 650;
        color: var(--text);
    }
    .achievement-card.unlocked .achievement-title {
        color: #123322;
    }
    .achievement-card.locked .achievement-title {
        color: #667065;
    }
    .achievement-state {
        font-size: 0.78rem;
        color: var(--primary);
        margin-top: 0.3rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .achievement-card.unlocked .achievement-state {
        color: #78b846;
    }
    .achievement-card.locked .achievement-state {
        color: #98a093;
    }
    .achievement-copy {
        color: var(--muted);
        font-size: 0.82rem;
        margin-top: 0.45rem;
    }
    .achievement-card.unlocked .achievement-copy {
        color: #5f6f5b;
    }
    .achievement-card.locked .achievement-copy {
        color: #8b9386;
    }
    .forest-overview-grid {
        display: none;
    }
    .overview-tree-card {
        background: linear-gradient(180deg, rgba(16, 37, 27, 0.98), rgba(22, 53, 36, 0.96));
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 0.95rem;
        box-shadow: var(--shadow);
    }
    .overview-tree-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.6rem;
    }
    .overview-tree-title {
        font-size: 1rem;
        font-weight: 650;
        color: var(--text);
    }
    .overview-tree-stage {
        color: var(--accent);
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .overview-tree-body {
        display: flex;
        justify-content: center;
        align-items: flex-end;
        min-height: 132px;
        margin-top: 0.5rem;
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(122, 201, 67, 0.06), rgba(6, 17, 13, 0.05));
    }
    .impact-card {
        background:
            radial-gradient(circle at top right, rgba(166, 217, 106, 0.14), transparent 30%),
            radial-gradient(circle at bottom left, rgba(127, 191, 77, 0.10), transparent 24%),
            linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 252, 244, 0.97));
        border: 1px solid rgba(111, 166, 74, 0.14);
        border-radius: 22px;
        padding: 0.85rem 1rem;
        margin-top: 0.45rem;
        box-shadow: 0 20px 44px rgba(62, 88, 54, 0.10);
        box-sizing: border-box;
    }
    .impact-card .eyebrow {
        color: #6fa64a !important;
    }
    .impact-card .section-heading {
        color: #123322 !important;
    }
    .impact-card .section-copy,
    .impact-card .habit-meta,
    .impact-card .xp-label {
        color: #6f7d6a !important;
    }
    .impact-card .mini-tile {
        background: linear-gradient(180deg, rgba(246, 251, 237, 0.96), rgba(255, 253, 246, 0.98));
        border-color: rgba(111, 166, 74, 0.14);
        box-shadow: inset 0 0 0 1px rgba(255,255,255,0.42);
    }
    .impact-card .metric-label {
        color: #6f7d6a !important;
        font-weight: 600;
    }
    .impact-card .metric-value {
        color: #123322 !important;
        font-weight: 700;
    }
    .impact-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 0.6rem;
        margin-top: 0.5rem;
    }
    .impact-pill {
        background: rgba(122, 201, 67, 0.08);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 0.75rem;
    }
    .floating-panel {
        position: relative;
        overflow: hidden;
    }
    .floating-panel::after {
        content: "";
        position: absolute;
        inset: auto -40px -40px auto;
        width: 140px;
        height: 140px;
        background: radial-gradient(circle, rgba(166, 217, 106, 0.15), transparent 70%);
        pointer-events: none;
    }
    .insight-card {
        background:
            radial-gradient(circle at top right, rgba(166, 217, 106, 0.14), transparent 30%),
            radial-gradient(circle at bottom left, rgba(127, 191, 77, 0.10), transparent 24%),
            linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 252, 244, 0.97));
        border: 1px solid rgba(111, 166, 74, 0.14);
        border-radius: 22px;
        padding: 0.85rem 0.95rem;
        margin-top: 0.45rem;
        box-shadow: 0 20px 44px rgba(62, 88, 54, 0.10);
        box-sizing: border-box;
    }
    .insight-title {
        color: #6fa64a;
        font-size: 0.8rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .insight-copy {
        color: #123322;
        margin-top: 0.4rem;
        font-size: 0.92rem;
    }
    .selector-card {
        background: linear-gradient(180deg, rgba(13, 31, 23, 0.96), rgba(20, 51, 35, 0.94));
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 0.62rem 0.75rem;
        box-shadow: var(--shadow);
    }
    .floating-tree {
        filter: drop-shadow(0 10px 16px rgba(122, 201, 67, 0.1));
    }
    .comparison-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 0.85rem;
        margin-top: 0.65rem;
    }
    .comparison-card {
        background: linear-gradient(180deg, rgba(16, 37, 27, 0.98), rgba(22, 53, 36, 0.96));
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 0.8rem 0.9rem;
        box-shadow: var(--shadow);
        box-sizing: border-box;
    }
    .comparison-name {
        color: var(--text);
        font-weight: 650;
    }
    .comparison-meta {
        color: var(--muted);
        font-size: 0.82rem;
        margin-top: 0.28rem;
    }
    .table-card {
        background: linear-gradient(180deg, rgba(16, 37, 27, 0.98), rgba(22, 53, 36, 0.96));
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 0.8rem 0.9rem;
        margin-top: 0.5rem;
        box-shadow: var(--shadow);
        box-sizing: border-box;
    }
    .table-row {
        display: grid;
        grid-template-columns: 1.4fr 0.8fr 0.8fr 0.9fr;
        gap: 0.7rem;
        padding: 0.45rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        color: var(--text);
        font-size: 0.9rem;
    }
    .table-row.header {
        color: var(--muted);
        text-transform: uppercase;
        font-size: 0.74rem;
        letter-spacing: 0.08em;
    }
    .season-tag {
        color: var(--accent);
        font-size: 0.78rem;
        margin-top: 0.35rem;
    }
    .failure-badge {
        display: inline-flex;
        margin-top: 0.6rem;
        padding: 0.3rem 0.65rem;
        border-radius: 999px;
        background: rgba(255, 107, 107, 0.18);
        color: #ffb5b5;
        border: 1px solid rgba(255, 107, 107, 0.16);
        font-size: 0.78rem;
    }
    .friend-grid,
    .impact-grid,
    .share-grid,
    .connection-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 0.65rem;
        margin-top: 0.6rem;
    }
    .friend-card,
    .share-card,
    .connection-card,
    .ad-card,
    .onboarding-card,
    .partner-card {
        background: linear-gradient(180deg, rgba(16, 37, 27, 0.98), rgba(22, 53, 36, 0.96));
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 0.8rem 0.9rem;
        box-shadow: var(--shadow);
        box-sizing: border-box;
    }
    .friend-top,
    .connection-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.6rem;
    }
    .friend-name,
    .share-title,
    .partner-name {
        color: var(--text);
        font-weight: 650;
    }
    .friend-copy,
    .share-copy,
    .partner-copy {
        color: var(--muted);
        font-size: 0.84rem;
        margin-top: 0.45rem;
    }
    .status-ok {
        color: var(--primary);
    }
    .status-warn {
        color: #ffd89a;
    }
    .status-bad {
        color: #ffb5b5;
    }
    .group-visual {
        display: flex;
        align-items: flex-end;
        justify-content: center;
        gap: 0.35rem;
        min-height: 120px;
        margin-top: 0.65rem;
    }
    .share-preview {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 136px;
        margin-top: 0.6rem;
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(61, 220, 132, 0.04), rgba(7, 20, 15, 0.04));
    }
    .mini-forest {
        display: flex;
        gap: 0.35rem;
        justify-content: center;
        align-items: flex-end;
    }
    .ad-card {
        border-color: rgba(242, 201, 76, 0.16);
        background:
            radial-gradient(circle at top right, rgba(242, 201, 76, 0.12), transparent 28%),
            linear-gradient(180deg, rgba(16, 37, 27, 0.98), rgba(22, 53, 36, 0.96));
    }
    .onboarding-card {
        border-color: rgba(61, 220, 132, 0.18);
        background:
            radial-gradient(circle at top left, rgba(61, 220, 132, 0.12), transparent 30%),
            linear-gradient(180deg, rgba(16, 37, 27, 0.98), rgba(22, 53, 36, 0.96));
        margin-top: 0.8rem;
    }
    .step-list {
        display: grid;
        gap: 0.45rem;
        margin-top: 0.8rem;
    }
    .step-item {
        color: var(--text);
        background: rgba(61, 220, 132, 0.06);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 0.62rem 0.75rem;
    }
    .partner-card {
        border-color: rgba(242, 201, 76, 0.14);
    }
    .metric-tile {
        background: rgba(7, 20, 15, 0.36);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 0.8rem 0.9rem;
    }
    .metric-label {
        color: var(--muted);
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .metric-value {
        color: var(--text);
        font-size: 1.2rem;
        font-weight: 700;
        margin-top: 0.15rem;
    }
    .compact-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 0.65rem;
    }
    .block-container > div,
    .block-container .element-container {
        box-sizing: border-box;
    }
    .stTabs [data-testid="stVerticalBlock"] {
        gap: 0.7rem;
    }
    .stTabs [data-testid="stVerticalBlock"] > div {
        margin-bottom: 0.15rem;
    }
    .today-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 0.7rem;
        align-items: start;
    }
    .card-stack {
        display: grid;
        gap: 0.6rem;
    }
    .compact-card {
        min-height: 100%;
    }
    .overview-tree-card {
        min-height: 252px;
    }
    .today-actions {
        display: grid;
        gap: 0.5rem;
    }
    div[data-testid="stVerticalBlock"] {
        gap: 0.7rem;
    }
    .block-container > div:last-child,
    .block-container .element-container:last-child,
    .section-card:last-child,
    .profile-card:last-child,
    .user-card:last-child,
    .insight-card:last-child,
    .table-card:last-child {
        margin-bottom: 8px !important;
    }
    .block-container > div,
    .block-container .element-container,
    .section-card,
    .habit-card,
    .profile-card,
    .user-card,
    .insight-card,
    .comparison-card,
    .table-card,
    .achievement-card,
    .share-card,
    .friend-card,
    .connection-card,
    .partner-card,
    .impact-card,
    .ad-card,
    .onboarding-card {
        box-sizing: border-box;
    }
    div[data-testid="stForm"] {
        margin-top: 0.45rem;
    }
    div[data-testid="stSlider"] {
        margin: 0.1rem 0 0.6rem 0;
    }
    .action-row {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 0.7rem;
        align-items: center;
    }
    .dark-card,
    .dark-button,
    .green-gradient-button,
    .feature-button,
    .action-button,
    .habit-card-dark,
    .settings-button,
    .menu-button,
    .profile-action {
        color: #f8f6ee !important;
    }
    .dark-card *,
    .dark-button *,
    .green-gradient-button *,
    .feature-button *,
    .action-button *,
    .habit-card-dark *,
    .settings-button *,
    .menu-button *,
    .profile-action * {
        color: inherit !important;
        opacity: 1 !important;
    }
    div[data-testid="stExpander"] {
        background: transparent;
        border: none;
        margin-top: 0.35rem;
    }
    div[data-testid="stExpander"] details {
        background:
            radial-gradient(circle at top right, rgba(166, 217, 106, 0.12), transparent 30%),
            radial-gradient(circle at bottom left, rgba(127, 191, 77, 0.08), transparent 24%),
            linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 252, 244, 0.97));
        border: 1px solid rgba(111, 166, 74, 0.14);
        border-radius: 22px;
        box-shadow: 0 20px 44px rgba(62, 88, 54, 0.10);
        overflow: hidden;
    }
    div[data-testid="stExpander"] summary {
        color: #123322 !important;
        background: rgba(255, 252, 244, 0.96);
        border-radius: 22px;
        padding: 0.2rem 0.2rem;
    }
    div[data-testid="stExpander"] summary:hover {
        background: rgba(246, 251, 237, 0.98);
    }
    div[data-testid="stExpander"] details[open] summary {
        border-bottom: 1px solid rgba(111, 166, 74, 0.12);
        border-radius: 22px 22px 0 0;
    }
    div[data-testid="stExpander"] summary p,
    div[data-testid="stExpander"] label,
    div[data-testid="stExpander"] div {
        color: #123322 !important;
        opacity: 1 !important;
    }
    div[data-testid="stExpander"] svg,
    div[data-testid="stExpander"] summary svg {
        fill: #5f6f5b !important;
        stroke: #5f6f5b !important;
    }
    div[data-testid="stExpander"] .section-copy,
    div[data-testid="stExpander"] .friend-copy,
    div[data-testid="stExpander"] .achievement-copy,
    div[data-testid="stExpander"] .dashboard-habit-meta,
    div[data-testid="stExpander"] .habit-meta,
    div[data-testid="stExpander"] .season-tag,
    div[data-testid="stExpander"] .user-meta,
    div[data-testid="stExpander"] .xp-label,
    div[data-testid="stExpander"] .forest-label,
    div[data-testid="stExpander"] .comparison-meta,
    div[data-testid="stExpander"] .secondary-text {
        color: #dce6d5 !important;
        opacity: 1 !important;
    }
    div[data-testid="stExpander"] .section-heading,
    div[data-testid="stExpander"] .friend-name,
    div[data-testid="stExpander"] .share-title,
    div[data-testid="stExpander"] .partner-name,
    div[data-testid="stExpander"] .comparison-name,
    div[data-testid="stExpander"] .achievement-title,
    div[data-testid="stExpander"] .metric-value,
    div[data-testid="stExpander"] .metric-label,
    div[data-testid="stExpander"] .achievement-state,
    div[data-testid="stExpander"] .eyebrow,
    div[data-testid="stExpander"] .status-ok,
    div[data-testid="stExpander"] .status-warn,
    div[data-testid="stExpander"] .status-bad {
        color: #f8f6ee !important;
        opacity: 1 !important;
    }
    div[data-testid="stExpander"] .profile-card,
    div[data-testid="stExpander"] .table-card,
    div[data-testid="stExpander"] .comparison-card,
    div[data-testid="stExpander"] .insight-card,
    div[data-testid="stExpander"] .achievement-card,
    div[data-testid="stExpander"] .friend-card,
    div[data-testid="stExpander"] .share-card,
    div[data-testid="stExpander"] .connection-card,
    div[data-testid="stExpander"] .partner-card,
    div[data-testid="stExpander"] .impact-pill {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 253, 246, 0.96)) !important;
        color: #123322 !important;
        border-color: rgba(111, 166, 74, 0.14) !important;
    }
    div[data-testid="stExpander"] .profile-card *,
    div[data-testid="stExpander"] .table-card *,
    div[data-testid="stExpander"] .comparison-card *,
    div[data-testid="stExpander"] .insight-card *,
    div[data-testid="stExpander"] .achievement-card *,
    div[data-testid="stExpander"] .friend-card *,
    div[data-testid="stExpander"] .share-card *,
    div[data-testid="stExpander"] .connection-card *,
    div[data-testid="stExpander"] .partner-card *,
    div[data-testid="stExpander"] .impact-pill * {
        color: inherit !important;
        opacity: 1 !important;
    }
    div[data-testid="stExpander"] .profile-card .eyebrow,
    div[data-testid="stExpander"] .table-card .eyebrow,
    div[data-testid="stExpander"] .insight-card .insight-title,
    div[data-testid="stExpander"] .impact-pill .achievement-title,
    div[data-testid="stExpander"] .achievement-card .eyebrow,
    div[data-testid="stExpander"] .share-card .eyebrow,
    div[data-testid="stExpander"] .connection-card .eyebrow,
    div[data-testid="stExpander"] .friend-card .eyebrow,
    div[data-testid="stExpander"] .partner-card .eyebrow,
    div[data-testid="stExpander"] .ad-card .eyebrow,
    div[data-testid="stExpander"] .onboarding-card .eyebrow,
    div[data-testid="stExpander"] .section-card .eyebrow,
    div[data-testid="stExpander"] .profile-card .section-label,
    div[data-testid="stExpander"] .table-card .section-label,
    div[data-testid="stExpander"] .comparison-card .section-label,
    div[data-testid="stExpander"] .insight-card .section-label,
    div[data-testid="stExpander"] .achievement-card .section-label,
    div[data-testid="stExpander"] .friend-card .section-label,
    div[data-testid="stExpander"] .share-card .section-label,
    div[data-testid="stExpander"] .connection-card .section-label,
    div[data-testid="stExpander"] .partner-card .section-label,
    div[data-testid="stExpander"] .ad-card .section-label,
    div[data-testid="stExpander"] .onboarding-card .section-label {
        color: #6fa64a !important;
        opacity: 1 !important;
    }
    div[data-testid="stExpander"] .table-row,
    div[data-testid="stExpander"] .table-row div,
    div[data-testid="stExpander"] .profile-line,
    div[data-testid="stExpander"] .comparison-meta,
    div[data-testid="stExpander"] .achievement-copy,
    div[data-testid="stExpander"] .friend-copy,
    div[data-testid="stExpander"] .share-copy,
    div[data-testid="stExpander"] .partner-copy,
    div[data-testid="stExpander"] .section-copy,
    div[data-testid="stExpander"] .dashboard-habit-meta,
    div[data-testid="stExpander"] .habit-meta,
    div[data-testid="stExpander"] .season-tag,
    div[data-testid="stExpander"] .user-meta,
    div[data-testid="stExpander"] .xp-label,
    div[data-testid="stExpander"] .forest-label {
        color: #123322 !important;
        opacity: 1 !important;
    }
    div[data-testid="stExpander"] .profile-card .section-heading,
    div[data-testid="stExpander"] .table-card .section-heading,
    div[data-testid="stExpander"] .comparison-card .section-heading,
    div[data-testid="stExpander"] .insight-card .section-heading,
    div[data-testid="stExpander"] .achievement-card .section-heading,
    div[data-testid="stExpander"] .friend-card .section-heading,
    div[data-testid="stExpander"] .share-card .section-heading,
    div[data-testid="stExpander"] .connection-card .section-heading,
    div[data-testid="stExpander"] .partner-card .section-heading,
    div[data-testid="stExpander"] .ad-card .section-heading,
    div[data-testid="stExpander"] .onboarding-card .section-heading,
    div[data-testid="stExpander"] .section-card .section-heading,
    div[data-testid="stExpander"] .profile-card .title,
    div[data-testid="stExpander"] .table-card .title,
    div[data-testid="stExpander"] .comparison-card .title,
    div[data-testid="stExpander"] .insight-card .title,
    div[data-testid="stExpander"] .achievement-card .title,
    div[data-testid="stExpander"] .friend-card .title,
    div[data-testid="stExpander"] .share-card .title,
    div[data-testid="stExpander"] .connection-card .title,
    div[data-testid="stExpander"] .partner-card .title,
    div[data-testid="stExpander"] .ad-card .title,
    div[data-testid="stExpander"] .onboarding-card .title,
    div[data-testid="stExpander"] .section-card .title,
    div[data-testid="stExpander"] .profile-card h1,
    div[data-testid="stExpander"] .profile-card h2,
    div[data-testid="stExpander"] .profile-card h3,
    div[data-testid="stExpander"] .table-card h1,
    div[data-testid="stExpander"] .table-card h2,
    div[data-testid="stExpander"] .table-card h3,
    div[data-testid="stExpander"] .comparison-card h1,
    div[data-testid="stExpander"] .comparison-card h2,
    div[data-testid="stExpander"] .comparison-card h3,
    div[data-testid="stExpander"] .insight-card h1,
    div[data-testid="stExpander"] .insight-card h2,
    div[data-testid="stExpander"] .insight-card h3,
    div[data-testid="stExpander"] .achievement-card h1,
    div[data-testid="stExpander"] .achievement-card h2,
    div[data-testid="stExpander"] .achievement-card h3,
    div[data-testid="stExpander"] .friend-card h1,
    div[data-testid="stExpander"] .friend-card h2,
    div[data-testid="stExpander"] .friend-card h3,
    div[data-testid="stExpander"] .share-card h1,
    div[data-testid="stExpander"] .share-card h2,
    div[data-testid="stExpander"] .share-card h3,
    div[data-testid="stExpander"] .connection-card h1,
    div[data-testid="stExpander"] .connection-card h2,
    div[data-testid="stExpander"] .connection-card h3,
    div[data-testid="stExpander"] .partner-card h1,
    div[data-testid="stExpander"] .partner-card h2,
    div[data-testid="stExpander"] .partner-card h3,
    div[data-testid="stExpander"] .ad-card h1,
    div[data-testid="stExpander"] .ad-card h2,
    div[data-testid="stExpander"] .ad-card h3,
    div[data-testid="stExpander"] .onboarding-card h1,
    div[data-testid="stExpander"] .onboarding-card h2,
    div[data-testid="stExpander"] .onboarding-card h3,
    div[data-testid="stExpander"] .section-card h1,
    div[data-testid="stExpander"] .section-card h2,
    div[data-testid="stExpander"] .section-card h3 {
        color: #123322 !important;
        opacity: 1 !important;
    }
    .light-card,
    .inner-card,
    .accordion-content-card,
    .demo-card,
    .info-card {
        background: #fffdf6 !important;
        color: #123322 !important;
    }
    .light-card *,
    .inner-card *,
    .accordion-content-card *,
    .demo-card *,
    .info-card * {
        color: inherit !important;
        opacity: 1 !important;
    }
    .light-card .eyebrow,
    .light-card .section-label,
    .light-card .overline,
    .inner-card .eyebrow,
    .inner-card .section-label,
    .inner-card .overline,
    .accordion-content-card .eyebrow,
    .accordion-content-card .section-label,
    .accordion-content-card .overline,
    .demo-card .eyebrow,
    .demo-card .section-label,
    .demo-card .overline,
    .info-card .eyebrow,
    .info-card .section-label,
    .info-card .overline {
        color: #6fa64a !important;
        opacity: 1 !important;
    }
    .dark-section,
    .accordion,
    .expandable-section,
    .green-panel {
        color: #f8f6ee !important;
    }
    .dark-section *,
    .accordion *,
    .expandable-section *,
    .green-panel * {
        opacity: 1 !important;
    }
    .compact-progress {
        display: grid;
        gap: 0.7rem;
    }
    .today-ring {
        width: 104px;
        height: 104px;
        margin: 0 auto;
        border-radius: 50%;
        background: conic-gradient(var(--primary) var(--progress), rgba(255,255,255,0.07) 0);
        display: grid;
        place-items: center;
    }
    .today-ring-inner {
        width: 78px;
        height: 78px;
        border-radius: 50%;
        background: var(--card);
        display: grid;
        place-items: center;
        text-align: center;
        color: var(--text);
        font-weight: 700;
    }
    .mini-metrics {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.55rem;
    }
    .selector-layout {
        display: grid;
        grid-template-columns: 0.82fr 1.18fr;
        gap: 0.8rem;
        align-items: start;
        margin-top: 0.55rem;
    }
    .insights-stack {
        display: grid;
        gap: 0.85rem;
    }
    .mini-tile {
        background:
            linear-gradient(180deg, rgba(248, 251, 241, 0.98), rgba(255, 253, 246, 0.98));
        border: 1px solid rgba(111, 166, 74, 0.14);
        border-radius: 18px;
        padding: 0.72rem 0.68rem;
        text-align: center;
        box-shadow:
            inset 0 0 0 1px rgba(255,255,255,0.45),
            0 10px 24px rgba(62, 88, 54, 0.08);
    }
    .mini-tile .metric-label {
        font-size: 0.68rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #6f7d6a;
        font-weight: 600;
    }
    .mini-tile .metric-value {
        font-size: 1rem;
        color: #123322;
        font-weight: 700;
    }
    div[data-testid="stRadio"] label p {
        color: #123322 !important;
        opacity: 1 !important;
    }
    div[data-testid="stRadio"] {
        margin: 0 !important;
        width: 100% !important;
        max-width: 100% !important;
        overflow: visible !important;
    }
    div[data-testid="stRadio"] > div {
        margin: 0 !important;
        width: 100% !important;
        max-width: 100% !important;
        overflow: visible !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 0.5rem;
        display: flex;
        flex-direction: row;
        flex-wrap: nowrap;
        overflow-x: auto;
        overflow-y: hidden !important;
        white-space: nowrap;
        scrollbar-width: none;
        min-height: 52px;
        height: 52px;
        width: 100%;
        max-width: 100%;
        padding: 5px 18px 5px 8px;
        padding-right: 24px !important;
        background: rgba(22, 56, 37, 0.94);
        border: 1px solid var(--border);
        border-radius: 999px;
        box-shadow: 0 14px 32px rgba(0, 0, 0, 0.18);
        backdrop-filter: blur(12px);
        align-items: center;
        justify-content: flex-start;
        box-sizing: border-box;
        margin: 0 !important;
        scroll-padding-left: 8px;
        scroll-padding-right: 18px;
        -webkit-overflow-scrolling: touch;
    }
    div[data-testid="stRadio"] div[role="radiogroup"]::-webkit-scrollbar {
        display: none;
        height: 0;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label {
        background: rgba(22, 56, 37, 0.96);
        border: 1px solid var(--border);
        border-radius: 999px;
        height: 40px;
        min-height: 40px;
        padding: 0 16px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        align-self: center;
        flex: 0 0 auto;
        min-width: max-content !important;
        max-width: none !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: unset !important;
        transition: background 180ms ease, box-shadow 180ms ease, border-color 180ms ease, transform 180ms ease;
        color: #f8f6ee !important;
        opacity: 1 !important;
        box-sizing: border-box;
        margin: 0 !important;
        line-height: 1 !important;
        scroll-snap-align: start;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:hover {
        transform: translateY(-1px);
        border-color: rgba(122, 201, 67, 0.28);
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
        background: linear-gradient(180deg, #eaf4dd, #dcecc7);
        border-color: rgba(122, 201, 67, 0.3);
        box-shadow: inset 0 0 0 1px rgba(122, 201, 67, 0.38), 0 0 12px rgba(122, 201, 67, 0.12);
        color: #123322 !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label p {
        white-space: nowrap;
        overflow: visible;
        text-overflow: unset;
        max-width: none;
        min-width: max-content;
        width: max-content;
        margin: 0;
        color: inherit !important;
        opacity: 1 !important;
        text-align: center;
        line-height: 1.2;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label *,
    div[data-testid="stRadio"] div[role="radiogroup"] label span,
    div[data-testid="stRadio"] div[role="radiogroup"] label div {
        color: inherit !important;
        opacity: 1 !important;
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label input {
        accent-color: #78b846;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"] {
        height: 40px !important;
        min-height: 40px !important;
        padding: 0 16px !important;
        margin: 0 !important;
        align-self: center !important;
        min-width: max-content !important;
        max-width: none !important;
        overflow: visible !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] label[data-baseweb="radio"] > div {
        margin: 0 !important;
        align-self: center !important;
        min-width: max-content !important;
        overflow: visible !important;
    }
    .habit-chip,
    .selected-habit-chip,
    .filter-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 44px;
        padding: 0 12px;
        box-sizing: border-box;
        color: #f8f6ee !important;
    }
    .habit-chip-inner,
    .selected-habit-chip-inner {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        height: 38px;
        padding: 0 18px;
        margin: 0;
        border-radius: 999px;
        box-sizing: border-box;
    }
    ::-webkit-scrollbar {
        height: 8px;
        width: 8px;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(61, 220, 132, 0.24);
        border-radius: 999px;
    }
    .dark-card,
    .dark-button,
    .green-gradient-button,
    .feature-button,
    .action-button,
    .habit-card-dark,
    .settings-button,
    .menu-button,
    .profile-action,
    .more-section,
    .green-panel,
    .timeline-dark,
    div[data-testid="stExpander"] details,
    div[data-testid="stRadio"] div[role="radiogroup"] {
        color: #f8f6ee !important;
    }
    .dark-card *,
    .dark-button *,
    .green-gradient-button *,
    .feature-button *,
    .action-button *,
    .habit-card-dark *,
    .settings-button *,
    .menu-button *,
    .profile-action *,
    .more-section *,
    .green-panel *,
    .timeline-dark * {
        color: inherit !important;
        opacity: 1 !important;
    }
    .dark-card .secondary-text,
    .dark-button .secondary-text,
    .green-gradient-button .secondary-text,
    .more-section .secondary-text,
    .timeline-dark .secondary-text {
        color: #d7e2cf !important;
    }
    .dark-section .muted,
    .green-panel .muted,
    .more-section .muted,
    .timeline-dark .muted,
    .dark-section .date,
    .green-panel .date,
    .more-section .date,
    .timeline-dark .date,
    .dark-section .timeline-label,
    .green-panel .timeline-label,
    .more-section .timeline-label,
    .timeline-dark .timeline-label {
        color: #c8d6bf !important;
        opacity: 1 !important;
    }
    .light-card,
    .inner-card,
    .accordion-content-card,
    .demo-card,
    .info-card {
        background: #fffdf6 !important;
        color: #123322 !important;
    }
    .light-card *,
    .inner-card *,
    .accordion-content-card *,
    .demo-card *,
    .info-card * {
        color: inherit !important;
        opacity: 1 !important;
    }
    .light-card .eyebrow,
    .light-card .section-label,
    .light-card .overline,
    .inner-card .eyebrow,
    .inner-card .section-label,
    .inner-card .overline,
    .accordion-content-card .eyebrow,
    .accordion-content-card .section-label,
    .accordion-content-card .overline {
        color: #6fa64a !important;
    }
    @media (max-width: 640px) {
        [data-testid="stAppViewContainer"] {
            padding: 0;
            display: block;
        }
        section.main,
        section[data-testid="stMain"],
        [data-testid="stAppViewContainer"] > .main {
            width: 100%;
            max-width: 100%;
            min-width: 0;
            height: 100dvh;
            min-height: 100dvh;
            border-radius: 0;
            padding: 0;
            box-shadow: none;
            background: transparent;
        }
        section.main .block-container,
        section[data-testid="stMain"] .block-container,
        [data-testid="stAppViewBlockContainer"],
        .main .block-container {
            padding-top: 0.9rem;
            padding-left: 0.8rem;
            padding-right: 0.8rem;
            margin-top: 0;
            margin-bottom: 0;
            height: auto !important;
            max-height: none !important;
            overflow: visible !important;
            border-radius: 0;
            box-shadow: none;
            border: none;
        }
        div[data-testid="stVerticalBlock"] > div:has(.content-scroll-marker),
        div[data-testid="element-container"]:has(.content-scroll-marker) {
            padding-bottom: calc(var(--phone-nav-height) + 1rem + env(safe-area-inset-bottom, 0px)) !important;
        }
        div[data-testid="stVerticalBlock"] > div:has(.bottom-nav-marker),
        div[data-testid="element-container"]:has(.bottom-nav-marker) {
            left: 0.8rem !important;
            right: 0.8rem !important;
            bottom: max(0.8rem, env(safe-area-inset-bottom, 0px)) !important;
        }
        div[data-testid="stTabs"] {
            height: auto;
            overflow: visible;
        }
        div[data-baseweb="tab-panel-list"],
        div[data-testid="stTabs"] [data-baseweb="tab-panel-list"] {
            height: auto;
            max-height: none;
            overflow: visible;
        }
        div[data-baseweb="tab-panel"],
        div[data-testid="stTabs"] [data-baseweb="tab-panel"],
        div[data-testid="stTabs"] [role="tabpanel"] {
            height: auto;
            max-height: none;
            overflow: visible;
            padding-bottom: 0;
        }
        section.main .block-container::before,
        section.main .block-container::after,
        section[data-testid="stMain"] .block-container::before,
        section[data-testid="stMain"] .block-container::after,
        [data-testid="stAppViewBlockContainer"]::before,
        [data-testid="stAppViewBlockContainer"]::after,
        .main .block-container::before,
        .main .block-container::after {
            display: none;
        }
        section.main div[data-baseweb="tab-list"],
        section[data-testid="stMain"] div[data-baseweb="tab-list"],
        [data-testid="stAppViewContainer"] > .main div[data-baseweb="tab-list"] {
            position: fixed;
            left: 10px;
            right: 10px;
            bottom: 6px;
            width: auto;
        }
        .hero-title {
            font-size: 1.7rem;
        }
        .section-heading,
        .forest-heading {
            font-size: 1.02rem;
        }
        .user-top {
            flex-direction: column;
            align-items: flex-start;
        }
        .xp-label {
            gap: 0.6rem;
            flex-direction: column;
            align-items: flex-start;
        }
        .habit-scroll {
            gap: 0.75rem;
            margin-left: -0.05rem;
        }
        .dashboard-habit-card {
            min-width: 188px;
            max-width: 188px;
            padding: 0.9rem;
        }
        .forest-tree,
        .forest-label {
            min-width: 46px;
            width: 46px;
        }
        .forest-tree {
            height: 88px;
        }
        .achievement-grid {
            grid-template-columns: 1fr;
        }
        .selector-layout {
            grid-template-columns: 1fr;
        }
        .today-grid {
            grid-template-columns: 1fr;
        }
        .forest-overview-grid,
        .comparison-grid,
        .impact-grid,
        .friend-grid,
        .share-grid,
        .connection-grid {
            grid-template-columns: 1fr;
        }
        .table-row {
            grid-template-columns: 1.3fr 0.9fr 0.8fr 0.9fr;
            font-size: 0.82rem;
        }
        .action-row {
            grid-template-columns: 1fr;
        }
    }
</style>
"""


def html_string(value):
    return dedent(value).strip()


def render_html(value):
    st.markdown(html_string(value), unsafe_allow_html=True)


def category_icon_svg(category, accent="#7ac943", size=18):
    mark = CATEGORY_MARKS.get(category or "custom", CATEGORY_MARKS["custom"])
    return (
        f"<svg viewBox='0 0 24 24' width='{size}' height='{size}' fill='none' "
        f"stroke='{accent}' stroke-width='1.7' aria-hidden='true'><{mark}</svg>"
    )


def initials(value, fallback="HF"):
    tokens = [token for token in (value or "").split() if token]
    if not tokens:
        return fallback
    if len(tokens) == 1:
        return tokens[0][:2].upper()
    return (tokens[0][0] + tokens[-1][0]).upper()


def avatar_svg(label, size=42, accent="#7ac943"):
    letters = escape(initials(label, "HF"))
    return (
        f"<svg viewBox='0 0 44 44' width='{size}' height='{size}' aria-hidden='true'>"
        "<defs><linearGradient id='avatarGrad' x1='0' y1='0' x2='1' y2='1'>"
        f"<stop offset='0%' stop-color='{accent}' stop-opacity='0.92'/>"
        "<stop offset='100%' stop-color='#1f3527'/></linearGradient></defs>"
        "<rect x='1.5' y='1.5' width='41' height='41' rx='14' fill='url(#avatarGrad)'/>"
        f"<text x='22' y='26' text-anchor='middle' font-size='12' font-weight='700' fill='#eef8f1' font-family='Inter, system-ui, sans-serif'>{letters}</text>"
        "</svg>"
    )


def badge_icon_svg(name, accent="#a6d96a", size=20):
    marks = {
        "First Sprout": "<path d='M12 20 V9' stroke-linecap='round'/><path d='M12 10 C9 8 8 5.5 10 3.5 C12 4.8 14 7.2 12 10 Z'/><path d='M12 12 C15 10 17 7.5 15 5.2 C13 6.4 11 9.1 12 12 Z'/>",
        "Week Warrior": "<path d='M7 20 h10' stroke-linecap='round'/><path d='M8 7 h8 l-1.5 5 H17 L9 21 l1.5-6 H7 Z' stroke-linejoin='round'/>",
        "Forest Keeper": "<path d='M12 20 V14' stroke-linecap='round'/><path d='M12 4 L5 13 h14 Z' stroke-linejoin='round'/><path d='M12 8 L7.5 14 h9 Z' stroke-linejoin='round'/>",
        "Hydration Hero": "<path d='M12 3 C9 7 7 9.5 7 13 a5 5 0 0 0 10 0 c0-3.5-2-6-5-10Z' stroke-linejoin='round'/>",
        "Step Master": "<path d='M8 16 c2-5 4-8 7-8 2 0 4 1.8 4 4.4 0 4.2-3.8 7.6-8.2 7.6-1.4 0-2.4-.3-3.8-1.1 Z' stroke-linejoin='round'/>",
        "World Changer": "<circle cx='12' cy='12' r='8'/><path d='M4.8 10 h14.4 M6.5 15.5 c2-1.3 3.7-1.9 5.5-1.9 2.2 0 4.3.9 5.5 1.9 M9 4.8 c1.4 1.8 2 4.3 2 7.2 0 3-.7 5.6-2 7.3 M15 4.8 c-1.4 1.8-2 4.3-2 7.2 0 3 .7 5.6 2 7.3' stroke-linecap='round'/>",
        "Winter Warrior": "<path d='M12 3 v18 M4.8 7.2 l14.4 9.6 M19.2 7.2 L4.8 16.8' stroke-linecap='round'/>",
        "Legendary": "<path d='M12 4 l2.6 5.3 5.9.9-4.2 4.1 1 5.7-5.3-2.8-5.3 2.8 1-5.7-4.2-4.1 5.9-.9Z' stroke-linejoin='round'/>",
    }
    mark = marks.get(name, marks["First Sprout"])
    return (
        f"<svg viewBox='0 0 24 24' width='{size}' height='{size}' fill='none' "
        f"stroke='{accent}' stroke-width='1.7' aria-hidden='true'>{mark}</svg>"
    )


def habit_visual_icon(category, color, size=18):
    return category_icon_svg(category or "custom", accent=color or "#7ac943", size=size)


def app_logo_svg(size=28):
    return (
        f"<svg viewBox='0 0 32 32' width='{size}' height='{size}' fill='none' aria-hidden='true'>"
        "<defs><linearGradient id='leafGrad' x1='0' y1='0' x2='1' y2='1'>"
        "<stop offset='0%' stop-color='#a6d96a'/><stop offset='100%' stop-color='#4caf50'/></linearGradient></defs>"
        "<path d='M16 4 C10 8 8 14 8 19 a8 8 0 0 0 16 0 C24 14 22 8 16 4z' fill='url(#leafGrad)' fill-opacity='0.92'/>"
        "<path d='M16 9 v14 M16 15 c-2-1.5-4-2.8-6-3.6 M16 17 c2-1.2 4.2-2.3 6-3.4' stroke='#eef8f1' stroke-width='1.8' stroke-linecap='round'/>"
        "</svg>"
    )


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS habits (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS checkins (id INTEGER PRIMARY KEY, habit_id INTEGER, date TEXT, UNIQUE(habit_id, date))"
    )
    habit_migrations = [
        "ALTER TABLE habits ADD COLUMN category TEXT DEFAULT 'custom'",
        "ALTER TABLE habits ADD COLUMN icon TEXT DEFAULT ''",
        "ALTER TABLE habits ADD COLUMN color TEXT DEFAULT '#52d68a'",
        "ALTER TABLE habits ADD COLUMN target_value INTEGER",
        "ALTER TABLE habits ADD COLUMN unit TEXT",
        "ALTER TABLE habits ADD COLUMN verification_mode TEXT DEFAULT 'manual'",
        "ALTER TABLE habits ADD COLUMN health INTEGER DEFAULT 100",
        "ALTER TABLE habits ADD COLUMN streak INTEGER DEFAULT 0",
        "ALTER TABLE habits ADD COLUMN total_completions INTEGER DEFAULT 0",
        "ALTER TABLE habits ADD COLUMN created_at TEXT",
    ]
    checkin_migrations = [
        "ALTER TABLE checkins ADD COLUMN value INTEGER",
        "ALTER TABLE checkins ADD COLUMN note TEXT",
    ]

    for statement in habit_migrations + checkin_migrations:
        try:
            conn.execute(statement)
        except sqlite3.OperationalError:
            pass

    conn.commit()
    return conn


def load_demo_data(conn):
    created_at = date.today().isoformat()
    walk_id = ensure_demo_walk_habit(conn)
    meditate_row = conn.execute(
        "SELECT id FROM habits WHERE lower(name)=lower(?) LIMIT 1",
        ("Meditate 10 min",),
    ).fetchone()
    if meditate_row:
        meditate_id = meditate_row[0]
    else:
        meditate_cursor = conn.execute(
            """
            INSERT INTO habits (
                name, category, icon, color, target_value, unit, verification_mode,
                health, streak, total_completions, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Meditate 10 min",
                "mindfulness",
                "",
                "#52d68a",
                10,
                "minutes",
                "manual",
                100,
                0,
                0,
                created_at,
            ),
        )
        meditate_id = meditate_cursor.lastrowid
    walk_total = 0
    meditate_total = 0

    for days_ago in range(6, -1, -1):
        checkin_day = (date.today() - timedelta(days=days_ago)).isoformat()
        walk_value = 10000 if days_ago in {0, 1, 3, 4, 6} else 8500
        if walk_value >= 10000:
            conn.execute(
                "INSERT OR IGNORE INTO checkins (habit_id, date, value, note) VALUES (?, ?, ?, ?)",
                (walk_id, checkin_day, walk_value, "Seeded demo walk"),
            )
            walk_total += 1

        if days_ago in {0, 2, 3, 5, 6}:
            conn.execute(
                "INSERT OR IGNORE INTO checkins (habit_id, date, value, note) VALUES (?, ?, ?, ?)",
                (meditate_id, checkin_day, 10, "Seeded demo meditation"),
            )
            meditate_total += 1

    conn.execute(
        "UPDATE habits SET total_completions=? WHERE id=?",
        (walk_total, walk_id),
    )
    conn.execute(
        "UPDATE habits SET total_completions=? WHERE id=?",
        (meditate_total, meditate_id),
    )
    conn.commit()


def reset_fresh_start(conn):
    conn.execute("DELETE FROM checkins")
    conn.execute("DELETE FROM habits")
    for table_name, in conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND (
            lower(name) GLOB '*profile*'
            OR lower(name) GLOB '*user*'
            OR lower(name) GLOB '*session*'
            OR lower(name) GLOB '*demo*'
          )
        """
    ).fetchall():
        if table_name in {"habits", "checkins", "sqlite_sequence"}:
            continue
        try:
            conn.execute(f'DELETE FROM "{table_name}"')
        except sqlite3.OperationalError:
            pass
    try:
        conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('habits', 'checkins')")
    except sqlite3.OperationalError:
        pass
    conn.commit()


def clear_app_session_state():
    exact_keys = {
        "xp",
        "last_xp_gain",
        "last_completed_habit",
        "failure_checked_for",
        "milestone_shown_for",
        "onboarding_dismissed",
        "profile_username",
        "profile_avatar",
        "profile-username-input",
        "profile-avatar-input",
        "google_fit_connected",
        "apple_health_connected",
        "google_fit_tokens",
        "google_fit_error",
        "google_fit_oauth_state",
        "google_fit_last_code",
        "confirm-reset-demo",
        "forest-detail-select",
        "today-focus",
        "today-search",
    }
    prefix_keys = (
        "walk_steps_",
        "profile_",
        "demo_",
        "achievement_",
    )
    for key in list(st.session_state.keys()):
        if key in exact_keys or key.startswith(prefix_keys):
            st.session_state.pop(key, None)
    st.session_state["xp"] = 0


def find_demo_walk_habit(conn):
    row = conn.execute(
        "SELECT id, name FROM habits WHERE name IN (?, ?) ORDER BY CASE WHEN name=? THEN 0 ELSE 1 END LIMIT 1",
        (DEMO_WALK_HABIT, LEGACY_WALK_HABIT, DEMO_WALK_HABIT),
    ).fetchone()
    if row and row[1] != DEMO_WALK_HABIT:
        conn.execute("UPDATE habits SET name=? WHERE id=?", (DEMO_WALK_HABIT, row[0]))
        conn.commit()
    return row[0] if row else None


def get_display_habits(conn):
    rows = conn.execute(
        "SELECT id, name FROM habits ORDER BY lower(name), id"
    ).fetchall()
    deduped = []
    seen = set()
    for hid, name in rows:
        display_name = DEMO_WALK_HABIT if name in {DEMO_WALK_HABIT, LEGACY_WALK_HABIT} else name
        key = display_name.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append((hid, display_name))
    return deduped


def ensure_demo_walk_habit(conn):
    existing_id = find_demo_walk_habit(conn)
    if existing_id:
        conn.execute(
            """
            UPDATE habits
            SET category=?,
                color=?,
                target_value=?,
                unit=?,
                verification_mode=?
            WHERE id=?
            """,
            ("fitness", "#52d68a", STEP_TARGET, "steps", "auto", existing_id),
        )
        conn.commit()
        return existing_id

    cursor = conn.execute(
        """
        INSERT INTO habits (
            name, category, icon, color, target_value, unit, verification_mode,
            health, streak, total_completions, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            DEMO_WALK_HABIT,
            "fitness",
            "",
            "#52d68a",
            STEP_TARGET,
            "steps",
            "auto",
            100,
            0,
            0,
            date.today().isoformat(),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def checkins_for_day(conn, day):
    return conn.execute(
        "SELECT COUNT(*) FROM checkins WHERE date=?", (day,)
    ).fetchone()[0]


def get_google_fit_credentials():
    try:
        google_fit_config = st.secrets["google_fit"]
    except Exception:
        return None
    client_id = str(google_fit_config.get("client_id", "")).strip()
    client_secret = str(google_fit_config.get("client_secret", "")).strip()
    redirect_uri = str(google_fit_config.get("redirect_uri", "")).strip()
    if not client_id or not client_secret or not redirect_uri:
        return None
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }


def current_google_fit_tokens():
    tokens = st.session_state.get("google_fit_tokens")
    return tokens if isinstance(tokens, dict) else None


def google_fit_connected():
    return bool(st.session_state.get("google_fit_connected", False))


def step_demo_sync_enabled():
    return USE_STEP_DEMO_DATA and google_fit_connected()


def is_step_goal_habit(name, target_value, unit):
    normalized_name = (name or "").strip().lower()
    return (
        ((target_value or 0) >= STEP_TARGET and (unit or "").lower() == "steps")
        or normalized_name in {DEMO_WALK_HABIT.lower(), LEGACY_WALK_HABIT.lower()}
    )


def set_google_fit_connection(connected):
    st.session_state["google_fit_connected"] = bool(connected)
    if not connected:
        st.session_state.pop("google_fit_tokens", None)
        st.session_state.pop("google_fit_last_code", None)
        st.session_state.pop("google_fit_oauth_state", None)
    st.session_state["google_fit_error"] = ""


def render_google_fit_connection_action(auth_url, key_prefix):
    if google_fit_connected():
        if st.button("Disconnect Google Fit", key=f"{key_prefix}-disconnect-google-fit", use_container_width=True):
            set_google_fit_connection(False)
            st.rerun()
    else:
        if auth_url:
            render_html(
                f"""
                <div style="margin-top:0.75rem;">
                    <a href="{escape(auth_url)}" style="display:flex;align-items:center;justify-content:center;min-height:44px;padding:0.8rem 1rem;border-radius:999px;background:#123322;color:#fffdf6;text-decoration:none;font-weight:600;box-shadow:0 14px 32px rgba(18,51,34,0.16);">
                        Connect Google Fit
                    </a>
                </div>
                """
            )
        else:
            st.button("Connect Google Fit", key=f"{key_prefix}-connect-google-fit", use_container_width=True, disabled=True)


def disconnected_step_sync_html():
    return html_string(
        '<div style="margin-top:0.9rem;">'
        '<div class="section-copy">Google Fit / Fitbit not connected</div>'
        '<div class="habit-meta" style="margin-top:0.28rem; font-size:0.76rem;">Track manually or connect Google Fit to sync steps automatically.</div>'
        '</div>'
    )


def manual_progress_html(progress_pct, progress_fill_style, done, extra_html=""):
    return html_string(
        f'<div style="margin-top:0.9rem;">'
        f'<div class="health-row"><span>Today progress</span><span>{progress_pct}%</span></div>'
        f'<div class="xp-bar" style="margin-top:0.7rem;"><div class="xp-fill" style="{progress_fill_style} width:{progress_pct}%;"></div></div>'
        f'{extra_html}'
        f'</div>'
    )


def build_connect_google_fit_url():
    creds = get_google_fit_credentials()
    if not creds:
        return None
    state = secrets.token_urlsafe(16)
    st.session_state["google_fit_oauth_state"] = state
    return build_google_fit_auth_url(
        creds["client_id"],
        creds["redirect_uri"],
        state,
    )


def handle_google_fit_oauth_callback():
    query_params = st.query_params
    code = query_params.get("code")
    oauth_state = query_params.get("state")
    oauth_error = query_params.get("error")
    if isinstance(code, list):
        code = code[0]
    if isinstance(oauth_state, list):
        oauth_state = oauth_state[0]
    if isinstance(oauth_error, list):
        oauth_error = oauth_error[0]
    if oauth_error:
        st.session_state["google_fit_error"] = "Google Fit connection was cancelled."
        query_params.clear()
        return
    if not code:
        return
    if st.session_state.get("google_fit_last_code") == code:
        return
    expected_state = st.session_state.get("google_fit_oauth_state")
    if expected_state and oauth_state != expected_state:
        st.session_state["google_fit_error"] = "Google Fit login could not be verified."
        query_params.clear()
        return
    creds = get_google_fit_credentials()
    if not creds:
        st.session_state["google_fit_error"] = "Google Fit credentials are missing."
        query_params.clear()
        return
    try:
        tokens = exchange_google_fit_code(
            code,
            creds["client_id"],
            creds["client_secret"],
            creds["redirect_uri"],
        )
        st.session_state["google_fit_tokens"] = tokens
        st.session_state["google_fit_connected"] = True
        st.session_state["google_fit_error"] = ""
        st.session_state["google_fit_last_code"] = code
    except GoogleFitOAuthError as exc:
        st.session_state["google_fit_error"] = str(exc)
    query_params.clear()
    st.session_state["active_tab"] = "profile"
    st.rerun()


def get_step_snapshot():
    creds = get_google_fit_credentials()
    tokens = current_google_fit_tokens()
    if creds and tokens:
        try:
            provider = GoogleFitStepTrackerProvider(
                tokens,
                creds["client_id"],
                creds["client_secret"],
            )
            snapshot = provider.get_today_snapshot()
            st.session_state["google_fit_tokens"] = provider.updated_tokens
            st.session_state["google_fit_error"] = ""
            return snapshot
        except GoogleFitOAuthError as exc:
            st.session_state["google_fit_error"] = str(exc)
    else:
        st.session_state.setdefault("google_fit_error", "")
    return SimulatedStepTrackerProvider().get_today_snapshot()


def load_demo_steps():
    demo_path = Path(__file__).resolve().parent / STEP_DEMO_FILE
    fallback = {
        "date": date.today().isoformat(),
        "steps": 0,
        "source": "Local demo data unavailable",
    }
    if not demo_path.exists():
        return fallback["date"], fallback["steps"], fallback["source"]
    try:
        payload = json.loads(demo_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return fallback["date"], fallback["steps"], fallback["source"]

    payload_date = str(payload.get("date") or fallback["date"])
    raw_steps = payload.get("steps", 0)
    try:
        steps = max(0, int(raw_steps))
    except (TypeError, ValueError):
        steps = 0
    source = str(payload.get("source") or "Local demo data")
    return payload_date, steps, source


def get_step_integration_state():
    if step_demo_sync_enabled():
        demo_date, demo_steps, demo_source = load_demo_steps()
        progress_pct = min(100, int((demo_steps / STEP_TARGET) * 100))
        return {
            "date": demo_date,
            "steps": demo_steps,
            "source": demo_source,
            "synced_at": "Local demo file",
            "last_synced": "Local demo file",
            "connected": True,
            "source_status": "Connected",
            "error": "",
            "provider_used": "Local demo JSON",
            "raw_response": {},
            "data_source_names": ["Google Fit", "Fitbit"],
            "fallback_active": True,
            "notice": "",
            "time_range": "00:00 - 23:59",
            "last_updated": demo_date,
            "target": STEP_TARGET,
            "progress_pct": progress_pct,
            "completed": demo_steps >= STEP_TARGET,
            "integration_label": "Connected via Google Fit / Fitbit",
            "demo_source_note": f"Demo data source: {demo_source}",
            "uses_demo_data": True,
        }

    if not google_fit_connected():
        return {
            "date": date.today().isoformat(),
            "steps": 0,
            "source": "",
            "synced_at": "Not connected",
            "last_synced": "Not connected",
            "connected": False,
            "source_status": "Disconnected",
            "error": "",
            "provider_used": "Manual tracking",
            "raw_response": {},
            "data_source_names": [],
            "fallback_active": False,
            "notice": "",
            "time_range": "00:00 - 23:59",
            "last_updated": "Not connected",
            "target": STEP_TARGET,
            "progress_pct": 0,
            "completed": False,
            "integration_label": "Google Fit / Fitbit not connected",
            "demo_source_note": "",
            "uses_demo_data": False,
        }

    snapshot = get_step_snapshot()
    steps = max(0, int(snapshot.steps))
    progress_pct = min(100, int((steps / STEP_TARGET) * 100))
    return {
        "date": snapshot.date,
        "steps": steps,
        "source": snapshot.source,
        "synced_at": snapshot.synced_at,
        "last_synced": snapshot.synced_at,
        "connected": bool(snapshot.connected),
        "source_status": "Connected" if snapshot.connected else "Disconnected",
        "error": snapshot.error,
        "provider_used": snapshot.provider_used or snapshot.source,
        "raw_response": snapshot.raw_response or {},
        "data_source_names": list(snapshot.data_source_names),
        "fallback_active": bool(snapshot.fallback_active),
        "notice": snapshot.notice,
        "time_range": "00:00 - 23:59",
        "last_updated": snapshot.synced_at,
        "target": STEP_TARGET,
        "progress_pct": progress_pct,
        "completed": steps >= STEP_TARGET,
        "integration_label": "Connected via Google Fit / Fitbit" if snapshot.connected else "Google Fit / Fitbit not connected",
        "demo_source_note": "",
        "uses_demo_data": False,
    }


def is_auto_step_habit(verification_mode, target_value, unit):
    return google_fit_connected() and (target_value or 0) >= STEP_TARGET and (unit or "").lower() == "steps"


def calculate_streak(habit_id):
    streak = 0
    streak_day = date.today()
    while True:
        done = conn.execute(
            "SELECT 1 FROM checkins WHERE habit_id=? AND date=?",
            (habit_id, streak_day.isoformat()),
        ).fetchone()
        if not done:
            break
        streak += 1
        streak_day -= timedelta(days=1)
    return streak


def calculate_stage(streak, total_completions):
    progress = max(streak, total_completions)
    if progress <= 0:
        return 0
    if progress >= 50:
        return 5
    if progress >= 21:
        return 4
    if progress >= 7:
        return 3
    if progress >= 3:
        return 2
    return 1


def display_stage_for_today(stage, completed_today):
    if completed_today:
        return max(stage, 2)
    return stage


def current_season():
    month = date.today().month
    if month in {12, 1, 2}:
        return "winter"
    if month in {3, 4, 5}:
        return "spring"
    if month in {6, 7, 8}:
        return "summer"
    return "autumn"


def season_overlay(season):
    return ""


def stage_name(stage):
    return ["Seed", "Seedling", "Sapling", "Young Tree", "Mature Tree", "Legendary Tree"][stage]


def level_from_xp(xp):
    level = max(1, xp // 150 + 1)
    current_floor = (level - 1) * 150
    current_ceiling = level * 150
    return level, current_floor, current_ceiling


def longest_streak():
    longest = 0
    for hid, _ in habits:
        dates = [date.fromisoformat(row[0]) for row in conn.execute(
            "SELECT date FROM checkins WHERE habit_id=? ORDER BY date ASC", (hid,)
        ).fetchall()]
        running = 0
        last_day = None
        for entry in dates:
            if last_day and entry == last_day + timedelta(days=1):
                running += 1
            elif last_day and entry == last_day:
                continue
            else:
                running = 1
            last_day = entry
            longest = max(longest, running)
    return longest


def active_habits_count():
    return conn.execute("SELECT COUNT(*) FROM habits").fetchone()[0]


def habit_completed_today(habit_id, verification_mode=None, target_value=None, unit=None):
    if verification_mode is None or target_value is None or unit is None:
        row = conn.execute(
            "SELECT verification_mode, target_value, unit FROM habits WHERE id=?",
            (habit_id,),
        ).fetchone()
        if row:
            verification_mode, target_value, unit = row
    if is_auto_step_habit(verification_mode, target_value, unit):
        return bool(step_integration["completed"])
    return bool(
        conn.execute("SELECT 1 FROM checkins WHERE habit_id=? AND date=?", (habit_id, today)).fetchone()
    )


def completed_today_count():
    total = 0
    for hid, verification_mode, target_value, unit in conn.execute(
        "SELECT id, verification_mode, target_value, unit FROM habits"
    ).fetchall():
        if habit_completed_today(hid, verification_mode, target_value, unit):
            total += 1
    return total


def perfect_week_bonus():
    days = [(date.today() - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    return all(checkins_for_day(conn, day) > 0 for day in days)


def complete_habit(habit_id, value=None, note="Completed today"):
    existing = conn.execute(
        "SELECT 1 FROM checkins WHERE habit_id=? AND date=?",
        (habit_id, today),
    ).fetchone()
    if existing:
        return False

    conn.execute(
        "INSERT OR IGNORE INTO checkins (habit_id, date, value, note) VALUES (?, ?, ?, ?)",
        (habit_id, today, value, note),
    )

    habit_row = conn.execute(
        "SELECT health, total_completions FROM habits WHERE id=?",
        (habit_id,),
    ).fetchone()
    current_health = habit_row[0] or 0
    current_total = habit_row[1] or 0
    new_total = current_total + 1
    new_health = min(100, current_health + 20)
    new_streak = calculate_streak(habit_id)
    streak_bonus = 5 if new_streak and new_streak % 7 == 0 else 0
    xp_gain = 10 + min(new_streak * 2, 20) + streak_bonus
    if perfect_week_bonus():
        xp_gain += 15

    conn.execute(
        "UPDATE habits SET total_completions=?, health=?, streak=? WHERE id=?",
        (new_total, new_health, new_streak, habit_id),
    )
    st.session_state["xp"] = st.session_state.get("xp", 0) + xp_gain
    st.session_state["last_xp_gain"] = xp_gain
    st.session_state["last_completed_habit"] = habit_id
    conn.commit()
    return True


def auto_complete_step_habit_if_needed(habit_id, step_state):
    if not habit_id or not step_state["completed"]:
        return False
    return complete_habit(
        habit_id,
        value=step_state["steps"],
        note=AUTO_STEP_NOTE,
    )


def sync_step_habit_status(habit_id, step_state):
    if not habit_id:
        return False
    existing = conn.execute(
        "SELECT id, note FROM checkins WHERE habit_id=? AND date=?",
        (habit_id, today),
    ).fetchone()
    if step_state["completed"]:
        if existing:
            return False
        return complete_habit(habit_id, value=step_state["steps"], note=AUTO_STEP_NOTE)

    if not existing or existing[1] != AUTO_STEP_NOTE:
        return False

    conn.execute("DELETE FROM checkins WHERE id=?", (existing[0],))
    total = conn.execute(
        "SELECT COUNT(*) FROM checkins WHERE habit_id=?",
        (habit_id,),
    ).fetchone()[0]
    health = conn.execute(
        "SELECT health FROM habits WHERE id=?",
        (habit_id,),
    ).fetchone()[0] or 0
    conn.execute(
        "UPDATE habits SET total_completions=?, streak=?, health=? WHERE id=?",
        (total, calculate_streak(habit_id), max(0, health - 20), habit_id),
    )
    conn.commit()
    return True


def apply_failure_states():
    if st.session_state.get("failure_checked_for") == today:
        return
    for hid, _, verification_mode, target_value in conn.execute(
        "SELECT id, name, verification_mode, target_value FROM habits"
    ).fetchall():
        done_today = conn.execute(
            "SELECT 1 FROM checkins WHERE habit_id=? AND date=?", (hid, today)
        ).fetchone()
        if done_today:
            continue
        health = conn.execute("SELECT health FROM habits WHERE id=?", (hid,)).fetchone()[0] or 0
        penalty = 12 if verification_mode == "auto" and (target_value or 0) >= 10000 else 6
        conn.execute(
            "UPDATE habits SET health=? WHERE id=?",
            (max(0, health - penalty), hid),
        )
    conn.commit()
    st.session_state["failure_checked_for"] = today


def habit_completion_rate(habit_id, days):
    total = conn.execute(
        "SELECT COUNT(*) FROM checkins WHERE habit_id=? AND date >= ?",
        (habit_id, (date.today() - timedelta(days=days - 1)).isoformat()),
    ).fetchone()[0]
    return round((total / max(1, days)) * 100)


def get_user_stats():
    xp = st.session_state.get("xp", 0)
    level, xp_floor, xp_ceiling = level_from_xp(xp)
    xp_progress = int(((xp - xp_floor) / max(1, xp_ceiling - xp_floor)) * 100)
    return {
        "xp": xp,
        "level": level,
        "xp_progress": min(100, max(0, xp_progress)),
        "xp_to_next": max(0, xp_ceiling - xp),
        "longest_streak": longest_streak(),
        "total_completions": conn.execute("SELECT COUNT(*) FROM checkins").fetchone()[0],
        "active_habits": active_habits_count(),
        "completed_today": completed_today_count(),
    }


def render_step_integration_card(step_state, done_today):
    is_completed = bool(step_state.get("completed"))
    status_text = "Completed" if is_completed else "Not completed"
    status_class = "status-done" if is_completed else "status-pending"
    source_status_class = "status-done" if step_state.get("connected") else "status-pending"
    progress_text = (
        "Automatically completed via external step integration"
        if is_completed
        else f'{step_state["steps"]:,} / {step_state["target"]:,} steps'
    )
    render_html(
        f"""
        <div class="insight-card">
            <div class="insight-title">External Integration</div>
            <div class="insight-copy">{progress_text}</div>
            <div class="mini-metrics">
                <div class="mini-tile"><div class="metric-label">Source</div><div class="metric-value" style="font-size:0.82rem;">{escape(step_state["source"])}</div></div>
                <div class="mini-tile"><div class="metric-label">Today</div><div class="metric-value">{step_state["steps"]:,}</div></div>
                <div class="mini-tile"><div class="metric-label">Target</div><div class="metric-value">{step_state["target"]:,}</div></div>
            </div>
            <div class="health-row" style="margin-top:0.8rem;"><span>Status</span><span class="status-pill {status_class}">{status_text}</span></div>
            <div class="health-row" style="margin-top:0.55rem;"><span>Last synced</span><span>{escape(step_state["synced_at"])}</span></div>
            <div class="health-row" style="margin-top:0.45rem;"><span>Source status</span><span class="status-pill {source_status_class}">{escape(step_state["source_status"])}</span></div>
            <div class="xp-bar" style="margin-top:0.75rem;"><div class="xp-fill" style="width:{step_state["progress_pct"]}%;"></div></div>
        </div>
        """
    )


def render_step_progress_summary(step_state, done_today):
    is_completed = bool(step_state.get("completed"))
    summary = f'{step_state["steps"]:,} / {step_state["target"]:,} steps'
    subcopy = "Automatically tracked" if step_state.get("connected") else "Automatic tracking unavailable"
    render_html(
        f"""
        <div class="section-card compact-card">
            <div class="health-row"><span>Step progress</span><span class="status-pill {'status-done' if is_completed else 'status-pending'}">{'Completed' if is_completed else 'In progress'}</span></div>
            <div class="section-heading" style="font-size:1.02rem; margin-top:0.45rem;">{summary}</div>
            <div class="section-copy">{subcopy}</div>
            <div class="xp-bar" style="margin-top:0.75rem;"><div class="xp-fill" style="width:{step_state["progress_pct"]}%;"></div></div>
        </div>
        """
    )


def inline_step_progress_html(step_state, show_status=True):
    is_completed = bool(step_state.get("completed"))
    status_text = "Completed" if is_completed else "Not completed"
    summary = f'{step_state["steps"]:,} / {step_state["target"]:,} steps'
    subcopy = escape(step_state.get("integration_label") or ("Automatically tracked" if step_state.get("connected") else "Automatic tracking unavailable"))
    demo_note = step_state.get("demo_source_note")
    status_row = (
        f"""<div class="health-row"><span>Status</span><span class="status-pill {'status-done' if is_completed else 'status-pending'}">{status_text}</span></div>"""
        if show_status
        else ""
    )
    demo_note_html = (
        f'<div class="habit-meta" style="margin-top:0.28rem; font-size:0.76rem;">{escape(demo_note)}</div>'
        if demo_note
        else ""
    )
    return html_string(
        f'<div style="margin-top:0.9rem;">'
        f'{status_row}'
        f'<div class="section-heading" style="font-size:1.02rem; margin-top:0.45rem;">{summary}</div>'
        f'<div class="section-copy">{subcopy}</div>'
        f'{demo_note_html}'
        f'<div class="xp-bar" style="margin-top:0.7rem;"><div class="xp-fill" style="width:{step_state["progress_pct"]}%;"></div></div>'
        f'</div>'
    )


def virtual_trees_planted():
    return max(0, (conn.execute("SELECT COUNT(*) FROM checkins").fetchone()[0] + longest_streak()) // 18)


def impact_stats():
    trees = virtual_trees_planted()
    return {
        "trees": trees,
        "co2": trees * 21,
        "days_restored": trees * 14,
        "habitats": max(0, trees // 2),
    }


def render_growth_timeline_section():
    timeline_items = []
    day_streak = 0
    for i in range(13, -1, -1):
        current_day = date.today() - timedelta(days=i)
        day = current_day.isoformat()
        count = checkins_for_day(conn, day)
        day_streak = day_streak + 1 if count > 0 else 0
        stage = calculate_stage(day_streak, day_streak)
        timeline_items.append(
            html_string(
                f"""
                <div style="min-width:58px;width:58px;flex:0 0 auto;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;text-align:center;">
                    <div style="display:flex;align-items:flex-end;justify-content:center;height:64px;margin:0;padding:0;">
                        {tree_svg(stage, "#3ddc84", 100, "small")}
                    </div>
                    <div style="margin-top:6px;color:#54674f;opacity:1;font-weight:700;font-size:11px;line-height:1.2;">{current_day.strftime("%a")}</div>
                    <div style="margin-top:2px;color:#647360;opacity:1;font-weight:600;font-size:11px;line-height:1.2;">{current_day.strftime("%d %b")}</div>
                </div>
                """
            )
        )
    render_html(
        """
        <div class="section-card">
            <div class="eyebrow">Growth timeline</div>
            <div class="section-heading">How your forest is evolving</div>
        </div>
        """
    )
    render_html(
        '<div style="display:flex;gap:6px;overflow-x:auto;overflow-y:hidden;padding-top:0.1rem;padding-bottom:0.15rem;-webkit-overflow-scrolling:touch;scrollbar-width:none;">'
        + "".join(timeline_items)
        + "</div>"
    )
    render_html(
        f"""
        <div class="impact-card">
            <div class="section-heading">Impact</div>
            <div class="mini-metrics">
                <div class="mini-tile"><div class="metric-label">Trees</div><div class="metric-value">{impact["trees"]}</div></div>
                <div class="mini-tile"><div class="metric-label">CO2</div><div class="metric-value">{impact["co2"]}</div></div>
                <div class="mini-tile"><div class="metric-label">Care days</div><div class="metric-value">{impact["days_restored"]}</div></div>
            </div>
        </div>
        """
    )


def group_challenge_state():
    member_status = [12, 9, 15, streak]
    shared_streak = min(member_status)
    warning = any(value < 7 for value in member_status)
    progress = min(100, round((sum(member_status) / max(1, len(member_status) * 14)) * 100))
    return {
        "goal": "Collectively complete 40 mindful check-ins this week",
        "shared_streak": shared_streak,
        "progress": progress,
        "warning": warning,
    }


def friend_forest_markup():
    cards = []
    for friend in MOCK_FRIENDS:
        stage = calculate_stage(friend["streak"], friend["streak"] * 2)
        status_class = "status-ok" if friend["streak"] >= streak else "status-warn"
        cards.append(
            html_string(
                f"""
                <div class="friend-card">
                    <div class="friend-top">
                        <div class="friend-name" style="display:flex;align-items:center;gap:0.55rem;">{avatar_svg(friend["name"], 28, "#a6d96a")}<span>{friend["name"]}</span></div>
                        <div class="streak-badge">{friend["streak"]} day streak</div>
                    </div>
                    <div class="share-preview">{tree_svg(stage, "#52d68a", 88, "medium")}</div>
                    <div class="friend-copy {status_class}">{friend["message"]}</div>
                </div>
                """
            )
        )
    return "".join(cards)


def onboarding_markup():
    if st.session_state.get("onboarding_dismissed"):
        return ""
    return html_string(
        """
        <div class="onboarding-card">
            <div class="eyebrow">First-time onboarding</div>
            <div class="section-heading">How HabitForest works</div>
            <div class="step-list">
                <div class="step-item">1. Create a habit and assign it a category, icon, and color.</div>
                <div class="step-item">2. Complete it daily to grow a dedicated tree from seed to legendary canopy.</div>
                <div class="step-item">3. Protect tree health, earn XP, and unlock real-world tree planting milestones.</div>
            </div>
        </div>
        """
    )


def mini_forest_markup(limit=5):
    rows = conn.execute(
        "SELECT name, color, health, streak, total_completions FROM habits ORDER BY id LIMIT ?",
        (limit,),
    ).fetchall()
    if not rows:
        return '<div class="share-preview"><div class="friend-copy">Add a few habits to generate a shareable forest preview.</div></div>'
    trees = []
    for name, color, health, stored_streak, total_completions in rows:
        stage = calculate_stage(stored_streak or 0, total_completions or 0)
        trees.append(
            html_string(
                f"""
                <div style="display:flex;flex-direction:column;align-items:center;gap:0.3rem;">
                    {tree_svg(stage, color or '#52d68a', health or 100, 'small')}
                    <div class="forest-label">{escape(name[:12])}</div>
                </div>
                """
            )
        )
    return f'<div class="share-preview"><div class="mini-forest">{"".join(trees)}</div></div>'


def accountability_markup():
    messages = []
    for friend in MOCK_FRIENDS:
        tone_class = "status-ok" if friend["streak"] >= streak else "status-warn"
        messages.append(
            html_string(
                f"""
                <div class="comparison-card">
                    <div class="comparison-name" style="display:flex;align-items:center;gap:0.55rem;">{avatar_svg(friend["name"], 24, "#a6d96a")}<span>{friend["name"]}</span></div>
                    <div class="comparison-meta {tone_class}">{friend["message"]}</div>
                </div>
                """
            )
        )
    return "".join(messages)


def ngo_partner_markup():
    cards = []
    for partner in NGO_PARTNERS:
        cards.append(
            html_string(
                f"""
                <div class="partner-card">
                    <div class="eyebrow">NGO partner placeholder</div>
                    <div class="partner-name">{escape(partner["name"])}</div>
                    <div class="partner-copy">{escape(partner["focus"])}</div>
                </div>
                """
            )
        )
    return "".join(cards)


def insight_summary(rate, comparison_rows):
    weakest = min(comparison_rows, key=lambda row: row["rate"]) if comparison_rows else None
    strongest = max(comparison_rows, key=lambda row: row["rate"]) if comparison_rows else None
    improve = f"Focus on {weakest['name']} next. It has the lowest completion rate at {weakest['rate']}%." if weakest else "Add a few habits to generate deeper insights."
    momentum = f"Your strongest habit is {strongest['name']} at {strongest['rate']}%." if strongest else "Momentum will appear after your first completions."
    consistency = "Consistency is strong enough to grow a resilient canopy." if rate >= 70 else "Consistency is patchy. Protect two habits this week and let the rhythm spread."
    suggestion = "Try pairing a mindfulness habit with a fitness or sleep habit for better weekly balance."
    return improve, momentum, consistency, suggestion


def get_achievements():
    habit_rows = conn.execute(
        "SELECT id, name, category, verification_mode, target_value, total_completions FROM habits"
    ).fetchall()
    all_checkin_dates = [row[0] for row in conn.execute("SELECT date FROM checkins").fetchall()]
    current_months = {date.fromisoformat(day).month for day in all_checkin_dates} if all_checkin_dates else set()
    max_habit_streak = 0
    for row in habit_rows:
        max_habit_streak = max(max_habit_streak, calculate_streak(row[0]))

    hydration_unlocked = any(
        "water" in (row[1] or "").lower()
        or "hydration" in (row[1] or "").lower()
        or (row[2] or "").lower() == "hydration"
        for row in habit_rows
    )
    step_master_unlocked = any(
        (row[3] or "").lower() == "auto" and (row[4] or 0) >= 10000 and (row[5] or 0) > 0
        for row in habit_rows
    )

    return [
        {"title": "First Sprout", "icon": "", "unlocked": total_checkins >= 1, "copy": "Complete your first habit check-in."},
        {"title": "Week Warrior", "icon": "", "unlocked": max_habit_streak >= 7 or streak >= 7, "copy": "Hold a 7-day streak on any habit."},
        {"title": "Forest Keeper", "icon": "", "unlocked": total_habits >= 5, "copy": "Grow your forest to five habits."},
        {"title": "Hydration Hero", "icon": "", "unlocked": hydration_unlocked, "copy": "Track and complete a hydration habit."},
        {"title": "Step Master", "icon": "", "unlocked": step_master_unlocked, "copy": "Complete a 10,000-step auto habit."},
        {"title": "World Changer", "icon": "", "unlocked": total_checkins >= 50, "copy": "Reach 50 total habit completions."},
        {"title": "Winter Warrior", "icon": "", "unlocked": any(month in {12, 1, 2} for month in current_months), "copy": "Check in during the winter season."},
        {"title": "Legendary", "icon": "", "unlocked": max_habit_streak >= 50 or total_checkins >= 100, "copy": "Build a legendary streak or 100 lifetime completions."},
    ]


def analytics_window(selection):
    today_date = date.today()
    if selection == "Weekly":
        days = 7
    elif selection == "Monthly":
        days = 30
    else:
        days = 365
    return today_date - timedelta(days=days - 1), days


def motivational_message(completion_rate):
    if completion_rate >= 80:
        return "Your canopy is thriving. Keep pressing while the rhythm is strong."
    if completion_rate >= 50:
        return "The forest is taking root. A few more consistent days will thicken the canopy."
    if completion_rate > 0:
        return "You have momentum. Protect the next few days and the pattern will start to hold."
    return "Start with one check-in today. A forest begins with a single sprout."


def milestone_progress(streak):
    if streak >= 7:
        return "Real tree unlocked"
    return f"{7 - streak} more days to your real tree milestone"


def tree_svg(stage, color, health, size="small"):
    size_map = {
        "small": ("56", "80"),
        "medium": ("64", "92"),
        "large": ("76", "108"),
    }
    width, height = size_map.get(size, size_map["small"])
    canopy_opacity = max(0.45, min(1.0, health / 100))
    season = current_season()
    overlay = season_overlay(season)
    low_health = health < 40
    fallen = health <= 0

    if fallen:
        return (
            f'<svg viewBox="0 0 64 96" width="{width}" height="{height}" aria-hidden="true">'
            '<ellipse cx="32" cy="88" rx="18" ry="5" fill="#314d35"/>'
            '<rect x="18" y="72" width="28" height="8" rx="4" fill="#6b4f2a" transform="rotate(-12 32 76)"/>'
            '<circle cx="46" cy="70" r="5" fill="#8a4f4f" fill-opacity="0.55"/>'
            '<circle cx="18" cy="78" r="4" fill="#8a4f4f" fill-opacity="0.4"/>'
            "</svg>"
        )

    if stage == 0:
        return (
            f'<svg viewBox="0 0 64 96" width="{width}" height="{height}" aria-hidden="true">'
            '<ellipse cx="32" cy="88" rx="16" ry="5" fill="#314d35"/>'
            '<circle cx="26" cy="82" r="2" fill="#7bc96f"/>'
            '<circle cx="38" cy="83" r="2" fill="#7bc96f"/>'
            f"{overlay}"
            "</svg>"
        )

    if stage == 1:
        return (
            f'<svg viewBox="0 0 64 96" width="{width}" height="{height}" aria-hidden="true">'
            '<ellipse cx="32" cy="88" rx="17" ry="5" fill="#314d35"/>'
            '<rect x="30" y="70" width="4" height="10" rx="2" fill="#6b4f2a"/>'
            f'<path d="M32 70 C24 65 23 57 30 53 C32 58 39 66 32 70 Z" fill="{color}" fill-opacity="{canopy_opacity}"/>'
            f'<path d="M32 70 C40 65 41 57 34 53 C32 58 25 66 32 70 Z" fill="#7fdc8f" fill-opacity="{canopy_opacity}"/>'
            f"{overlay}"
            "</svg>"
        )

    if stage == 2:
        return (
            f'<svg viewBox="0 0 64 96" width="{width}" height="{height}" aria-hidden="true">'
            '<ellipse cx="32" cy="88" rx="18" ry="5" fill="#314d35"/>'
            '<rect x="29" y="58" width="6" height="22" rx="3" fill="#6b4f2a"/>'
            f'<circle cx="25" cy="58" r="9" fill="{color}" fill-opacity="{canopy_opacity}"/>'
            f'<circle cx="39" cy="56" r="10" fill="#3da95f" fill-opacity="{canopy_opacity}"/>'
            f'<circle cx="32" cy="46" r="10" fill="#82db8b" fill-opacity="{canopy_opacity}"/>'
            f"{'' if not low_health else '<circle cx=\"43\" cy=\"69\" r=\"3.5\" fill=\"#8b5a3c\" fill-opacity=\"0.6\"/>'}"
            f"{overlay}"
            "</svg>"
        )

    if stage == 3:
        return (
            f'<svg viewBox="0 0 64 96" width="{width}" height="{height}" aria-hidden="true">'
            '<ellipse cx="32" cy="88" rx="20" ry="5" fill="#314d35"/>'
            '<rect x="28" y="48" width="8" height="32" rx="3" fill="#6b4f2a"/>'
            f'<circle cx="23" cy="50" r="11" fill="{color}" fill-opacity="{canopy_opacity}"/>'
            f'<circle cx="41" cy="48" r="12" fill="#2f8f4c" fill-opacity="{canopy_opacity}"/>'
            f'<circle cx="32" cy="37" r="13" fill="#7fdf8d" fill-opacity="{canopy_opacity}"/>'
            f'{" " if low_health else f"<circle cx=\"32\" cy=\"54\" r=\"10\" fill=\"#59c975\" fill-opacity=\"{canopy_opacity}\"/>"}'
            f"{'' if not low_health else '<circle cx=\"44\" cy=\"68\" r=\"4\" fill=\"#8b5a3c\" fill-opacity=\"0.65\"/><circle cx=\"20\" cy=\"72\" r=\"3\" fill=\"#8b5a3c\" fill-opacity=\"0.45\"/>'}"
            f"{overlay}"
            "</svg>"
        )

    if stage == 4:
        return (
            f'<svg viewBox="0 0 64 96" width="{width}" height="{height}" aria-hidden="true">'
            '<ellipse cx="32" cy="88" rx="21" ry="5" fill="#314d35"/>'
            '<rect x="27" y="38" width="10" height="42" rx="3" fill="#6b4f2a"/>'
            f'<circle cx="21" cy="40" r="12" fill="{color}" fill-opacity="{canopy_opacity}"/>'
            f'<circle cx="43" cy="38" r="14" fill="#287a41" fill-opacity="{canopy_opacity}"/>'
            f'<circle cx="31" cy="27" r="15" fill="#7fdf8d" fill-opacity="{canopy_opacity}"/>'
            f'<circle cx="29" cy="46" r="12" fill="#4bbb64" fill-opacity="{canopy_opacity}"/>'
            f'{" " if low_health else f"<circle cx=\"45\" cy=\"51\" r=\"9\" fill=\"#68d67b\" fill-opacity=\"{canopy_opacity}\"/>"}'
            f"{'' if not low_health else '<circle cx=\"46\" cy=\"71\" r=\"4\" fill=\"#8b5a3c\" fill-opacity=\"0.7\"/><circle cx=\"24\" cy=\"75\" r=\"3.5\" fill=\"#8b5a3c\" fill-opacity=\"0.55\"/>'}"
            f"{overlay}"
            "</svg>"
        )

    return (
        f'<svg viewBox="0 0 64 96" width="{width}" height="{height}" aria-hidden="true">'
        '<ellipse cx="32" cy="88" rx="22" ry="5" fill="#314d35"/>'
        '<rect x="26" y="28" width="12" height="52" rx="4" fill="#6b4f2a"/>'
        f'<circle cx="20" cy="34" r="12" fill="{color}" fill-opacity="{canopy_opacity}"/>'
        f'<circle cx="44" cy="33" r="15" fill="#23753d" fill-opacity="{canopy_opacity}"/>'
        f'<circle cx="32" cy="20" r="16" fill="#8be79a" fill-opacity="{canopy_opacity}"/>'
        f'<circle cx="28" cy="40" r="14" fill="#4cc66b" fill-opacity="{canopy_opacity}"/>'
        f'{" " if low_health else f"<circle cx=\"46\" cy=\"48\" r=\"10\" fill=\"#6fe084\" fill-opacity=\"{canopy_opacity}\"/>"}'
        f"{'' if not low_health else '<circle cx=\"20\" cy=\"78\" r=\"4\" fill=\"#8b5a3c\" fill-opacity=\"0.65\"/><circle cx=\"48\" cy=\"73\" r=\"3.5\" fill=\"#8b5a3c\" fill-opacity=\"0.55\"/><circle cx=\"36\" cy=\"76\" r=\"3\" fill=\"#8b5a3c\" fill-opacity=\"0.45\"/>'}"
        f"{overlay}"
        "</svg>"
    )


handle_google_fit_oauth_callback()
google_fit_auth_url = build_connect_google_fit_url()

conn = get_conn()
walk_habit_id = find_demo_walk_habit(conn)
today = date.today().isoformat()
step_integration = get_step_integration_state()
step_habit_auto_completed = sync_step_habit_status(walk_habit_id, step_integration)
streak = 0
streak_day = date.today()
st.session_state.setdefault("xp", 0)
apply_failure_states()

while True:
    streak_count = checkins_for_day(conn, streak_day.isoformat())
    if streak_count == 0:
        break
    streak += 1
    streak_day -= timedelta(days=1)

st.markdown(html_string(PAGE_CSS), unsafe_allow_html=True)
render_html(
    """
    <style>
        .app-header,
        .section-card,
        .habit-card,
        .insight-card,
        .user-card,
        .achievement-card,
        .connection-card,
        .friend-card,
        .share-card,
        .partner-card,
        .comparison-card,
        .table-card,
        .ad-card,
        .onboarding-card {
            background:
                radial-gradient(circle at top right, rgba(169, 207, 121, 0.14), transparent 28%),
                linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 253, 246, 0.94));
            backdrop-filter: blur(18px);
            border-color: rgba(111, 166, 74, 0.14);
            box-shadow: 0 18px 50px rgba(62, 88, 54, 0.10);
        }
        .app-icon {
            width: 46px;
            height: 46px;
            border-radius: 18px;
            font-size: 0;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.28), 0 10px 30px rgba(111, 166, 74, 0.12);
        }
        .app-icon svg,
        .achievement-icon svg {
            display: block;
            margin: 0 auto;
        }
        .section-heading,
        .forest-heading,
        .overview-tree-title,
        .habit-name,
        .user-name {
            letter-spacing: -0.02em;
            color: #123322;
        }
    .app-subtitle,
    .metric-label,
    .habit-status {
        color: #5f6f5b;
        opacity: 1 !important;
        }
        .eyebrow,
        .insight-title {
            color: #6fa64a !important;
            opacity: 1 !important;
        }
        .section-copy,
        .habit-meta,
        .dashboard-habit-meta,
        .friend-copy,
        .achievement-copy,
        .user-meta,
        .xp-label,
        .forest-label {
            color: #6f7d6a;
        }
        .forest-grid .forest-label,
        .forest-labels .forest-label {
            color: #eaf6e6 !important;
            opacity: 1 !important;
            font-weight: 600 !important;
            font-size: 0.78rem !important;
            line-height: 1.35 !important;
        }
        .overview-tree-body,
        .share-preview,
        .tree-wrap {
            background:
                radial-gradient(circle at top, rgba(127, 191, 77, 0.10), transparent 48%),
                linear-gradient(180deg, rgba(247, 244, 234, 0.65), rgba(255, 255, 255, 0.3));
            border: 1px solid rgba(111,166,74,0.08);
        }
        .overview-tree-body svg,
        .forest-tree svg,
        .share-preview svg {
            filter: drop-shadow(0 12px 28px rgba(111, 166, 74, 0.10));
        }
        .today-ring {
            width: 132px;
            height: 132px;
            background:
                radial-gradient(circle at center, rgba(127, 191, 77, 0.16), rgba(127, 191, 77, 0.02)),
                conic-gradient(var(--primary) var(--progress), rgba(255,255,255,0.06) 0);
            box-shadow: inset 0 0 0 1px rgba(111,166,74,0.08), 0 18px 40px rgba(62, 88, 54, 0.12);
        }
        .today-ring-inner {
            width: 94px;
            height: 94px;
            background: rgba(255, 253, 246, 0.96);
            box-shadow: inset 0 0 0 1px rgba(111,166,74,0.08);
        }
        .streak-badge,
        .status-pill {
            box-shadow: inset 0 0 0 1px rgba(111,166,74,0.08);
        }
        div[data-testid="stExpander"] details {
            color: #f8f6ee !important;
        }
        div[data-testid="stButton"] > button,
        div[data-testid="stFormSubmitButton"] > button {
            min-height: 44px;
            font-size: 0.95rem;
            letter-spacing: -0.01em;
            color: #fffdf6 !important;
        }
    div[data-testid="stButton"] > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover,
    div[data-testid="stButton"] > button:active,
    div[data-testid="stFormSubmitButton"] > button:active,
    div[data-testid="stButton"] > button:disabled,
    div[data-testid="stFormSubmitButton"] > button:disabled {
        color: #fffdf6 !important;
        opacity: 1 !important;
    }
    .welcome-screen {
        min-height: calc(100% - 10px);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding: 0.6rem 0 0.25rem;
        box-sizing: border-box;
    }
    .welcome-hero {
        text-align: center;
        padding-top: 2.1rem;
    }
    .welcome-logo {
        width: 98px;
        height: 98px;
        margin: 0 auto 1.3rem;
        border-radius: 32px;
        display: grid;
        place-items: center;
        background:
            radial-gradient(circle at 30% 30%, rgba(169, 207, 121, 0.65), rgba(127, 191, 77, 0.18) 50%, rgba(255,255,255,0.75) 100%);
        box-shadow: 0 20px 44px rgba(111, 166, 74, 0.16), inset 0 0 0 1px rgba(255,255,255,0.5);
    }
    .welcome-title {
        font-size: 2.5rem;
        line-height: 1;
        letter-spacing: -0.05em;
        font-weight: 700;
        margin-bottom: 0.85rem;
    }
    .welcome-title .habit {
        color: #7fbf4d;
    }
    .welcome-title .forest {
        color: #123322;
    }
    .welcome-subtitle {
        color: #5f6f5b;
        font-size: 1.04rem;
        line-height: 1.45;
        max-width: 240px;
        margin: 0 auto;
    }
    .welcome-scene {
        position: relative;
        height: 280px;
        margin-top: 1.2rem;
        overflow: hidden;
    }
    .welcome-scene::before,
    .welcome-scene::after {
        content: "";
        position: absolute;
        border-radius: 999px;
        background: rgba(127, 191, 77, 0.15);
        filter: blur(2px);
    }
    .welcome-scene::before {
        width: 22px;
        height: 14px;
        top: 28px;
        left: 18%;
        transform: rotate(-24deg);
    }
    .welcome-scene::after {
        width: 18px;
        height: 12px;
        top: 58px;
        right: 19%;
        transform: rotate(18deg);
    }
    .welcome-art {
        width: 100%;
        height: 100%;
        display: block;
    }
    .welcome-actions {
        margin-top: auto;
        padding-bottom: 0.45rem;
    }
    .debug-card {
        background: linear-gradient(180deg, rgba(6, 14, 10, 0.98), rgba(9, 22, 15, 0.99)) !important;
        border: 1px solid rgba(127, 191, 77, 0.22) !important;
        border-radius: 20px !important;
        padding: 0.9rem 1rem !important;
        box-shadow: 0 16px 40px rgba(3, 10, 7, 0.32) !important;
        color: #f8fbf6 !important;
    }
    .debug-card * {
        color: inherit !important;
        opacity: 1 !important;
        text-shadow: none !important;
    }
    .debug-card .section-heading {
        color: #b8f07b !important;
        font-size: 1rem !important;
        line-height: 1.3 !important;
    }
    .debug-card .eyebrow,
    .debug-card .insight-title {
        color: #b8f07b !important;
    }
    .debug-card .section-copy,
    .debug-card .forest-label,
    .debug-card .metric-label,
    .debug-card .health-row span:first-child {
        color: #dce8da !important;
    }
    .debug-card .health-row span:last-child,
    .debug-card .friend-copy,
    .debug-card .achievement-copy {
        color: #ffffff !important;
    }
    .debug-card .health-row {
        padding: 0.18rem 0;
        gap: 0.85rem;
    }
    .debug-card .section-copy {
        line-height: 1.5 !important;
    }
    .debug-json-shell {
        background: linear-gradient(180deg, rgba(5, 12, 9, 0.99), rgba(8, 18, 13, 0.99));
        border: 1px solid rgba(127, 191, 77, 0.22);
        border-radius: 18px;
        padding: 0.6rem;
        box-shadow: inset 0 0 0 1px rgba(255,255,255,0.03);
    }
    .debug-json-shell [data-testid="stJson"] {
        background: transparent !important;
        color: #f8fbf6 !important;
    }
    .debug-json-shell [data-testid="stJson"] * {
        color: #f8fbf6 !important;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace !important;
        opacity: 1 !important;
    }
    .debug-json-shell [data-testid="stJson"] pre,
    .debug-json-shell [data-testid="stJson"] code {
        background: transparent !important;
        color: #f8fbf6 !important;
        line-height: 1.5 !important;
    }
    .debug-json-shell [data-testid="stJson"] span,
    .debug-json-shell [data-testid="stJson"] div,
    .debug-json-shell [data-testid="stJson"] p {
        color: #f8fbf6 !important;
    }
    </style>
    """
)
milestone_key = "milestone_shown_for"
show_milestone = streak == 7 and st.session_state.get(milestone_key) != today

if show_milestone:
    st.session_state[milestone_key] = today
    st.markdown(
        html_string(
            """
        <div class="celebration-card">
            <div class="eyebrow">Milestone reached</div>
            <div class="hero-title">You've planted a real tree!</div>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )
    st.balloons()

habits = get_display_habits(conn)
total_habits = len(habits)
total_checkins = conn.execute("SELECT COUNT(*) FROM checkins").fetchone()[0]
st.session_state.setdefault("xp", 0)
user_stats = get_user_stats()
impact = impact_stats()
week_start = (date.today() - timedelta(days=6)).isoformat()
week_checkins = conn.execute(
    "SELECT COUNT(*) FROM checkins WHERE date >= ?", (week_start,)
).fetchone()[0]
best_day_row = conn.execute(
    "SELECT date, COUNT(*) AS total FROM checkins GROUP BY date ORDER BY total DESC, date DESC LIMIT 1"
).fetchone()
best_day_label = best_day_row[0] if best_day_row else "No check-ins yet"
best_day_total = best_day_row[1] if best_day_row else 0

st.session_state.setdefault("show_welcome", True)
st.session_state.setdefault("show_signup", False)
st.session_state.setdefault("welcome_notice", "")
signup_query_flag = st.query_params.get("signup")
if signup_query_flag == "1" and st.session_state.get("show_welcome"):
    st.session_state["show_signup"] = True
    st.query_params.pop("signup", None)
if st.session_state.get("show_welcome"):
    render_html(
        f"""
        <div class="welcome-screen">
            <div class="welcome-hero">
                <div class="welcome-logo">{app_logo_svg(54)}</div>
                <div class="welcome-title"><span class="habit">Habit</span> <span class="forest">Forest</span></div>
                <div class="welcome-subtitle">Build better habits.<br>Grow every day.</div>
                <div class="welcome-scene">
                    <svg class="welcome-art" viewBox="0 0 320 280" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                        <defs>
                            <linearGradient id="welcomeGlow" x1="160" y1="0" x2="160" y2="280" gradientUnits="userSpaceOnUse">
                                <stop stop-color="#F4F7E8"/>
                                <stop offset="1" stop-color="#EEF3DE"/>
                            </linearGradient>
                            <linearGradient id="hillBack" x1="160" y1="100" x2="160" y2="240" gradientUnits="userSpaceOnUse">
                                <stop stop-color="#E7EFD7"/>
                                <stop offset="1" stop-color="#DCE8C7"/>
                            </linearGradient>
                            <linearGradient id="hillFront" x1="160" y1="120" x2="160" y2="260" gradientUnits="userSpaceOnUse">
                                <stop stop-color="#D8E6BF"/>
                                <stop offset="1" stop-color="#C9DBAA"/>
                            </linearGradient>
                        </defs>
                        <rect width="320" height="280" rx="36" fill="url(#welcomeGlow)"/>
                        <ellipse cx="160" cy="118" rx="132" ry="58" fill="rgba(127, 191, 77, 0.10)"/>
                        <path d="M0 184C41 159 84 147 123 153C155 158 184 173 217 174C255 176 286 159 320 142V280H0V184Z" fill="url(#hillBack)"/>
                        <path d="M0 208C45 188 92 186 131 194C168 201 196 219 233 221C266 223 292 214 320 201V280H0V208Z" fill="url(#hillFront)"/>
                        <g opacity="0.62" stroke="#7FBF4D" stroke-linecap="round">
                            <path d="M68 210 L80 186 L92 210" stroke-width="4"/>
                            <path d="M82 187 L82 225" stroke-width="4"/>
                            <path d="M138 200 L153 171 L168 200" stroke-width="4.5"/>
                            <path d="M153 172 L153 230" stroke-width="4.5"/>
                            <path d="M210 214 L223 188 L236 214" stroke-width="4"/>
                            <path d="M223 189 L223 232" stroke-width="4"/>
                            <path d="M250 206 L261 183 L272 206" stroke-width="3.8"/>
                            <path d="M261 184 L261 226" stroke-width="3.8"/>
                        </g>
                    </svg>
                </div>
            </div>
            <div class="welcome-actions">
            </div>
        </div>
        """
    )
    if st.session_state.get("show_signup"):
        render_html(
            """
            <div class="section-card" style="margin-top:1rem;">
                <div class="section-heading">Create Account</div>
                <div class="section-copy">Set up your HabitForest account to save progress across devices in a future release.</div>
            </div>
            """
        )
        full_name = st.text_input("Full Name", key="signup-full-name")
        email_address = st.text_input("Email Address", key="signup-email-address")
        password = st.text_input("Password", type="password", key="signup-password")
        confirm_password = st.text_input("Confirm Password", type="password", key="signup-confirm-password")
        signup_cols = st.columns(2, gap="small")
        if signup_cols[0].button("Create Account", key="welcome-create-account", type="primary", use_container_width=True):
            if not all([
                full_name.strip(),
                email_address.strip(),
                password.strip(),
                confirm_password.strip(),
            ]):
                st.error("Please complete all fields.")
            else:
                st.session_state["welcome_notice"] = "Account created successfully. Welcome to HabitForest!"
                st.session_state["show_signup"] = False
                st.session_state["show_welcome"] = False
                st.session_state["active_tab"] = "forest"
                st.rerun()
        if signup_cols[1].button("Back to Log In", key="welcome-back-to-login", use_container_width=True):
            st.session_state["show_signup"] = False
            st.rerun()
    else:
        if st.button("Log In", key="welcome-log-in", type="primary", use_container_width=True):
            st.session_state["show_welcome"] = False
            st.session_state["active_tab"] = "forest"
            st.rerun()
        render_html(
            f"""
            <div style="text-align:center; margin-top:0.85rem; color:#6f7d6a; font-size:0.8rem;">
                <span>New here?</span>
                <a href="?signup=1" style="color:#4f7f39; font-weight:600; text-decoration:none; margin-left:0.18rem;">Sign up</a>
            </div>
            """
        )
    st.stop()

initial_tab = st.query_params.get("tab", st.session_state.get("active_tab", "forest"))
if isinstance(initial_tab, list):
    initial_tab = initial_tab[0]
initial_tab = str(initial_tab).lower()
if initial_tab not in {"forest", "today", "insights", "profile"}:
    initial_tab = "forest"
st.session_state.setdefault("active_tab", initial_tab)
current_tab = st.session_state.get("active_tab", "forest")

if st.session_state.get("welcome_notice"):
    st.success(st.session_state["welcome_notice"])
    st.session_state["welcome_notice"] = ""

content_container = st.container()
with content_container:
    render_html('<div class="content-scroll-marker" aria-hidden="true"></div>')
    if current_tab == "forest":
        render_html(
            f"""
            <div class="app-header">
                <div class="app-header-top">
                    <div class="app-logo">
                        <div class="app-icon">{app_logo_svg(28)}</div>
                        <div>
                            <div class="app-title">HabitForest</div>
                            <div class="app-subtitle">Grow your forest with calm daily rituals</div>
                        </div>
                    </div>
                    <div class="streak-badge">{streak} day streak</div>
                </div>
                <div class="xp-wrap" style="margin-top:0;">
                    <div class="xp-bar"><div class="xp-fill" style="width:{user_stats["xp_progress"]}%;"></div></div>
                    <div class="xp-label"><span>Level {user_stats["level"]}</span><span>{user_stats["xp"]} XP</span></div>
                </div>
            </div>
            """
        )
        if not habits:
            render_html(
                """
                <div class="section-card">
                    <div class="section-heading">No trees yet</div>
                    <p class="section-copy">Add one habit to start your forest.</p>
                </div>
                """
            )
        filter_cols = st.columns([1.3, 1])
        habit_search = filter_cols[0].text_input("Search habits", placeholder="Search your trees")
        category_filter = filter_cols[1].selectbox("Category filter", ["all"] + CATEGORY_CHOICES)

        filtered_habits = []
        overview_cards = []
        for hid, name in habits:
            row = conn.execute(
                "SELECT category, icon, color, verification_mode, health, target_value, unit, total_completions FROM habits WHERE id=?",
                (hid,),
            ).fetchone()
            category, icon, color, verification_mode, health, target_value, unit, total_completions = row
            if habit_search and habit_search.lower() not in name.lower():
                continue
            if category_filter != "all" and (category or "custom") != category_filter:
                continue
            filtered_habits.append((hid, name))
            is_step_goal = is_step_goal_habit(name, target_value, unit)
            is_step_habit = is_auto_step_habit(verification_mode, target_value, unit)
            display_name = "10.000 steps" if is_step_goal else name
            done = step_integration["completed"] if is_step_habit else conn.execute("SELECT 1 FROM checkins WHERE habit_id=? AND date=?", (hid, today)).fetchone()
            current_streak = calculate_streak(hid)
            stage = display_stage_for_today(calculate_stage(current_streak, total_completions or 0), bool(done))
            icon_display = habit_visual_icon(category, color or "#7ac943", 18)
            status_text = "Completed" if done else ("Not completed" if is_step_habit else "Open today")
            overview_cards.append(
                html_string(
                    f"""
                    <div class="overview-tree-card">
                        <div class="overview-tree-title" style="display:flex;align-items:center;gap:0.55rem;">{icon_display}<span>{escape(display_name)}</span></div>
                        <div class="dashboard-habit-meta">{escape((category or 'custom').title())}</div>
                        <div class="overview-tree-body">{tree_svg(stage, color or '#52d68a', health or 100, 'large')}</div>
                        <div class="health-row"><span>{current_streak}d streak</span><span>{int(health or 0)}%</span></div>
                        <div class="health-bar"><div class="health-fill" style="width:{int(health or 0)}%; background:linear-gradient(90deg, {escape(color or '#3ddc84')}, #6fbf73);"></div></div>
                        <div class="status-pill {'status-done' if done else 'status-pending'}">{status_text}</div>
                    </div>
                    """
                )
            )

        render_html(
            f'<div class="forest-overview-grid">{"".join(overview_cards)}</div>'
            if overview_cards
            else """
            <div class="section-card">
                <div class="section-heading">No matches</div>
                <p class="section-copy">Try another filter.</p>
            </div>
            """
        )
        forest_selector_items = filtered_habits if filtered_habits else habits
        if forest_selector_items:
            selector_details = []
            valid_selector_ids = set()
            for hid, name in forest_selector_items:
                category, verification_mode, target_value, unit = conn.execute(
                    "SELECT category, verification_mode, target_value, unit FROM habits WHERE id=?",
                    (hid,),
                ).fetchone()
                is_step_goal = is_step_goal_habit(name, target_value, unit)
                is_step_habit = is_auto_step_habit(verification_mode, target_value, unit)
                display_name = "10.000 steps" if is_step_goal else name
                selector_details.append((hid, display_name, category))
                valid_selector_ids.add(str(hid))

            raw_selected_habit = str(st.session_state.get("forest_selected_habit", str(selector_details[0][0])))
            if raw_selected_habit not in valid_selector_ids:
                raw_selected_habit = str(selector_details[0][0])
            selector_map = {str(hid): display_name for hid, display_name, _category in selector_details}
            selector_ids = [str(hid) for hid, _, _category in selector_details]
            st.session_state.setdefault("show_add_habit_form", False)
            if st.button(
                "+ Add Habit" if not st.session_state["show_add_habit_form"] else "Close",
                key="toggle-add-habit",
                use_container_width=True,
            ):
                st.session_state["show_add_habit_form"] = not st.session_state["show_add_habit_form"]
                st.rerun()
            if st.session_state["show_add_habit_form"]:
                render_html(
                    """
                    <div class="add-habit-panel">
                        <div class="section-heading">Create habit</div>
                        <div class="add-habit-copy">Add one simple ritual and let it become part of your forest.</div>
                    </div>
                    """
                )
                with st.form("add_habit", clear_on_submit=True):
                    name_col, category_col = st.columns(2)
                    mode_col, color_col = st.columns(2)
                    new_name = name_col.text_input("Habit name")
                    new_category = category_col.selectbox("Category", CATEGORY_CHOICES)
                    new_mode = mode_col.selectbox("Tracking", ["manual", "auto"])
                    new_color = color_col.color_picker("Color", value="#3ddc84")
                    if st.form_submit_button("Add Habit") and new_name.strip():
                        conn.execute(
                            """
                            INSERT INTO habits (
                                name, category, icon, color, target_value, unit, verification_mode,
                                health, streak, total_completions, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                new_name.strip(),
                                new_category,
                                "",
                                new_color,
                                10000 if new_mode == "auto" else None,
                                "steps" if new_mode == "auto" else "",
                                new_mode,
                                100,
                                0,
                                0,
                                date.today().isoformat(),
                            ),
                        )
                        conn.commit()
                        st.session_state["show_add_habit_form"] = False
                        st.rerun()
            render_html('<div class="forest-selector-label">Choose habit</div>')
            selected_forest_hid = st.selectbox(
                "Choose habit",
                selector_ids,
                index=selector_ids.index(raw_selected_habit),
                format_func=lambda hid: selector_map.get(str(hid), str(hid)),
                key="forest_selected_habit",
                label_visibility="collapsed",
            )
            selected_forest_hid = int(selected_forest_hid)
            icon, color, category, verification_mode, health, total_completions, target_value, unit = conn.execute(
                "SELECT icon, color, category, verification_mode, health, total_completions, target_value, unit FROM habits WHERE id=?",
                (selected_forest_hid,),
            ).fetchone()
            current_streak = calculate_streak(selected_forest_hid)
            selected_stage = calculate_stage(current_streak, total_completions or 0)
            selected_forest_name = next(name for hid, name in habits if hid == selected_forest_hid)
            is_step_goal = is_step_goal_habit(selected_forest_name, target_value, unit)
            is_step_habit = is_auto_step_habit(verification_mode, target_value, unit)
            selected_display_name = "10.000 steps" if is_step_goal else selected_forest_name
            done = step_integration["completed"] if is_step_habit else conn.execute("SELECT 1 FROM checkins WHERE habit_id=? AND date=?", (selected_forest_hid, today)).fetchone()
            selected_stage = display_stage_for_today(selected_stage, bool(done))
            if True:
                step_progress_block = inline_step_progress_html(step_integration, show_status=False) if is_step_habit else ""
                forest_manual_progress_block = (
                    manual_progress_html(
                        100 if done else 0,
                        f"background:linear-gradient(90deg, {escape(color or '#3ddc84')}, {escape(color or '#3ddc84')});",
                        bool(done),
                        "",
                    )
                    if is_step_goal and not is_step_habit
                    else ""
                )
                render_html(
                    f"""
                    <div class="section-card">
                        <div class="overview-tree-title" style="display:flex;align-items:center;gap:0.6rem;">{habit_visual_icon(category, color or '#7ac943', 20)}<span>{escape(selected_display_name)}</span></div>
                        <div class="dashboard-habit-meta">{escape((category or 'custom').title())} · {stage_name(selected_stage)}</div>
                        <div class="overview-tree-body floating-tree">{tree_svg(selected_stage, color or '#7ac943', health or 100, 'large')}</div>
                        <div class="mini-metrics">
                            <div class="mini-tile"><div class="metric-label">Streak</div><div class="metric-value">{current_streak}d</div></div>
                            <div class="mini-tile"><div class="metric-label">Health</div><div class="metric-value">{int(health or 0)}%</div></div>
                            <div class="mini-tile"><div class="metric-label">Today</div><div class="metric-value">{'Completed' if done else ('Not completed' if is_step_habit else 'Open')}</div></div>
                        </div>
                        {step_progress_block}
                    </div>
                    """
                )
                if forest_manual_progress_block:
                    render_html(f'<div class="section-card">{forest_manual_progress_block}</div>')
                if not is_step_habit:
                    if st.button("Complete selected habit", key=f"forest-complete-{selected_forest_hid}", disabled=bool(done), use_container_width=True):
                        complete_habit(selected_forest_hid)
                        render_html(
                            """
                            <div class="celebration-card">
                                <div class="eyebrow">Growth</div>
                                <div class="hero-title">Tree strengthened</div>
                            </div>
                            """
                        )
                        st.rerun()
        else:
            render_html(
                """
                <div class="section-card">
                    <div class="section-heading">No habits available</div>
                    <p class="section-copy">Create a habit to start growing your forest.</p>
                </div>
                """
            )
    if current_tab == "today":
        render_html(
            f"""
            <div class="page-header">
                <div>
                    <div class="page-title">Today</div>
                    <div class="page-subtitle">Check in and keep momentum</div>
                </div>
                <div class="page-indicator">{streak}d streak</div>
            </div>
            """
        )
        if not habits:
            render_html(
                """
                <div class="section-card">
                    <div class="section-heading">No habits available yet</div>
                    <p class="section-copy">Create your first habit in the Forest tab, then return here to complete it.</p>
                </div>
                """
            )
        else:
            progress_pct = int((user_stats["completed_today"] / max(1, total_habits)) * 100)
            render_html(
                f"""
                <div class="section-card compact-progress">
                    <div class="health-row"><span>Today</span><span>{user_stats["completed_today"]}/{total_habits}</span></div>
                    <div class="today-ring" style="--progress:{progress_pct}%;">
                        <div class="today-ring-inner">{progress_pct}%<br><span class="forest-label">done</span></div>
                    </div>
                </div>
                """
            )
            today_search = st.text_input("Search habits", placeholder="Find a habit", key="today-search")

            visible_today_habits = []
            for hid, name in habits:
                if today_search and today_search.lower() not in name.lower():
                    continue
                visible_today_habits.append((hid, name))

            for hid, name in visible_today_habits:
                category, icon, color, verification_mode, health, target_value, unit = conn.execute(
                    "SELECT category, icon, color, verification_mode, health, target_value, unit FROM habits WHERE id=?",
                    (hid,),
                ).fetchone()
                is_step_goal = is_step_goal_habit(name, target_value, unit)
                is_step_habit = is_auto_step_habit(verification_mode, target_value, unit)
                display_name = "10.000 steps" if is_step_goal else name
                done = step_integration["completed"] if is_step_habit else conn.execute("SELECT 1 FROM checkins WHERE habit_id=? AND date=?", (hid, today)).fetchone()
                meta_lines = [f"{(category or 'custom').title()}"]
                if target_value:
                    meta_lines.append(f"{target_value} {unit or ''}".strip())
                meta_text = " &#183; ".join(escape(item) for item in meta_lines)
                status_text = "Completed" if done else ("Not completed" if is_step_habit else "Ready")
                step_progress_block = inline_step_progress_html(step_integration, show_status=False) if is_step_habit else ""
                connection_hint_block = disconnected_step_sync_html() if is_step_goal and not is_step_habit else ""
                manual_progress_pct = 100 if done else 0
                progress_fill_style = f"background:linear-gradient(90deg, {escape(color or '#3ddc84')}, {escape(color or '#3ddc84')});"
                progress_block = (
                    step_progress_block.replace(
                        '<div class="xp-fill" style="width:',
                        f'<div class="xp-fill" style="{progress_fill_style} width:'
                    )
                    if is_step_habit
                    else manual_progress_html(manual_progress_pct, progress_fill_style, bool(done), connection_hint_block)
                )
                render_html(
                    f"""<div class="habit-card">
<div class="action-row">
<div>
<div class="habit-name" style="display:flex;align-items:center;gap:0.55rem;">{habit_visual_icon(category, color or '#7ac943', 18)}<span>{escape(display_name)}</span></div>
<div class="habit-meta">{meta_text}</div>
<div class="habit-status">{status_text}</div>
</div>
<div class="streak-badge">{calculate_streak(hid)} days</div>
</div>
{progress_block}
</div>"""
                )
                if not is_step_habit:
                    if (not done) and st.button("Complete today", key=f"today-done-{hid}", disabled=False, use_container_width=True):
                        complete_habit(hid)
                        st.rerun()
    if current_tab == "insights":
        render_html(
            f"""
            <div class="page-header">
                <div>
                    <div class="page-title">Insights</div>
                    <div class="page-subtitle">Clarity on your rhythm and growth</div>
                </div>
                <div class="page-indicator">Lv {user_stats["level"]}</div>
            </div>
            """
        )
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_dates = [week_start + timedelta(days=i) for i in range(7)]
        week_counts = []
        for current_day in week_dates:
            week_counts.append((current_day, checkins_for_day(conn, current_day.isoformat())))
        weekly_completions = sum(count for _, count in week_counts)
        weekly_possible = max(1, total_habits * 7)
        weekly_completion_rate = round((weekly_completions / weekly_possible) * 100)
        weekly_active_days = sum(1 for _, count in week_counts if count > 0)

        comparison_rows = []
        for hid, name in habits:
            total = conn.execute("SELECT total_completions FROM habits WHERE id=?", (hid,)).fetchone()[0] or 0
            comparison_rows.append(
                {
                    "id": hid,
                    "name": "10.000 steps" if hid == walk_habit_id else name,
                    "streak": calculate_streak(hid),
                    "rate": habit_completion_rate(hid, 7),
                    "total": total,
                }
            )
        comparison_rows.sort(key=lambda row: (row["rate"], row["streak"], row["total"]), reverse=True)
        best_habit = comparison_rows[0] if comparison_rows else None
        worst_habit = min(comparison_rows, key=lambda row: (row["rate"], row["streak"], row["total"])) if comparison_rows else None

        hero_title = f"You completed {weekly_completion_rate}% of your habits this week"
        hero_subtitle = (
            f"{weekly_completions} check-ins across {weekly_active_days} active days."
            if weekly_completions
            else "Your forest is ready for its first consistent week."
        )
        if best_habit and best_habit["streak"] >= 3:
            hero_note = f"Best streak: {escape(best_habit['name'])} ({best_habit['streak']} days)"
        elif impact["trees"] > 0:
            hero_note = f"Your forest has already grown {impact['trees']} tree{'s' if impact['trees'] != 1 else ''}."
        else:
            hero_note = "Small daily check-ins grow into visible progress."

        render_html(
            f"""
            <div class="section-card" style="background:
                radial-gradient(circle at top right, rgba(169, 207, 121, 0.18), transparent 28%),
                linear-gradient(180deg, rgba(255,255,255,0.98), rgba(244,250,236,0.98));">
                <div class="eyebrow">Hero insight</div>
                <div class="hero-title" style="font-size:1.65rem;">{hero_title}</div>
                <div class="section-copy" style="margin-top:0.45rem;">{hero_subtitle}</div>
                <div class="habit-meta" style="margin-top:0.6rem;">{hero_note}</div>
            </div>
            """
        )

        max_day_total = max((count for _, count in week_counts), default=1)
        weekly_bars = []
        for current_day, count in week_counts:
            fill_pct = 0 if max_day_total <= 0 else int((count / max_day_total) * 100)
            weekly_bars.append(
                html_string(
                    f"""
                    <div style="min-width:38px;display:flex;flex-direction:column;align-items:center;gap:0.35rem;flex:1 1 0;">
                        <div style="height:78px;width:100%;display:flex;align-items:flex-end;">
                            <div style="width:100%;height:{max(8, int(fill_pct * 0.78))}px;border-radius:12px 12px 6px 6px;background:linear-gradient(180deg, rgba(122,201,67,0.95), rgba(61,175,95,0.92));"></div>
                        </div>
                        <div style="color:#5F6F5B;font-size:11px;font-weight:600;line-height:1.2;">{current_day.strftime('%a')}</div>
                    </div>
                    """
                )
            )
        render_html(
            f"""
            <div class="section-card">
                <div class="eyebrow">Weekly consistency</div>
                <div class="section-heading">Your week at a glance</div>
                <div style="display:flex;gap:0.45rem;align-items:flex-end;margin-top:0.8rem;">
                    {''.join(weekly_bars)}
                </div>
            </div>
            """
        )
        render_growth_timeline_section()

        best_card = (
            f"""
            <div class="section-card compact-card">
                <div class="eyebrow">Best habit</div>
                <div class="section-heading">{escape(best_habit['name'])}</div>
                <div class="habit-meta">{best_habit['rate']}% completion rate</div>
                <div class="section-copy" style="margin-top:0.45rem;">{best_habit['streak']} day streak</div>
            </div>
            """
            if best_habit
            else """
            <div class="section-card compact-card">
                <div class="eyebrow">Best habit</div>
                <div class="section-heading">No data yet</div>
            </div>
            """
        )
        attention_card = (
            f"""
            <div class="section-card compact-card">
                <div class="eyebrow">Needs attention</div>
                <div class="section-heading">{escape(worst_habit['name'])}</div>
                <div class="habit-meta">{worst_habit['rate']}% completion rate</div>
                <div class="section-copy" style="margin-top:0.45rem;">Most skipped this week</div>
            </div>
            """
            if worst_habit
            else """
            <div class="section-card compact-card">
                <div class="eyebrow">Needs attention</div>
                <div class="section-heading">No data yet</div>
            </div>
            """
        )
        render_html(
            f"""
            <div class="comparison-grid" style="grid-template-columns:1fr 1fr;">
                {best_card}
                {attention_card}
            </div>
            """
        )

        forest_growth_items = []
        running_streak = 0
        for current_day, count in week_counts:
            running_streak = running_streak + 1 if count > 0 else 0
            growth_stage = calculate_stage(running_streak, running_streak)
            forest_growth_items.append(
                html_string(
                    f"""
                    <div style="min-width:54px;flex:0 0 auto;display:flex;flex-direction:column;align-items:center;text-align:center;">
                        <div style="height:60px;display:flex;align-items:flex-end;justify-content:center;">{tree_svg(growth_stage, '#3ddc84', 100, 'small')}</div>
                        <div style="margin-top:4px;color:#5f6f5b;font-size:11px;font-weight:600;line-height:1.2;">{current_day.strftime('%a')}</div>
                    </div>
                    """
                )
            )
        render_html(
            f"""
            <div class="impact-card">
                <div class="eyebrow">Forest growth</div>
                <div class="section-heading">Your habits are shaping the forest</div>
                <div class="section-copy" style="margin-top:0.35rem;">Every completed day adds visible growth and strengthens your long-term rhythm.</div>
                <div class="mini-metrics" style="margin-top:0.8rem;">
                    <div class="mini-tile"><div class="metric-label">Trees grown</div><div class="metric-value">{impact["trees"]}</div></div>
                    <div class="mini-tile"><div class="metric-label">Longest streak</div><div class="metric-value">{user_stats["longest_streak"]}d</div></div>
                    <div class="mini-tile"><div class="metric-label">Active habits</div><div class="metric-value">{user_stats["active_habits"]}</div></div>
                </div>
                <div style="display:flex;gap:0.4rem;overflow-x:auto;overflow-y:hidden;padding-top:0.8rem;-webkit-overflow-scrolling:touch;scrollbar-width:none;">
                    {''.join(forest_growth_items)}
                </div>
            </div>
            """
        )

        improve_msg, momentum_msg, consistency_msg, suggestion_msg = insight_summary(weekly_completion_rate, comparison_rows)
        motivation_copy = momentum_msg or motivational_message(weekly_completion_rate)
        suggestions = {
            "Fitness": ["Stretch 5 min", "Walk after lunch", "Mobility reset"],
            "Mindfulness": ["Journal 3 lines", "Meditate 10 min", "One-minute breathing"],
            "Health": ["Drink water", "Sleep by 11 PM", "Take vitamins"],
            "Sleep": ["Phone down at 10 PM", "Sleep ritual", "Wake at consistent time"],
            "Nutrition": ["Protein breakfast", "Add vegetables", "Meal prep check-in"],
            "Focus": ["Deep work block", "Inbox zero sweep", "Read 10 pages"],
        }
        suggestion_cards = []
        for category, items in suggestions.items():
            suggestion_cards.append(
                html_string(
                    f"""
                    <div class="achievement-card">
                        <div class="achievement-title">{category}</div>
                        <div class="achievement-copy">{escape(' · '.join(items))}</div>
                    </div>
                    """
                )
            )
        with st.expander("Habit Intelligence", expanded=False):
            render_html(
                f"""
                <div class="insights-stack">
                    <div class="insight-card">
                        <div class="insight-title">Motivation</div>
                        <div class="insight-copy">{motivation_copy}</div>
                        <div class="habit-meta">{improve_msg or 'Protect the habits that feel easiest to repeat.'}</div>
                        <div class="habit-meta">{consistency_msg or 'Consistency becomes visible when your rhythm stays simple.'}</div>
                        <div class="habit-meta">{suggestion_msg or 'Choose one small win to repeat tomorrow.'}</div>
                    </div>
                    <div class="section-card">
                        <div class="section-heading">Suggestions</div>
                        <div class="achievement-grid">
                            {''.join(suggestion_cards)}
                        </div>
                    </div>
                </div>
                """
            )

    if current_tab == "profile":
        render_html(
            f"""
            <div class="page-header">
                <div>
                    <div class="page-title">Profile</div>
                    <div class="page-subtitle">Account, achievements, and settings</div>
                </div>
                <div class="page-indicator">{user_stats["xp"]} XP</div>
            </div>
            """
        )
        achievements = get_achievements()
        st.session_state.setdefault("profile_username", "Forest Explorer")
        st.session_state.setdefault("profile_avatar", "FE")
        st.session_state.setdefault("google_fit_connected", False)
        st.session_state.setdefault("apple_health_connected", False)
        impact = impact_stats()
        unlocked_achievements = [achievement for achievement in achievements if achievement["unlocked"]]
        featured_badges = unlocked_achievements[:3] if unlocked_achievements else achievements[:3]
        achievement_share_cards = []
        for badge in featured_badges:
            achievement_share_cards.append(
                html_string(
                    f"""
                    <div class="share-card">
                        <div class="share-title" style="display:flex;align-items:center;gap:0.55rem;">{badge_icon_svg(badge["title"], '#a6d96a', 18)}<span>{badge["title"]}</span></div>
                        <div class="share-copy">{badge["copy"]}</div>
                        <div class="season-tag">Ready for Instagram, LinkedIn, or demo slides</div>
                    </div>
                    """
                )
            )
        render_html(
            f"""
            <div class="user-card">
                <div class="user-top">
                    <div>
                        <div class="user-name" style="display:flex;align-items:center;gap:0.7rem;">{avatar_svg(st.session_state["profile_username"], 40, "#7ac943")}<span>{escape(st.session_state["profile_username"])}</span></div>
                        <div class="user-meta">Level {user_stats["level"]} · Growing your forest daily</div>
                    </div>
                    <div class="streak-badge">{len(unlocked_achievements)} badge{'s' if len(unlocked_achievements) != 1 else ''} unlocked</div>
                </div>
                <div class="xp-wrap">
                    <div class="xp-bar"><div class="xp-fill" style="width:{user_stats["xp_progress"]}%;"></div></div>
                    <div class="xp-label"><span>Longest streak: {user_stats["longest_streak"]} day{'s' if user_stats["longest_streak"] != 1 else ''}</span><span>{user_stats["active_habits"]} active habits</span></div>
                </div>
            </div>
            """
        )
        profile_cols = st.columns(2)
        edited_username = profile_cols[0].text_input("Username", value=st.session_state["profile_username"], key="profile-username-input")
        edited_avatar = profile_cols[1].text_input("Initials", value=st.session_state["profile_avatar"], key="profile-avatar-input")
        if st.button("Save profile", key="save-profile", use_container_width=True):
            st.session_state["profile_username"] = edited_username.strip() or "Forest Explorer"
            st.session_state["profile_avatar"] = edited_avatar.strip() or "FE"
            st.success("Demo account updated.")
            st.rerun()

        connection_cards = [
            html_string(
                f"""
                <div class="connection-card">
                    <div class="connection-top">
                        <div class="friend-name">Google Fit / Fitbit</div>
                        <div class="achievement-state {'status-ok' if step_integration['connected'] else 'status-warn'}">{step_integration['source_status']}</div>
                    </div>
                    <div class="friend-copy">{'Connected via Google Fit / Fitbit' if step_integration['connected'] else 'Google Fit / Fitbit not connected'}</div>
                    <div class="habit-meta" style="margin-top:0.35rem;">{'Demo connection complete. HabitForest is using local demo step data after Google authorization.' if step_integration['connected'] else 'Track this habit manually or connect Google Fit to sync steps automatically.'}</div>
                    <div class="habit-meta" style="margin-top:0.35rem;">{'Demo data source: ' + escape(step_integration['source']) if step_integration['connected'] and step_integration.get('source') else ''}</div>
                    <div class="mini-metrics" style="margin-top:0.85rem;">
                        <div class="mini-tile"><div class="metric-label">Tracking</div><div class="metric-value" style="font-size:0.82rem;">Steps</div></div>
                        <div class="mini-tile"><div class="metric-label">Today</div><div class="metric-value">{step_integration['steps']:,}</div></div>
                        <div class="mini-tile"><div class="metric-label">Goal</div><div class="metric-value">{step_integration['target']:,}</div></div>
                    </div>
                    <div class="health-row" style="margin-top:0.8rem;"><span>Sync</span><span>Automatic</span></div>
                    <div class="health-row" style="margin-top:0.45rem;"><span>Last synced</span><span>{escape(step_integration['synced_at'])}</span></div>
                </div>
                """
            )
        ]
        achievement_cards = []
        for achievement in achievements:
            state = "Unlocked" if achievement["unlocked"] else "Locked"
            card_class = "achievement-card unlocked" if achievement["unlocked"] else "achievement-card locked"
            achievement_cards.append(
                html_string(
                    f"""
                <div class="{card_class}">
                    <div class="achievement-icon">{badge_icon_svg(achievement["title"], '#a6d96a' if achievement["unlocked"] else '#b7d3bf', 24)}</div>
                    <div class="achievement-title">{achievement["title"]}</div>
                    <div class="achievement-state">{state}</div>
                    <div class="achievement-copy">{achievement["copy"]}</div>
                </div>
                """
                )
            )
        with st.expander("Achievements", expanded=False):
            render_html(
                f"""
                <div class="section-card">
                    <div class="eyebrow">Achievements</div>
                    <div class="section-heading">{len(unlocked_achievements)} unlocked badges</div>
                    <div class="achievement-grid">
                        {''.join(achievement_cards)}
                    </div>
                </div>
                <div class="section-card">
                    <div class="section-heading">Share cards</div>
                    <div class="share-grid">
                        {''.join(achievement_share_cards)}
                    </div>
                </div>
                """
            )
        with st.expander("Friends & Group Challenge", expanded=False):
            challenge = group_challenge_state()
            group_members = [
                html_string(
                    f"""
                    <div style="display:flex;flex-direction:column;align-items:center;gap:0.35rem;">
                        <div class="forest-label" style="display:flex;flex-direction:column;align-items:center;gap:0.35rem;">{avatar_svg(friend["name"], 26, '#a6d96a')}<span>{escape(friend["name"])}</span></div>
                        {tree_svg(calculate_stage(friend["streak"], friend["streak"] * 2), "#3ddc84", 88, "small")}
                    </div>
                    """
                )
                for friend in MOCK_FRIENDS
            ]
            render_html(
                f"""
                <div class="section-card">
                    <div class="eyebrow">Social demo</div>
                    <div class="section-heading">Shared forest and accountability</div>
                    <div class="friend-grid">{friend_forest_markup()}</div>
                </div>
                <div class="section-card">
                    <div class="eyebrow">Group challenge</div>
                    <div class="section-heading">Shared streak: {challenge["shared_streak"]} days</div>
                    <p class="section-copy">{escape(challenge["goal"])}</p>
                    <div class="xp-bar" style="margin-top:0.75rem;"><div class="xp-fill" style="width:{challenge["progress"]}%;"></div></div>
                    <div class="xp-label"><span>{challenge["progress"]}% progress</span><span>{'One member is slipping' if challenge["warning"] else 'Group momentum is stable'}</span></div>
                    <div class="group-visual">{"".join(group_members)}</div>
                </div>
                """
            )
        with st.expander("Data Connections", expanded=False):
            render_html(
                f"""
                <div class="section-card">
                    <div class="eyebrow">Connected Apps</div>
                    <div class="section-heading">Connected Apps</div>
                    <p class="section-copy">Automatically track your daily activity and habits.</p>
                    <div class="connection-grid">
                        {''.join(connection_cards)}
                    </div>
                </div>
                """
            )
            if st.session_state.get("google_fit_error"):
                render_html(
                    f"""
                    <div class="section-card">
                        <div class="section-heading" style="font-size:1rem;">Connection update</div>
                        <div class="section-copy">{escape(st.session_state['google_fit_error'])}</div>
                    </div>
                    """
                )
            render_google_fit_connection_action(google_fit_auth_url, "profile")
            if step_integration.get("notice"):
                render_html(
                    f"""
                    <div class="section-card">
                        <div class="section-heading" style="font-size:1rem;">Data visibility</div>
                        <div class="section-copy">{escape(step_integration["notice"])}</div>
                    </div>
                    """
                )
        with st.expander("Impact", expanded=False):
            render_html(
                f"""
                <div class="section-card">
                    <div class="eyebrow">Impact layer</div>
                    <div class="section-heading">Trees planted together</div>
                    <p class="section-copy">Your habits helped plant {impact["trees"]} real trees. This section frames the startup story around measurable environmental outcomes.</p>
                    <div class="impact-grid">
                        <div class="impact-pill"><div class="achievement-title">Real trees</div><div class="achievement-copy">{impact["trees"]} funded in the demo narrative</div></div>
                        <div class="impact-pill"><div class="achievement-title">Environmental lift</div><div class="achievement-copy">{impact["co2"]} kg CO2 equivalent captured</div></div>
                        <div class="impact-pill"><div class="achievement-title">Restoration time</div><div class="achievement-copy">{impact["days_restored"]} field-work days supported</div></div>
                        <div class="impact-pill"><div class="achievement-title">Community habitats</div><div class="achievement-copy">{impact["habitats"]} restoration pockets activated</div></div>
                    </div>
                    <div class="friend-grid">
                        {ngo_partner_markup()}
                    </div>
                </div>
                """
            )
        with st.expander("Reset Demo", expanded=False):
            render_html(
                """
                <div class="section-card">
                    <div class="eyebrow">Demo reset</div>
                    <div class="section-heading">Fresh start or demo load</div>
                    <p class="section-copy">Start empty, or load sample habits for presentation mode.</p>
                </div>
                """
            )
            confirm_reset = st.checkbox("I understand this clears current app data", key="confirm-reset-demo")
            if st.button("Reset to fresh start", key="reset-fresh-start", type="primary", use_container_width=True, disabled=not confirm_reset):
                reset_fresh_start(conn)
                clear_app_session_state()
                st.rerun()
            if st.button("Load demo data", key="load-demo-data", use_container_width=True):
                reset_fresh_start(conn)
                load_demo_data(conn)
                clear_app_session_state()
                st.session_state["xp"] = 420
                st.session_state["google_fit_connected"] = False
                st.session_state["apple_health_connected"] = False
                st.rerun()

nav_container = st.container()
with nav_container:
    render_html('<div class="bottom-nav-marker" aria-hidden="true"></div>')
    nav_cols = st.columns(4, gap="small")
    nav_items = [
        ("forest", "Forest"),
        ("today", "Today"),
        ("insights", "Insights"),
        ("profile", "Profile"),
    ]
    for col, (tab_key, tab_label) in zip(nav_cols, nav_items):
        with col:
            if st.button(
                tab_label,
                key=f"bottom-nav-{tab_key}",
                use_container_width=True,
                type="primary" if current_tab == tab_key else "secondary",
            ):
                st.session_state["active_tab"] = tab_key
                st.rerun()
