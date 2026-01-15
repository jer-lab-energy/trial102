import os
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="BESS — Expandable Table", layout="wide")

BASE_DIR = os.path.dirname(__file__)
EXCEL_FILE = "BESS In construction.xlsx"
EXCEL_PATH = os.path.join(BASE_DIR, EXCEL_FILE)

# Expected columns (normalized)
COLUMNS = [
    "Project Name",
    "Company",
    "MW",
    "Location",
    "Connection date",
    "Comments",
    "Sources",
    "PNG Name",
]

# ✅ Hardcode flags here: "g" (green), "r" (red), else "".
# Keys should match Excel Project Name (we strip whitespace when matching).
FLAGS = {
    "Sambar Power": "g",
    "Bradford West 100MW": "r",
    "Bicker Fen 2 Solar": "r",
    "Didcot Energy Park": "r",
    "Berkswell Energy Storage": "",
    "WELBAR ENERGY STORAGE": "g",
    "Cellarhead 400kV Energy Storage": "r",
    "Worset Lane Energy Hub": "r",
    "Sundon Battery Energy Storage": "g",
    "Capenhurst BESS": "g",
    "Legacy": "",
    "Monk Fryston": "g",
    "Whitegate": "r",
    "Iron Acton": "g",
    "Cryogenic Battery System (Synchronous)": "g",
    "Norwich battery storage": "",
    "Bolney Green Energy Hub": "r",
    "Flash Solar Farm (Staythorpe)": "g",
    "Rushett Lane BESS": "r",
    "Bramley co-located bess and solar": "",
    "Fairglen BESS": "r",
    "Goldborough Road BESS": "",
    "Fleet EGH (Tertiary) Coxmoor Wood BESS": "r",
    "WORSET LANE BESS": "r",
    "Keithick Estate, California Farm solar and battery storage": "r",
    "Pembroke BESS": "",
    "Eggborough CCGT - OCGT - BESS": "r",
    "Neilston 400kV Greener Grid Park": "g",
    "Coylton 275kV Greener Grid Park": "g",
    "Sizing John (Rainhill)": "g",
    "Harker Green Energy Centre": "",
    "Zenobe Blackhillock 300 MW": "g",
}

URL_RE = re.compile(r"(https?://[^\s,]+)", re.IGNORECASE)

def normalize_flag(x: str) -> str:
    x = (x or "").strip().lower()
    return x if x in ("g", "r") else ""

def row_flag(project_name: str) -> str:
    key = (project_name or "").strip()
    return normalize_flag(FLAGS.get(key, ""))

def safe_str(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    return str(v)

def png_filename(png_name: str) -> str | None:
    name = (png_name or "").strip()
    if not name:
        return None
    return name if name.lower().endswith(".png") else name + ".png"

def render_sources(text: str):
    t = (text or "").strip()
    if not t:
        st.write("—")
        return
    parts = re.split(r"[;\n]", t)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        urls = URL_RE.findall(part)
        if urls:
            md = part
            for u in urls:
                md = md.replace(u, f"[{u}]({u})")
            st.markdown(f"- {md}")
        else:
            st.markdown(f"- {part}")

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]  # fixes "MW " etc.

    actual_lower = {c.lower(): c for c in df.columns}
    rename = {}
    for expected in COLUMNS:
        key = expected.lower()
        if key in actual_lower:
            rename[actual_lower[key]] = expected
        else:
            df[expected] = ""

    df = df.rename(columns=rename)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""

    return df[COLUMNS].copy()

@st.cache_data(show_spinner=False)
def load_df(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Excel file not found next to app.py: {EXCEL_FILE}")
    df = pd.read_excel(path)
    return normalize_columns(df)

df = load_df(EXCEL_PATH)

# --- expand state ---
if "open_rows" not in st.session_state:
    st.session_state.open_rows = set()

def expand_all():
    st.session_state.open_rows = set(df.index.tolist())

def collapse_all():
    st.session_state.open_rows = set()

# --- build a styled view (bold Project Name + Company, and colour Project Name by flag) ---
def style_df(display_df: pd.DataFrame):
    # We only style the visible table columns; details are rendered below.
    def style_rows(row: pd.Series):
        pname = safe_str(row.get("Project Name", ""))
        f = row_flag(pname)

        styles = [""] * len(row.index)
        col_to_idx = {c: i for i, c in enumerate(row.index)}

        # Bold Project Name + Company
        for c in ("Project Name", "Company"):
            if c in col_to_idx:
                styles[col_to_idx[c]] += "font-weight:700;"

        # Colour Project Name text based on flag
        if "Project Name" in col_to_idx:
            if f == "g":
                styles[col_to_idx["Project Name"]] += "color:#2ecc71;"
            elif f == "r":
                styles[col_to_idx["Project Name"]] += "color:#e74c3c;"

        return styles

    styler = display_df.style.apply(style_rows, axis=1)

    # Make it look like a clean grid
    styler = styler.set_table_styles(
        [
            {"selector": "th", "props": [("text-align", "left")]},
            {"selector": "td", "props": [("text-align", "left"), ("white-space", "pre-wrap")]},
        ]
    )
    return styler

st.title("BESS In construction — table (Excel source)")
st.caption(f"Source: {EXCEL_FILE}. Click rows in the table to expand/collapse details below.")

c1, c2 = st.columns(2)
with c1:
    if st.button("Expand all"):
        expand_all()
with c2:
    if st.button("Collapse all"):
        collapse_all()

# Show the table (without Comments/Sources/PNG Name if you want it cleaner)
TABLE_VIEW_COLS = ["Project Name", "Company", "MW", "Location", "Connection date"]
df_view = df[TABLE_VIEW_COLS].copy()

event = st.dataframe(
    style_df(df_view),
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="multi-row",
)

# Sync open rows to selected rows (click to select/deselect = expand/collapse)
selected = set(event.selection.get("rows", [])) if event and event.selection else set()
# Selection returns row positions in the displayed dataframe; same as df index positions here
st.session_state.open_rows = selected if selected else st.session_state.open_rows

# Expanded details below (in original Excel order)
for i in sorted(st.session_state.open_rows):
    row = df.loc[i]

    pname = safe_str(row.get("Project Name", ""))
    company = safe_str(row.get("Company", ""))
    mw = safe_str(row.get("MW", ""))
    location = safe_str(row.get("Location", ""))
    conn_date = safe_str(row.get("Connection date", ""))

    st.markdown(f"### {pname}")

    left, right = st.columns([1.3, 1.0], gap="large")

    with left:
        # ✅ NEW: replicate table entry as bullet points
        st.markdown("**Project details**")
        st.markdown(
            f"""
- **Project Name:** {pname or "—"}
- **Company:** {company or "—"}
- **MW:** {mw or "—"}
- **Location:** {location or "—"}
- **Connection date:** {conn_date or "—"}
            """.strip()
        )

        st.markdown("**Comments**")
        st.write(safe_str(row.get("Comments", "")) or "—")

        st.markdown("**Sources**")
        render_sources(safe_str(row.get("Sources", "")))

    with right:
        png = png_filename(safe_str(row.get("PNG Name", "")))
        if png:
            img_path = os.path.join(BASE_DIR, png)
            if os.path.exists(img_path):
                st.markdown("**Image**")
                st.image(img_path, use_container_width=True)
            else:
                st.warning(f"PNG not found next to app.py: {png}")
        else:
            st.caption("No PNG Name for this row.")

    st.divider()


