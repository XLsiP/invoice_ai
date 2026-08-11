from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import altair as alt
import pandas as pd
import streamlit as st

from src import analytics
from src.ai_assistant import answer_question
from src.ai_parser import extract_invoice_fields_with_ai
from src.database import (
    delete_invoice,
    get_all_invoices,
    get_invoice_line_items,
    initialize_database,
    save_invoice,
    search_invoices,
    update_invoice,
)
from src.excel_export import export_invoices_to_excel
from src.executive_summary import build_full_executive_report
from src.line_item_parser import extract_line_items_with_ai
from src.parser import extract_invoice_fields
from src.pdf_reader import extract_text_from_file
from src.validator import validate_invoice

APP_NAME = "Accounts Payable"
DATABASE_PATH = Path("data/invoices.db")
UPLOAD_FOLDER = Path("invoices/uploads")
EXCEL_PATH = Path("excel/ap_accounts_payable_ledger.xlsx")
ORGANIZATION_NAME = "Lehigh Valley Phantoms"
LOGO_PATH = Path("assets/phantoms_logo.png")

# ---------------------------------------------------------------------
# Design tokens. Dark navy surface with the Phantoms' own brand colors
# (black, orange, blue — sampled straight from the logo) as accents.
# Used only for actions, active states, and ring/status metrics — never
# large surfaces — so the color still reads as signal, not decoration.
# ---------------------------------------------------------------------

BG = "#0B0E14"
SURFACE = "#151A23"
SURFACE_RAISED = "#1B2130"
BORDER = "#262B3D"
TEXT_PRIMARY = "#F4F4F5"
TEXT_SECONDARY = "#9CA3AF"

PRIMARY = "#F48325"
PRIMARY_DARK = "#D66C13"
BLUE = "#0154A4"
AMBER = "#FBBF24"
ROSE = "#FB7185"

SUCCESS = "#34D399"
SUCCESS_BG = "rgba(52, 211, 153, 0.14)"
WARNING = "#FBBF24"
WARNING_BG = "rgba(251, 191, 36, 0.14)"
DANGER = "#FB7185"
DANGER_BG = "rgba(251, 113, 133, 0.14)"


def apply_styles() -> None:
    """Apply the dark, card-based visual design across the app."""

    st.markdown(
        """
        <style>
        .stApp { background-color: #0B0E14; }

        #MainMenu, footer { visibility: hidden; }
        header { background: transparent; }

        .block-container {
            max-width: 1180px;
            padding-top: 1.5rem;
            padding-bottom: 4rem;
        }

        h1, h2, h3, h4 { color: #F4F4F5 !important; }
        p, label { color: #9CA3AF; }

        /* Section headings */
        .section-label {
            margin-bottom: 4px;
            color: #F48325;
            font-size: 0.72rem;
            font-weight: 750;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }
        .section-title { margin: 0 0 6px; color: #F4F4F5 !important; font-size: 1.6rem; font-weight: 750; }
        .section-description { margin-bottom: 22px; color: #9CA3AF; }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background: #0D111A;
            border-right: 1px solid #262B3D;
        }
        [data-testid="stSidebar"] > div { padding-top: 1.2rem; }

        .ia-brand {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 4px 4px 22px 4px;
            margin-bottom: 6px;
            border-bottom: 1px solid #262B3D;
        }
        .ia-brand-mark {
            width: 52px;
            height: 52px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.92);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            padding: 6px;
        }
        .ia-brand-mark img { width: 100%; height: 100%; object-fit: contain; }
        .ia-brand-mark-fallback {
            background: linear-gradient(135deg, #F48325, #0154A4);
            font-weight: 800;
            font-size: 0.85rem;
            color: #FFFFFF;
        }
        .ia-brand-name { font-weight: 800; font-size: 1.05rem; color: #F4F4F5; letter-spacing: -0.02em; }
        .ia-brand-tagline { font-size: 0.74rem; color: #6B7280; margin-top: -2px; }

        /* Sidebar navigation, styled from Streamlit's radio widget */
        [data-testid="stSidebar"] [data-testid="stRadio"] {
            width: 100%;
            padding: 0;
            background: transparent;
            border: none;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] > div { display: flex; flex-direction: column; gap: 2px; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            justify-content: flex-start;
            padding: 10px 14px;
            border-radius: 8px;
            border-left: 3px solid transparent;
            color: #9CA3AF;
            font-weight: 600;
            cursor: pointer;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background: #161B26; color: #F4F4F5; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
            background: rgba(244, 131, 37, 0.16);
            color: #F4F4F5;
            border-left: 3px solid #F48325;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child { display: none; }

        /* Upload box */
        [data-testid="stFileUploaderDropzone"] {
            min-height: 170px;
            padding: 34px;
            background: #151A23;
            border: 1.5px dashed #363B4D;
            border-radius: 14px;
        }
        [data-testid="stFileUploaderDropzone"]:hover { background: #171C2A; border-color: #F48325; }

        /* Buttons */
        .stButton > button, .stDownloadButton > button {
            min-height: 44px;
            border-radius: 9px;
            font-weight: 650;
            background: #151A23;
            border: 1px solid #262B3D;
            color: #F4F4F5;
        }
        .stButton > button[kind="primary"] {
            color: #0B0E14;
            background: linear-gradient(135deg, #F48325, #FBA857);
            border: none;
        }
        .stButton > button[kind="primary"]:hover { background: linear-gradient(135deg, #D66C13, #F48325); }

        /* Metrics */
        [data-testid="stMetric"] {
            min-height: 100px;
            padding: 16px;
            background: #151A23;
            border: 1px solid #262B3D;
            border-radius: 12px;
        }
        [data-testid="stMetricLabel"] { color: #9CA3AF; }
        [data-testid="stMetricValue"] { color: #F4F4F5; font-size: 1.55rem; font-weight: 750; }

        /* Inputs */
        .stTextInput input {
            min-height: 42px;
            color: #F4F4F5;
            background: #151A23;
            border: 1px solid #262B3D;
            border-radius: 9px;
        }
        .stSelectbox [data-baseweb="select"] { color: #F4F4F5; background: #151A23; border-color: #262B3D; border-radius: 9px; }

        /* Tables and charts */
        [data-testid="stDataFrame"] { overflow: hidden; border: 1px solid #262B3D; border-radius: 12px; }
        [data-testid="stVegaLiteChart"] { padding: 12px; background: #151A23; border: 1px solid #262B3D; border-radius: 12px; }

        .invoice-preview { padding: 12px; background: #151A23; border: 1px solid #262B3D; border-radius: 12px; }
        .invoice-preview iframe { width: 100%; height: 700px; border: none; border-radius: 8px; }

        details { background: #151A23 !important; border: 1px solid #262B3D !important; border-radius: 10px !important; }

        /* Generic card, reused for every "callout" block instead of ad-hoc st.info/emoji headers */
        .ia-card {
            background: #151A23;
            border: 1px solid #262B3D;
            border-radius: 12px;
            padding: 18px 20px;
            margin-bottom: 12px;
        }
        .ia-card-title { font-size: 0.95rem; font-weight: 700; color: #F4F4F5; margin-bottom: 6px; }
        .ia-card-body { color: #9CA3AF; font-size: 0.92rem; line-height: 1.6; margin: 0; }

        .ia-status {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 999px;
            margin-bottom: 8px;
        }
        .ia-status .dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
        .ia-status.success { background: rgba(52, 211, 153, 0.14); color: #34D399; }
        .ia-status.success .dot { background: #34D399; }
        .ia-status.warning { background: rgba(251, 191, 36, 0.14); color: #FBBF24; }
        .ia-status.warning .dot { background: #FBBF24; }
        .ia-status.danger { background: rgba(251, 113, 133, 0.14); color: #FB7185; }
        .ia-status.danger .dot { background: #FB7185; }

        /* Ring metric card — a small conic-gradient donut next to a label,
        used where a percentage genuinely means something (e.g. valid rate). */
        .ia-ring-card {
            display: flex;
            align-items: center;
            gap: 18px;
            background: #151A23;
            border: 1px solid #262B3D;
            border-radius: 12px;
            padding: 16px 18px;
            min-height: 100px;
        }
        .ia-ring {
            position: relative;
            width: 64px;
            height: 64px;
            border-radius: 50%;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .ia-ring::after {
            content: "";
            position: absolute;
            width: 46px;
            height: 46px;
            border-radius: 50%;
            background: #151A23;
        }
        .ia-ring-value { position: relative; z-index: 1; font-weight: 800; color: #F4F4F5; font-size: 0.82rem; }
        .ia-ring-label { color: #9CA3AF; font-size: 0.82rem; margin-bottom: 2px; }
        .ia-ring-sublabel { color: #F4F4F5; font-size: 1.15rem; font-weight: 750; }

        /* Gradient hero banner, used for the executive report header */
        .exec-report-header {
            background: linear-gradient(135deg, #D66C13 0%, #F48325 55%, #0154A4 130%);
            border-radius: 14px;
            padding: 26px 28px;
            margin-bottom: 8px;
        }
        .exec-report-header .kicker { color: rgba(255, 255, 255, 0.75); font-size: 0.72rem; font-weight: 750; letter-spacing: 0.1em; text-transform: uppercase; }
        .exec-report-header h1 { font-size: 1.5rem !important; margin: 6px 0 2px; color: #FFFFFF !important; }
        .exec-report-header .meta { color: rgba(255, 255, 255, 0.85); font-size: 0.88rem; }

        .exec-summary p { margin: 0 0 16px; line-height: 1.75; font-size: 16px; color: #E4E4E7; text-align: left; }
        .exec-summary p:last-child { margin-bottom: 0; }

        @media (max-width: 800px) {
            .ia-brand-mark { width: 42px; height: 42px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    """Render the logo, app name, and organization at the top of the sidebar."""

    logo_html = ""

    if LOGO_PATH.exists():
        import base64

        logo_data = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
        logo_html = (
            '<div class="ia-brand-mark">'
            f'<img src="data:image/png;base64,{logo_data}" alt="{ORGANIZATION_NAME} logo">'
            "</div>"
        )
    else:
        logo_html = '<div class="ia-brand-mark ia-brand-mark-fallback">AP</div>'

    # Single line on purpose — see the note on render_card(): a blank line
    # partway through a <div>-based HTML block ends Markdown's HTML parsing
    # early, and this function has no guarantee that every piece is non-empty.
    brand_html = (
        '<div class="ia-brand">'
        f"{logo_html}"
        "<div>"
        f'<div class="ia-brand-name">{APP_NAME}</div>'
        f'<div class="ia-brand-tagline">{ORGANIZATION_NAME}</div>'
        "</div>"
        "</div>"
    )

    st.sidebar.markdown(brand_html, unsafe_allow_html=True)


def render_ring_card(label: str, value_text: str, percent: float, color: str) -> None:
    """Render a small donut-ring metric card (built with a conic-gradient, no chart library needed)."""

    percent = max(0, min(100, percent))

    ring_html = (
        f'<div class="ia-ring-card">'
        f'<div class="ia-ring" style="background: conic-gradient({color} {percent}%, #262B3D 0);">'
        f'<div class="ia-ring-value">{percent:.0f}%</div>'
        "</div>"
        "<div>"
        f'<div class="ia-ring-label">{label}</div>'
        f'<div class="ia-ring-sublabel">{value_text}</div>'
        "</div>"
        "</div>"
    )

    st.markdown(ring_html, unsafe_allow_html=True)


def render_section(label: str, title: str, description: str) -> None:
    """Render a section heading."""

    st.markdown(
        f"""
        <div class="section-label">{label}</div>
        <h2 class="section-title">{title}</h2>
        <p class="section-description">{description}</p>
        """,
        unsafe_allow_html=True,
    )


def render_card(title: str, body: str, status: str = None) -> None:
    """Render a single callout card with an optional status pill."""

    status_html = ""

    if status:
        label = {"success": "On track", "warning": "Attention", "danger": "Action needed"}[status]
        status_html = f'<span class="ia-status {status}"><span class="dot"></span>{label}</span>'

    # Single line on purpose — see the note in render_header(). Most calls to
    # this function pass no status, so status_html is "" here far more often
    # than not, and a blank line in the middle of an HTML block breaks
    # Markdown's HTML parsing and prints the raw tags instead of rendering them.
    card_html = (
        '<div class="ia-card">'
        f"{status_html}"
        f'<div class="ia-card-title">{title}</div>'
        f'<p class="ia-card-body">{body}</p>'
        "</div>"
    )

    st.markdown(card_html, unsafe_allow_html=True)


def configure_chart(chart: alt.Chart) -> alt.Chart:
    """Apply consistent dark chart styling."""

    return (
        chart.configure_view(strokeWidth=0, fill="transparent")
        .configure_axis(
            gridColor="#262B3D",
            domainColor="#363B4D",
            tickColor="#363B4D",
            labelColor="#9CA3AF",
            titleColor="#9CA3AF",
            labelFontSize=12,
            titleFontSize=12,
        )
        .configure_title(color="#F4F4F5", fontSize=16, anchor="start")
        .configure_legend(labelColor="#9CA3AF", titleColor="#9CA3AF", labelFontSize=12)
    )


DONUT_PALETTE = [PRIMARY, BLUE, AMBER, ROSE, SUCCESS]
DONUT_OTHER_COLOR = "#4B5563"


def top_n_plus_other(
    rows: List[Dict[str, Any]],
    key_field: str,
    value_field: str,
    n: int = 5,
    other_label: str = "Other",
) -> pd.DataFrame:
    """Reduce a ranked list to its top N entries plus a single 'Other' bucket.

    Keeps donut charts readable (a pie with 10+ slices is unreadable) while
    still accounting for every dollar, so the chart always represents 100%
    of the total rather than silently dropping the long tail.
    """

    top = rows[:n]
    remainder = sum(row[value_field] for row in rows[n:])

    result = [{"label": row[key_field], "value": row[value_field]} for row in top]

    if remainder > 0.005:
        result.append({"label": other_label, "value": round(remainder, 2)})

    return pd.DataFrame(result)


def render_donut_chart(
    df: pd.DataFrame,
    category_label: str = "Category",
    value_format: str = "$,.2f",
    height: int = 300,
) -> None:
    """Render an interactive donut chart from a two-column (label, value) dataframe."""

    if df.empty:
        st.info("Not enough data for this chart.")
        return

    labels = df["label"].tolist()
    colors = (DONUT_PALETTE * ((len(labels) // len(DONUT_PALETTE)) + 1))[: len(labels)]

    if "Other" in labels:
        colors[labels.index("Other")] = DONUT_OTHER_COLOR

    # Highlight the hovered slice and dim the rest — a small touch that
    # makes a donut feel interactive rather than static.
    hover = alt.selection_point(fields=["label"], on="mouseover", empty="all", nearest=True)

    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=68, outerRadius=125, cornerRadius=3, padAngle=0.012)
        .encode(
            theta=alt.Theta("value:Q", stack=True),
            color=alt.Color(
                "label:N",
                scale=alt.Scale(domain=labels, range=colors),
                legend=alt.Legend(title=None, orient="right"),
            ),
            opacity=alt.condition(hover, alt.value(1), alt.value(0.55)),
            tooltip=[
                alt.Tooltip("label:N", title=category_label),
                alt.Tooltip("value:Q", title="Amount", format=value_format),
            ],
        )
        .add_params(hover)
        .properties(height=height)
    )

    st.altair_chart(configure_chart(chart), use_container_width=True)


def monthly_area_chart(monthly: pd.DataFrame) -> alt.Chart:
    """Build the gradient-filled monthly spending area chart (shared by Insights and the Executive Report)."""

    return (
        alt.Chart(monthly)
        .mark_area(
            line={"color": PRIMARY, "strokeWidth": 3},
            point=alt.OverlayMarkDef(color=PRIMARY, size=45),
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color=PRIMARY, offset=0),
                    alt.GradientStop(color="rgba(244, 131, 37, 0)", offset=1),
                ],
                x1=1, x2=1, y1=1, y2=0,
            ),
            interpolate="monotone",
        )
        .encode(
            x=alt.X("month:N", title="Month", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("total_spend:Q", title="Total spending", axis=alt.Axis(format="$,.0f")),
            tooltip=[
                alt.Tooltip("month:N", title="Month"),
                alt.Tooltip("total_spend:Q", title="Total spending", format="$,.2f"),
            ],
        )
        .properties(height=300)
    )


def format_money(value: Any) -> str:
    """Format a value as U.S. currency."""

    if value is None:
        return "Missing"

    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def money_column(label: str) -> "st.column_config.NumberColumn":
    return st.column_config.NumberColumn(label, format="$%.2f")


# ---------------------------------------------------------------------
# Upload & review
# ---------------------------------------------------------------------


def prepare_invoice(invoice_data: Dict[str, Any], source_file: str) -> Dict[str, Any]:
    """Add validation and source information."""

    validation_result = validate_invoice(invoice_data)

    invoice_data["source_file"] = source_file
    invoice_data["validation_status"] = "Valid" if validation_result["is_valid"] else "Needs Review"
    invoice_data["validation_errors"] = "; ".join(validation_result["errors"])

    return invoice_data


def process_uploaded_file(uploaded_file: Any) -> Dict[str, Any]:
    """Process an uploaded invoice without immediately saving it."""

    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    saved_path = UPLOAD_FOLDER / uploaded_file.name
    saved_path.write_bytes(uploaded_file.getvalue())

    text = extract_text_from_file(saved_path)

    try:
        invoice_data = extract_invoice_fields_with_ai(text)
        parser_used = "AI"

    except Exception as error:
        invoice_data = extract_invoice_fields(text)
        parser_used = "Regex fallback"
        invoice_data["parser_error"] = str(error)

    try:
        invoice_data["line_items"] = extract_line_items_with_ai(text)

    except Exception:
        invoice_data["line_items"] = []

    invoice_data = prepare_invoice(invoice_data, uploaded_file.name)
    invoice_data["parser_used"] = parser_used
    invoice_data["database_result"] = "Awaiting approval"
    invoice_data["saved"] = False

    return invoice_data


def clean_text_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def clean_number_value(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def prepare_line_items(invoice: Dict[str, Any]) -> pd.DataFrame:
    """Convert extracted line items into a dataframe that can be edited."""

    items = invoice.get("line_items", [])

    if not items:
        items = [{"description": "", "quantity": 1, "unit_price": 0.0, "line_total": 0.0}]

    return pd.DataFrame(items)


def calculate_line_item_total(items: pd.DataFrame) -> float:
    if items.empty:
        return 0.0

    total = 0

    for _, row in items.iterrows():
        try:
            total += float(row["line_total"])
        except Exception:
            pass

    return round(total, 2)


def clean_line_items(items: pd.DataFrame) -> List[Dict]:
    cleaned = []

    for _, row in items.iterrows():
        if str(row["description"]).strip() == "" and float(row["line_total"] or 0) == 0:
            continue

        cleaned.append(
            {
                "description": str(row["description"]).strip(),
                "quantity": float(row["quantity"]),
                "unit_price": float(row["unit_price"]),
                "line_total": float(row["line_total"]),
            }
        )

    return cleaned


LINE_ITEM_COLUMN_CONFIG = {
    "description": st.column_config.TextColumn("Description", width="large"),
    "quantity": st.column_config.NumberColumn("Qty", format="%.2f"),
    "unit_price": money_column("Unit Price"),
    "line_total": money_column("Line Total"),
}


def render_invoice_preview(source_file: str) -> None:
    """Display the original uploaded PDF or image."""

    import base64

    file_path = UPLOAD_FOLDER / source_file

    if not file_path.exists():
        st.warning("The original uploaded file could not be found.")
        return

    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        pdf_data = base64.b64encode(file_path.read_bytes()).decode("utf-8")

        st.markdown(
            f'<div class="invoice-preview"><iframe src="data:application/pdf;base64,{pdf_data}"></iframe></div>',
            unsafe_allow_html=True,
        )

    elif suffix in {".png", ".jpg", ".jpeg"}:
        st.image(str(file_path), use_container_width=True)

    else:
        st.info("Preview is unavailable for this file type.")


def display_processed_invoice(invoice: Dict[str, Any]) -> None:
    """Display one processed invoice."""

    status = invoice.get("validation_status")

    if status == "Valid":
        st.success("Invoice passed validation.")
    else:
        st.warning("Invoice needs review.")

    details_column, money_column_, system_column = st.columns(3)

    with details_column:
        st.subheader("Invoice details")
        st.write(f"**Vendor:** {invoice.get('vendor') or 'Missing'}")
        st.write(f"**Invoice number:** {invoice.get('invoice_number') or 'Missing'}")
        st.write(f"**Invoice date:** {invoice.get('invoice_date') or 'Missing'}")
        st.write(f"**Due date:** {invoice.get('due_date') or 'Missing'}")

    with money_column_:
        st.subheader("Financials")
        st.write(f"**Subtotal:** {format_money(invoice.get('subtotal'))}")
        st.write(f"**Tax:** {format_money(invoice.get('tax'))}")
        st.write(f"**Shipping:** {format_money(invoice.get('shipping'))}")
        st.write(f"**Total due:** {format_money(invoice.get('total_due'))}")

    with system_column:
        st.subheader("Processing")
        st.write(f"**Parser:** {invoice.get('parser_used', 'Unknown')}")
        st.write(f"**Database:** {invoice.get('database_result', 'Unknown')}")
        st.write(f"**Source:** {invoice.get('source_file', 'Unknown')}")
        st.write(f"**Status:** {status}")

    if invoice.get("description"):
        st.write(f"**Description:** {invoice.get('description')}")

    if invoice.get("validation_errors"):
        st.error(invoice["validation_errors"])


def render_invoice_review_form(invoice: Dict[str, Any], invoice_index: int) -> None:
    """Show the original invoice beside editable extracted data."""

    source_file = invoice.get("source_file", "Invoice")
    parser_used = invoice.get("parser_used", "Unknown")
    form_key = f"invoice_review_{invoice_index}"

    if invoice.get("saved"):
        st.success(f"{source_file} has already been saved.")

        preview_column, data_column = st.columns([1.15, 1], gap="large")

        with preview_column:
            st.subheader("Original invoice")
            render_invoice_preview(source_file)

        with data_column:
            st.subheader("Saved information")
            display_processed_invoice(invoice)

            saved_items = invoice.get("line_items", [])

            if saved_items:
                st.markdown("#### Purchased items")
                st.dataframe(
                    pd.DataFrame(saved_items),
                    use_container_width=True,
                    hide_index=True,
                    column_config=LINE_ITEM_COLUMN_CONFIG,
                )

        return

    st.caption(
        f"Extracted using {parser_used}. Compare the original invoice with the "
        "extracted data before approving."
    )

    preview_column, review_column = st.columns([1.05, 1], gap="large")

    with preview_column:
        st.subheader("Original invoice")
        render_invoice_preview(source_file)

    with review_column:
        st.subheader("Review extracted data")

        with st.form(form_key):
            vendor = st.text_input("Vendor", value=clean_text_value(invoice.get("vendor")))
            invoice_number = st.text_input(
                "Invoice Number", value=clean_text_value(invoice.get("invoice_number"))
            )

            date_left, date_right = st.columns(2)

            with date_left:
                invoice_date = st.text_input(
                    "Invoice Date",
                    value=clean_text_value(invoice.get("invoice_date")),
                    placeholder="YYYY-MM-DD",
                )

            with date_right:
                due_date = st.text_input(
                    "Due Date",
                    value=clean_text_value(invoice.get("due_date")),
                    placeholder="YYYY-MM-DD",
                )

            money_left, money_right = st.columns(2)

            with money_left:
                subtotal = st.number_input(
                    "Subtotal", value=clean_number_value(invoice.get("subtotal")),
                    min_value=0.0, step=0.01, format="%.2f",
                )
                tax = st.number_input(
                    "Tax", value=clean_number_value(invoice.get("tax")),
                    min_value=0.0, step=0.01, format="%.2f",
                )

            with money_right:
                shipping = st.number_input(
                    "Shipping", value=clean_number_value(invoice.get("shipping")),
                    min_value=0.0, step=0.01, format="%.2f",
                )
                total_due = st.number_input(
                    "Total Due", value=clean_number_value(invoice.get("total_due")),
                    min_value=0.0, step=0.01, format="%.2f",
                )

            description = st.text_area(
                "Description", value=clean_text_value(invoice.get("description")), height=90
            )

            st.markdown("#### Purchased Items")
            st.caption("Edit, add, or delete extracted line items.")

            edited_items = st.data_editor(
                prepare_line_items(invoice),
                hide_index=True,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    **LINE_ITEM_COLUMN_CONFIG,
                    "quantity": st.column_config.NumberColumn("Qty", min_value=0, step=1),
                },
            )

            calculated_total = calculate_line_item_total(edited_items)
            st.metric("Purchased Items Total", f"${calculated_total:,.2f}")

            difference = round(total_due - calculated_total, 2)

            if abs(difference) < 0.01:
                st.success("Invoice total matches purchased items.")
            else:
                st.warning(f"Difference between invoice and item totals: ${difference:,.2f}")

            approve = st.form_submit_button(
                "Approve and Save", type="primary", use_container_width=True
            )

    if not approve:
        return

    corrected_invoice = {
        **invoice,
        "vendor": vendor.strip() or None,
        "invoice_number": invoice_number.strip() or None,
        "invoice_date": invoice_date.strip() or None,
        "due_date": due_date.strip() or None,
        "description": description.strip() or None,
        "subtotal": subtotal,
        "tax": tax,
        "shipping": shipping,
        "total_due": total_due,
        "line_items": clean_line_items(edited_items),
    }

    corrected_invoice = prepare_invoice(corrected_invoice, source_file)
    was_saved = save_invoice(DATABASE_PATH, corrected_invoice)

    corrected_invoice["saved"] = True
    corrected_invoice["parser_used"] = parser_used
    corrected_invoice["database_result"] = "Saved" if was_saved else "Duplicate skipped"

    processed = st.session_state["processed_invoices"]
    processed[invoice_index] = corrected_invoice
    st.session_state["processed_invoices"] = processed

    if was_saved:
        st.success("Invoice approved and saved.")
    else:
        st.warning("Duplicate invoice detected.")

    st.rerun()


def render_upload_page() -> None:
    """Render invoice extraction and manual approval."""

    render_section(
        "Upload",
        "Process and review invoice files",
        "Upload invoices, review the extracted fields, correct any mistakes, and approve each record.",
    )

    uploaded_files = st.file_uploader(
        "Upload invoice files",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        st.caption(f"{len(uploaded_files)} file(s) selected.")

        if st.button("Extract invoice data", type="primary", use_container_width=True):
            processed_invoices = []
            progress_bar = st.progress(0)

            for index, uploaded_file in enumerate(uploaded_files):
                with st.spinner(f"Extracting {uploaded_file.name}..."):
                    try:
                        invoice = process_uploaded_file(uploaded_file)
                        processed_invoices.append(invoice)

                    except Exception as error:
                        st.error(f"Could not process {uploaded_file.name}: {error}")

                progress_bar.progress((index + 1) / len(uploaded_files))

            st.session_state["processed_invoices"] = processed_invoices

            if processed_invoices:
                st.success(
                    f"Extracted {len(processed_invoices)} invoice(s). Review and approve them below."
                )

    processed_invoices = st.session_state.get("processed_invoices", [])

    if not processed_invoices:
        return

    st.divider()

    pending_count = sum(1 for invoice in processed_invoices if not invoice.get("saved"))
    saved_count = len(processed_invoices) - pending_count

    metric_one, metric_two = st.columns(2)
    metric_one.metric("Awaiting approval", pending_count)
    metric_two.metric("Completed", saved_count)

    st.subheader("Manual review")

    for index, invoice in enumerate(processed_invoices):
        status = (
            invoice.get("database_result")
            if invoice.get("saved")
            else invoice.get("validation_status", "Needs Review")
        )

        title = f"{invoice.get('source_file', 'Invoice')} — {status}"

        with st.expander(title, expanded=not invoice.get("saved")):
            render_invoice_review_form(invoice, index)

    if st.button("Clear completed upload session", use_container_width=True):
        st.session_state.pop("processed_invoices", None)
        st.rerun()


# ---------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------


def invoices_to_dataframe(invoices: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert invoice dictionaries to a DataFrame."""

    if not invoices:
        return pd.DataFrame()

    dataframe = pd.DataFrame(invoices)

    preferred_columns = [
        "id", "source_file", "vendor", "invoice_number", "invoice_date", "due_date",
        "description", "subtotal", "tax", "shipping", "total_due",
        "validation_status", "created_at",
    ]

    available_columns = [column for column in preferred_columns if column in dataframe.columns]

    return dataframe[available_columns]


def render_invoice_edit_form(invoice: Dict[str, Any]) -> None:
    """Editable form for correcting an already-saved invoice, mirrors the upload review form."""

    invoice_id = invoice["id"]

    with st.form(f"edit_invoice_{invoice_id}"):
        vendor = st.text_input("Vendor", value=clean_text_value(invoice.get("vendor")))
        invoice_number = st.text_input("Invoice Number", value=clean_text_value(invoice.get("invoice_number")))

        date_left, date_right = st.columns(2)

        with date_left:
            invoice_date = st.text_input(
                "Invoice Date", value=clean_text_value(invoice.get("invoice_date")), placeholder="YYYY-MM-DD"
            )

        with date_right:
            due_date = st.text_input(
                "Due Date", value=clean_text_value(invoice.get("due_date")), placeholder="YYYY-MM-DD"
            )

        money_left, money_right = st.columns(2)

        with money_left:
            subtotal = st.number_input(
                "Subtotal", value=clean_number_value(invoice.get("subtotal")), min_value=0.0, step=0.01, format="%.2f"
            )
            tax = st.number_input(
                "Tax", value=clean_number_value(invoice.get("tax")), min_value=0.0, step=0.01, format="%.2f"
            )

        with money_right:
            shipping = st.number_input(
                "Shipping", value=clean_number_value(invoice.get("shipping")), min_value=0.0, step=0.01, format="%.2f"
            )
            total_due = st.number_input(
                "Total Due", value=clean_number_value(invoice.get("total_due")), min_value=0.0, step=0.01, format="%.2f"
            )

        description = st.text_area(
            "Description", value=clean_text_value(invoice.get("description")), height=90
        )

        st.markdown("#### Purchased Items")
        st.caption("Edit, add, or delete purchased items.")

        edited_items = st.data_editor(
            prepare_line_items(invoice),
            hide_index=True,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                **LINE_ITEM_COLUMN_CONFIG,
                "quantity": st.column_config.NumberColumn("Qty", min_value=0, step=1),
            },
        )

        save_col, cancel_col = st.columns(2)

        with save_col:
            save = st.form_submit_button("Save changes", type="primary", use_container_width=True)

        with cancel_col:
            cancel = st.form_submit_button("Cancel", use_container_width=True)

    if cancel:
        st.session_state.pop("editing_invoice_id", None)
        st.rerun()

    if not save:
        return

    corrected_invoice = {
        **invoice,
        "vendor": vendor.strip() or None,
        "invoice_number": invoice_number.strip() or None,
        "invoice_date": invoice_date.strip() or None,
        "due_date": due_date.strip() or None,
        "description": description.strip() or None,
        "subtotal": subtotal,
        "tax": tax,
        "shipping": shipping,
        "total_due": total_due,
        "line_items": clean_line_items(edited_items),
    }

    corrected_invoice = prepare_invoice(corrected_invoice, invoice.get("source_file", ""))
    update_invoice(DATABASE_PATH, invoice_id, corrected_invoice)

    st.session_state.pop("editing_invoice_id", None)
    st.success("Invoice updated.")
    st.rerun()


def render_delete_confirmation(invoice: Dict[str, Any]) -> bool:
    """Render the delete confirmation card for a saved invoice.

    Returns True if the confirmation is currently showing, so the caller
    can skip rendering the rest of the invoice viewer underneath it.
    """

    invoice_id = invoice["id"]

    if st.session_state.get("pending_delete_invoice_id") != invoice_id:
        return False

    render_card(
        "Delete this invoice?",
        f"This will permanently remove {invoice.get('source_file') or 'this invoice'} "
        "and its purchased items from the database. This cannot be undone.",
        status="danger",
    )

    confirm_col, cancel_col = st.columns(2)

    with confirm_col:
        if st.button(
            "Confirm delete", type="primary", use_container_width=True, key=f"confirm_delete_{invoice_id}"
        ):
            delete_invoice(DATABASE_PATH, invoice_id)
            st.session_state.pop("pending_delete_invoice_id", None)
            st.success("Invoice deleted.")
            st.rerun()

    with cancel_col:
        if st.button("Cancel", use_container_width=True, key=f"cancel_delete_{invoice_id}"):
            st.session_state.pop("pending_delete_invoice_id", None)
            st.rerun()

    return True


def render_database_page() -> None:
    """Search and review invoices stored in SQLite."""

    render_section(
        "Database",
        "Invoice Database",
        "Search invoices, inspect purchased items, and review the original source file.",
    )

    search_term = st.text_input(
        "Search",
        placeholder="Vendor, invoice number, purchased item...",
        label_visibility="collapsed",
    )

    invoices = search_invoices(DATABASE_PATH, search_term) if search_term.strip() else get_all_invoices(DATABASE_PATH)

    if not invoices:
        st.info("No invoices found.")
        return

    dataframe = invoices_to_dataframe(invoices)
    dataframe["total_due"] = pd.to_numeric(dataframe["total_due"], errors="coerce").fillna(0)

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Invoices", len(dataframe))
    metric2.metric("Total Spending", f"${dataframe['total_due'].sum():,.2f}")
    metric3.metric("Average Invoice", f"${dataframe['total_due'].mean():,.2f}")

    st.divider()
    st.subheader("Invoice List")

    display_columns = ["vendor", "invoice_number", "invoice_date", "total_due", "validation_status"]
    available_columns = [column for column in display_columns if column in dataframe.columns]

    st.dataframe(
        dataframe[available_columns].copy(),
        hide_index=True,
        use_container_width=True,
        column_config={
            "vendor": st.column_config.TextColumn("Vendor", width="large"),
            "invoice_number": st.column_config.TextColumn("Invoice #"),
            "invoice_date": "Invoice Date",
            "total_due": money_column("Total"),
            "validation_status": "Status",
        },
    )

    st.divider()
    st.subheader("Invoice Viewer")

    options = []

    for invoice in invoices:
        vendor = invoice.get("vendor") or "Unknown"
        number = invoice.get("invoice_number") or (f"ID {invoice.get('id')}")
        total = format_money(invoice.get("total_due"))
        options.append(f"{vendor} — {number} — {total}")

    selected = st.selectbox("Choose an invoice", options)
    invoice = invoices[options.index(selected)]
    invoice_id = invoice["id"]

    # Discard any edit/delete intent left over from a previously selected
    # invoice — switching away from an in-progress edit abandons it rather
    # than letting it silently resurface if that invoice is picked again.
    if st.session_state.get("editing_invoice_id") not in (None, invoice_id):
        st.session_state.pop("editing_invoice_id", None)

    if st.session_state.get("pending_delete_invoice_id") not in (None, invoice_id):
        st.session_state.pop("pending_delete_invoice_id", None)

    if st.session_state.get("editing_invoice_id") == invoice_id:
        st.subheader("Edit Invoice")
        render_invoice_edit_form(invoice)
        return

    edit_col, delete_col = st.columns(2)

    with edit_col:
        if st.button("Edit invoice", use_container_width=True, key=f"edit_{invoice_id}"):
            st.session_state["editing_invoice_id"] = invoice_id
            st.rerun()

    with delete_col:
        if st.button("Delete invoice", use_container_width=True, key=f"delete_{invoice_id}"):
            st.session_state["pending_delete_invoice_id"] = invoice_id
            st.rerun()

    if render_delete_confirmation(invoice):
        return

    preview_col, info_col = st.columns([1.15, 1], gap="large")

    with preview_col:
        st.markdown("### Original Invoice")
        source_file = invoice.get("source_file")

        if source_file:
            render_invoice_preview(source_file)
        else:
            st.info("Original invoice unavailable.")

    with info_col:
        st.markdown("### Invoice Information")
        st.write(f"**Vendor:** {invoice.get('vendor') or 'Missing'}")
        st.write(f"**Invoice #:** {invoice.get('invoice_number') or 'Missing'}")
        st.write(f"**Invoice Date:** {invoice.get('invoice_date') or 'Missing'}")
        st.write(f"**Due Date:** {invoice.get('due_date') or 'Missing'}")
        st.write(f"**Description:** {invoice.get('description') or 'Missing'}")

        st.divider()
        st.markdown("### Financials")

        finance_left, finance_right = st.columns(2)

        with finance_left:
            st.metric("Subtotal", format_money(invoice.get("subtotal")))
            st.metric("Tax", format_money(invoice.get("tax")))

        with finance_right:
            st.metric("Shipping", format_money(invoice.get("shipping")))
            st.metric("Total Due", format_money(invoice.get("total_due")))

    st.divider()
    st.subheader("Purchased Items")

    items = get_invoice_line_items(DATABASE_PATH, invoice["id"])
    item_df = pd.DataFrame()

    if items:
        item_df = pd.DataFrame(items)
        item_columns = [c for c in ["description", "quantity", "unit_price", "line_total"] if c in item_df.columns]

        st.dataframe(
            item_df[item_columns],
            hide_index=True,
            use_container_width=True,
            column_config=LINE_ITEM_COLUMN_CONFIG,
        )
    else:
        st.info("No purchased items stored for this invoice.")

    st.divider()
    st.subheader("Invoice Summary")

    items_total = 0.0

    if not item_df.empty and "line_total" in item_df.columns:
        items_total = float(pd.to_numeric(item_df["line_total"], errors="coerce").fillna(0).sum())

    invoice_total = clean_number_value(invoice.get("total_due"))
    difference = round(invoice_total - items_total, 2)

    summary_left, summary_middle, summary_right = st.columns(3)
    summary_left.metric("Purchased Items", len(items))
    summary_middle.metric("Items Total", f"${items_total:,.2f}")
    summary_right.metric("Invoice Total", f"${invoice_total:,.2f}")

    if abs(difference) < 0.01:
        st.success("Invoice and purchased-item totals match.")
    else:
        st.warning(f"Difference between invoice and item totals: ${difference:,.2f}")

    st.divider()
    st.subheader("System Information")

    system_left, system_right = st.columns(2)

    with system_left:
        st.write(f"**Validation Status:** {invoice.get('validation_status') or 'Unknown'}")
        st.write(f"**Source File:** {invoice.get('source_file') or 'Unknown'}")

    with system_right:
        st.write(f"**Created:** {invoice.get('created_at') or 'Unknown'}")

        if invoice.get("validation_errors"):
            st.error(invoice["validation_errors"])


# ---------------------------------------------------------------------
# Insights (Overview charts + Vendor analytics + AI assistant, combined)
# ---------------------------------------------------------------------


def vendor_spend_frame(invoices: List[Dict[str, Any]], limit: int = None) -> pd.DataFrame:
    rows = analytics.vendor_summary(invoices, limit=limit)
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["vendor", "total_spend", "invoice_count"])


def monthly_spend_frame(invoices: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = analytics.monthly_spending(invoices)
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["month", "total_spend", "invoice_count"])


def item_spend_frame(invoices: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = analytics.purchased_item_summary(invoices)
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["description", "quantity", "spend", "vendor_count", "average_unit_price"]
    )


def render_ask_tab(invoices: List[Dict[str, Any]]) -> None:
    """Natural-language question box over the invoice database."""

    render_card(
        "Ask about your invoices",
        "This assistant answers questions using your invoice database — vendors, spend, and purchased products.",
    )

    suggestions = [
        "Who do we spend the most with?",
        "What are our top 5 purchased products?",
        "How much have we spent?",
        "What invoices need review?",
        "What did we spend this month?",
    ]

    cols = st.columns(2)
    selected_question = None

    for i, question in enumerate(suggestions):
        column = cols[i % 2]

        with column:
            if st.button(question, use_container_width=True, key=f"ai_{i}"):
                selected_question = question

    question = st.text_input(
        "Ask anything",
        value=selected_question or "",
        placeholder="Example: Which vendor do we spend the most with?",
    )

    if not question:
        return

    with st.spinner("Analyzing invoices..."):
        result = answer_question(DATABASE_PATH, question)

    if not result["success"]:
        st.error(result["message"])
        return

    intent = result["intent"]
    data = result["data"]

    st.divider()

    if intent == "top_vendors":
        st.subheader("Top Vendors")
        dataframe = pd.DataFrame(data)

        if dataframe.empty:
            st.info("No vendor information available.")
            return

        st.dataframe(
            dataframe, hide_index=True, use_container_width=True,
            column_config={
                "vendor": st.column_config.TextColumn("Vendor", width="large"),
                "total_spend": money_column("Total Spend"),
                "average_invoice": money_column("Average"),
                "largest_invoice": money_column("Largest"),
            },
        )

    elif intent == "top_products":
        st.subheader("Top Purchased Products")
        dataframe = pd.DataFrame(data)

        st.dataframe(
            dataframe, hide_index=True, use_container_width=True,
            column_config={
                "description": st.column_config.TextColumn("Item", width="large"),
                "spend": money_column("Spend"),
                "quantity": st.column_config.NumberColumn("Qty"),
            },
        )

    elif intent == "overall_summary":
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Invoices", data["invoice_count"])
        c2.metric("Vendors", data["vendor_count"])
        c3.metric("Total Spend", f"${data['total_spend']:,.2f}")
        c4.metric("Average Invoice", f"${data['average_invoice']:,.2f}")

    elif intent == "vendor_lookup":
        if data is None:
            st.warning("Vendor not found.")
            return

        st.subheader(data["vendor"])

        c1, c2, c3 = st.columns(3)
        c1.metric("Invoices", data["invoice_count"])
        c2.metric("Total Spend", f"${data['total_spend']:,.2f}")
        c3.metric("Largest Invoice", f"${data['largest_invoice']:,.2f}")

        st.markdown("### Top Purchased Items")
        st.dataframe(pd.DataFrame(data["top_items"]), hide_index=True, use_container_width=True)

    elif intent in ["item_search", "general_search"]:
        matches = data["matches"]

        if not matches:
            st.info("No matching invoices found.")
            return

        st.subheader(f"{len(matches)} Matching Results")
        st.dataframe(pd.DataFrame(matches), hide_index=True, use_container_width=True)

    elif intent == "review_queue":
        dataframe = pd.DataFrame(data)

        if dataframe.empty:
            st.success("No invoices currently need review.")
            return

        st.subheader("Invoices Requiring Review")
        st.dataframe(dataframe, hide_index=True, use_container_width=True)

    elif intent == "current_month_summary":
        c1, c2, c3 = st.columns(3)
        c1.metric("Month", data["month"])
        c2.metric("Invoices", data["invoice_count"])
        c3.metric("Total Spend", f"${data['total_spend']:,.2f}")

        if data["invoices"]:
            st.dataframe(pd.DataFrame(data["invoices"]), hide_index=True, use_container_width=True)

    else:
        st.json(result)


def render_charts_tab(invoices: List[Dict[str, Any]]) -> None:
    """Spending charts and breakdowns."""

    chart_option = st.selectbox(
        "Choose a report",
        [
            "Spending by vendor",
            "Monthly spending",
            "Validation status",
            "Invoice amount distribution",
            "Largest invoices",
            "Purchased item analytics",
        ],
    )

    if chart_option == "Spending by vendor":
        ranked = analytics.vendor_summary(invoices)

        if not ranked:
            st.info("No vendor data available.")
            return

        st.subheader("Vendor spend concentration")
        st.caption("Share of total spend held by each vendor — a donut fits this better than a bar chart since it's a part-of-whole question, not a ranking.")

        donut_df = top_n_plus_other(ranked, "vendor", "total_spend", n=5)
        render_donut_chart(donut_df, category_label="Vendor")

        summary = vendor_spend_frame(invoices, limit=10)

        st.dataframe(
            summary[["vendor", "total_spend"]], use_container_width=True, hide_index=True, height=230,
            column_config={
                "vendor": st.column_config.TextColumn("Vendor", width="large"),
                "total_spend": money_column("Total Spending"),
            },
        )

    elif chart_option == "Monthly spending":
        monthly = monthly_spend_frame(invoices)

        if monthly.empty:
            st.info("No usable invoice dates were found.")
            return

        st.subheader("Monthly spending")

        st.altair_chart(configure_chart(monthly_area_chart(monthly)), use_container_width=True)

        st.dataframe(
            monthly[["month", "total_spend"]], use_container_width=True, hide_index=True, height=220,
            column_config={"month": "Month", "total_spend": money_column("Total Spending")},
        )

    elif chart_option == "Validation status":
        validation = analytics.validation_summary(invoices)
        total = validation["valid"] + validation["needs_review"]

        st.subheader("Validation status")

        if total == 0:
            st.info("No invoices available.")
            return

        valid_pct = (validation["valid"] / total) * 100
        st.caption(f"{valid_pct:.0f}% of invoices passed validation on first pass.")

        status_df = pd.DataFrame(
            {"label": ["Valid", "Needs Review"], "value": [validation["valid"], validation["needs_review"]]}
        )
        status_df = status_df[status_df["value"] > 0].reset_index(drop=True)

        labels = status_df["label"].tolist()
        colors = [SUCCESS if label == "Valid" else DANGER for label in labels]

        hover = alt.selection_point(fields=["label"], on="mouseover", empty="all", nearest=True)

        chart = (
            alt.Chart(status_df)
            .mark_arc(innerRadius=68, outerRadius=125, cornerRadius=3, padAngle=0.012)
            .encode(
                theta=alt.Theta("value:Q", stack=True),
                color=alt.Color("label:N", scale=alt.Scale(domain=labels, range=colors), legend=alt.Legend(title=None, orient="right")),
                opacity=alt.condition(hover, alt.value(1), alt.value(0.55)),
                tooltip=[
                    alt.Tooltip("label:N", title="Status"),
                    alt.Tooltip("value:Q", title="Invoices", format="d"),
                ],
            )
            .add_params(hover)
            .properties(height=300)
        )

        st.altair_chart(configure_chart(chart), use_container_width=True)

    elif chart_option == "Invoice amount distribution":
        amounts = pd.DataFrame({"total_due": [analytics.safe_float(i.get("total_due")) for i in invoices]})

        st.subheader("Invoice amount distribution")
        st.caption("How many invoices fall into each dollar range — useful for spotting whether spend is dominated by a few large invoices or many small ones.")

        chart = (
            alt.Chart(amounts)
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color=PRIMARY)
            .encode(
                x=alt.X("total_due:Q", bin=alt.Bin(maxbins=12), title="Invoice amount"),
                y=alt.Y("count():Q", title="Number of invoices"),
                tooltip=[
                    alt.Tooltip("total_due:Q", bin=alt.Bin(maxbins=12), title="Range", format="$,.0f"),
                    alt.Tooltip("count():Q", title="Invoices"),
                ],
            )
            .properties(height=320)
        )

        st.altair_chart(configure_chart(chart), use_container_width=True)
        st.caption(
            f"{len(amounts)} invoices, ranging from ${amounts['total_due'].min():,.2f} "
            f"to ${amounts['total_due'].max():,.2f}."
        )

    elif chart_option == "Largest invoices":
        largest = sorted(invoices, key=lambda i: analytics.safe_float(i.get("total_due")), reverse=True)[:10]
        largest_df = pd.DataFrame(largest)[["vendor", "invoice_number", "total_due"]].copy()

        largest_df["display_name"] = largest_df.apply(
            lambda row: (
                str(row["invoice_number"])
                if pd.notna(row["invoice_number"]) and str(row["invoice_number"]) != "None"
                else str(row["vendor"])
            ),
            axis=1,
        )

        st.subheader("Largest invoices")

        chart = (
            alt.Chart(largest_df)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color=ROSE)
            .encode(
                y=alt.Y("display_name:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
                x=alt.X("total_due:Q", title="Total due", axis=alt.Axis(format="$,.0f")),
                tooltip=[
                    alt.Tooltip("vendor:N", title="Vendor"),
                    alt.Tooltip("invoice_number:N", title="Invoice number"),
                    alt.Tooltip("total_due:Q", title="Total due", format="$,.2f"),
                ],
            )
            .properties(height=max(180, min(360, len(largest_df) * 48)))
        )

        st.altair_chart(configure_chart(chart), use_container_width=True)

        st.dataframe(
            largest_df[["vendor", "invoice_number", "total_due"]], use_container_width=True, hide_index=True, height=250,
            column_config={
                "vendor": st.column_config.TextColumn("Vendor", width="large"),
                "invoice_number": st.column_config.TextColumn("Invoice Number"),
                "total_due": money_column("Total Due"),
            },
        )

    elif chart_option == "Purchased item analytics":
        item_summary = item_spend_frame(invoices)

        if item_summary.empty:
            st.info("No purchased line-item data is available yet.")
            return

        item_metric_one, item_metric_two, item_metric_three = st.columns(3)
        item_metric_one.metric("Unique items", len(item_summary))
        item_metric_two.metric("Total item spend", f"${item_summary['spend'].sum():,.2f}")
        item_metric_three.metric("Units purchased", f"{item_summary['quantity'].sum():,.2f}")

        st.divider()

        item_view = st.selectbox(
            "Choose an item report",
            ["Highest-spend items", "Most-purchased items", "Average unit price"],
            key="item_report_type",
        )

        if item_view == "Highest-spend items":
            chart_data = item_summary.head(12)
            x_field, x_title, x_format = "spend:Q", "Total spend", "$,.0f"
            st.subheader("Highest-spend purchased items")

        elif item_view == "Most-purchased items":
            chart_data = item_summary.sort_values("quantity", ascending=False).head(12)
            x_field, x_title, x_format = "quantity:Q", "Total quantity", ",.0f"
            st.subheader("Most-purchased items")

        else:
            chart_data = item_summary[item_summary["average_unit_price"] > 0].sort_values(
                "average_unit_price", ascending=False
            ).head(12)
            x_field, x_title, x_format = "average_unit_price:Q", "Average unit price", "$,.0f"
            st.subheader("Highest average unit prices")

            if chart_data.empty:
                st.info("No usable unit-price data is available.")
                return

        chart = (
            alt.Chart(chart_data)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color=AMBER)
            .encode(
                y=alt.Y("description:N", sort="-x", title=None, axis=alt.Axis(labelLimit=300)),
                x=alt.X(x_field, title=x_title, axis=alt.Axis(format=x_format)),
                tooltip=[
                    alt.Tooltip("description:N", title="Item"),
                    alt.Tooltip("spend:Q", title="Total spend", format="$,.2f"),
                    alt.Tooltip("quantity:Q", title="Quantity", format=".2f"),
                    alt.Tooltip("vendor_count:Q", title="Vendors", format="d"),
                ],
            )
            .properties(height=max(240, min(520, len(chart_data) * 44)))
        )

        st.altair_chart(configure_chart(chart), use_container_width=True)

        st.subheader("Purchased-item summary")
        st.dataframe(
            item_summary, use_container_width=True, hide_index=True, height=420,
            column_config={
                "description": st.column_config.TextColumn("Item", width="large"),
                "quantity": st.column_config.NumberColumn("Total Quantity", format="%.2f"),
                "spend": money_column("Total Spend"),
                "average_unit_price": money_column("Average Unit Price"),
                "vendor_count": st.column_config.NumberColumn("Vendors", format="%d"),
                "invoice_count": st.column_config.NumberColumn("Invoice Rows", format="%d"),
            },
        )


def render_vendors_tab(invoices: List[Dict[str, Any]]) -> None:
    """Vendor-level analytics and drill-down."""

    vendor_df = vendor_spend_frame(invoices)

    if vendor_df.empty:
        st.info("No vendor information available.")
        return

    st.subheader("Vendor Summary")
    st.dataframe(
        vendor_df, hide_index=True, use_container_width=True,
        column_config={
            "vendor": st.column_config.TextColumn("Vendor", width="large"),
            "invoice_count": st.column_config.NumberColumn("Invoices"),
            "total_spend": money_column("Total Spend"),
            "average_invoice": money_column("Average Invoice"),
            "largest_invoice": money_column("Largest Invoice"),
        },
    )

    st.divider()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Vendors", len(vendor_df))
    col2.metric("Total Spend", f"${vendor_df['total_spend'].sum():,.2f}")
    col3.metric("Invoices", int(vendor_df["invoice_count"].sum()))
    col4.metric("Average Vendor Spend", f"${vendor_df['total_spend'].mean():,.2f}")

    st.divider()
    st.subheader("Top Vendors")

    top10 = vendor_df.sort_values("total_spend", ascending=False).head(10)

    chart = (
        alt.Chart(top10)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color=BLUE)
        .encode(
            y=alt.Y("vendor:N", sort="-x", title=None),
            x=alt.X("total_spend:Q", title="Total Spend"),
            tooltip=["vendor", alt.Tooltip("total_spend:Q", format="$,.2f"), "invoice_count"],
        )
        .properties(height=400)
    )

    st.altair_chart(configure_chart(chart), use_container_width=True)

    st.divider()
    st.subheader("Vendor Details")

    vendor_name = st.selectbox("Choose a vendor", vendor_df["vendor"].tolist())
    vendor_invoices = [i for i in invoices if (i.get("vendor") or "Unknown Vendor") == vendor_name]

    if not vendor_invoices:
        return

    spend = analytics.total_spending(vendor_invoices)
    largest = analytics.safe_float(analytics.largest_invoice(vendor_invoices).get("total_due"))
    avg = analytics.average_invoice(vendor_invoices)

    c1, c2, c3 = st.columns(3)
    c1.metric("Invoices", len(vendor_invoices))
    c2.metric("Total Spend", f"${spend:,.2f}")
    c3.metric("Largest Invoice", f"${largest:,.2f}")
    st.metric("Average Invoice", f"${avg:,.2f}")

    st.subheader("Invoices")
    invoice_df = pd.DataFrame(vendor_invoices)

    st.dataframe(
        invoice_df[["invoice_number", "invoice_date", "total_due", "validation_status"]],
        hide_index=True, use_container_width=True,
        column_config={
            "invoice_number": "Invoice #", "invoice_date": "Date",
            "total_due": money_column("Total"), "validation_status": "Status",
        },
    )

    st.subheader("Purchased Items")

    item_summary = item_spend_frame(vendor_invoices)

    if not item_summary.empty:
        st.dataframe(
            item_summary[["description", "quantity", "spend"]], hide_index=True, use_container_width=True,
            column_config={
                "description": st.column_config.TextColumn("Description", width="large"),
                "quantity": st.column_config.NumberColumn("Qty"),
                "spend": money_column("Total"),
            },
        )
    else:
        st.info("No purchased items recorded for this vendor.")


def render_insights_page() -> None:
    """Combined analytics home: ask a question, browse charts, or drill into a vendor."""

    render_section(
        "Insights",
        "Spending Intelligence",
        "Ask a question, explore spending charts, or drill into a specific vendor — all in one place.",
    )

    invoices = get_all_invoices(DATABASE_PATH)

    if not invoices:
        st.info("There is no invoice data available yet.")
        return

    summary = analytics.overall_summary(invoices)
    valid_percent = (
        (summary["valid_count"] / summary["invoice_count"]) * 100 if summary["invoice_count"] else 0
    )
    valid_color = SUCCESS if valid_percent >= 80 else AMBER if valid_percent >= 50 else ROSE

    metric_one, metric_two, metric_three, metric_four = st.columns(4)

    with metric_one:
        render_ring_card("Valid rate", f"{summary['invoice_count']} invoices", valid_percent, valid_color)

    metric_two.metric("Total spending", f"${summary['total_spend']:,.2f}")
    metric_three.metric("Average invoice", f"${summary['average_invoice']:,.2f}")
    metric_four.metric("Needs review", summary["needs_review_count"])

    st.divider()

    ask_tab, charts_tab, vendors_tab = st.tabs(["Ask", "Charts", "Vendors"])

    with ask_tab:
        render_ask_tab(invoices)

    with charts_tab:
        render_charts_tab(invoices)

    with vendors_tab:
        render_vendors_tab(invoices)


# ---------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------


def render_export_page() -> None:
    """Render the Excel export page."""

    render_section(
        "Export", "Download invoice spreadsheet", "Generate a master Excel report from all stored invoices."
    )

    invoices = get_all_invoices(DATABASE_PATH)

    if not invoices:
        st.info("There are no invoices available to export.")
        return

    dataframe = invoices_to_dataframe(invoices)

    metric_one, metric_two = st.columns(2)
    metric_one.metric("Records included", len(dataframe))
    metric_two.metric("Combined value", f"${dataframe['total_due'].fillna(0).sum():,.2f}")

    st.divider()

    if st.button("Generate Excel spreadsheet", type="primary", use_container_width=True):
        export_invoices_to_excel(
            invoices,
            EXCEL_PATH,
            line_items=[
                {**item, "vendor": invoice["vendor"], "invoice_number": invoice["invoice_number"]}
                for invoice in invoices
                for item in get_invoice_line_items(DATABASE_PATH, invoice["id"])
            ],
            vendor_summary=analytics.vendor_summary(invoices),
        )

        st.success("Excel spreadsheet generated.")

    if EXCEL_PATH.exists():
        st.download_button(
            "Download Excel spreadsheet",
            data=EXCEL_PATH.read_bytes(),
            file_name="ap_accounts_payable_ledger.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


# ---------------------------------------------------------------------
# Executive report
# ---------------------------------------------------------------------


def render_executive_report_page() -> None:
    """Executive-level financial report, generated on demand."""

    render_section(
        "Executive Report",
        "AI Financial Intelligence",
        "Generate an executive-level financial report from all processed invoices.",
    )

    left, right = st.columns([3, 1])

    with left:
        render_card(
            "What this generates",
            "A complete financial analysis including vendor performance, spending trends, "
            "purchasing behavior, and executive recommendations.",
        )

    with right:
        generate = st.button("Generate Report", type="primary", use_container_width=True)

    if generate:
        with st.spinner("Analyzing invoices..."):
            st.session_state["executive_report"] = build_full_executive_report(DATABASE_PATH)

    if "executive_report" not in st.session_state:
        st.info("Generate a report to begin.")
        return

    report = st.session_state["executive_report"]
    facts = report["facts"]
    today = datetime.now().strftime("%B %d, %Y")

    exec_header_html = (
        '<div class="exec-report-header">'
        '<div class="kicker">Executive Financial Report</div>'
        f"<h1>{ORGANIZATION_NAME}</h1>"
        f'<div class="meta">Generated {today}</div>'
        "</div>"
    )

    st.markdown(exec_header_html, unsafe_allow_html=True)

    ai_report = report["report"]

    st.divider()
    st.subheader("Executive Summary")

    if not ai_report or not ai_report.strip():
        st.error("No AI summary was generated. Check your OpenAI API key.")
    else:
        # Use an HTML entity for "$" instead of a literal dollar sign so
        # Streamlit doesn't treat it as a LaTeX math delimiter.
        safe_report = ai_report.replace("$", "&#36;")

        paragraphs = [p.strip() for p in safe_report.split(chr(10)) if p.strip()]

        if len(paragraphs) <= 1:
            import re as _re

            sentences = _re.split(r"(?<=[.!?])\s+", safe_report.strip())
            paragraphs = [" ".join(sentences[i : i + 2]) for i in range(0, len(sentences), 2)]

        paragraphs_html = "".join(f"<p>{p}</p>" for p in paragraphs)

        st.markdown(
            f'<div class="ia-card"><div class="exec-summary">{paragraphs_html}</div></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    validation = facts["validation"]
    top_vendor = facts.get("top_vendor")

    valid_percent = (validation["valid"] / facts["invoice_count"]) * 100 if facts["invoice_count"] else 0
    valid_color = SUCCESS if valid_percent >= 80 else AMBER if valid_percent >= 50 else ROSE

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        render_ring_card("Valid rate", f"{facts['invoice_count']} invoices", valid_percent, valid_color)

    col2.metric("Total Spend", f"${facts['total_spend']:,.2f}")
    col3.metric("Average", f"${facts['average_invoice']:,.2f}")
    col4.metric("Needs Review", validation["needs_review"])

    if top_vendor:
        col5.metric("Top Vendor", top_vendor["vendor"])

    st.divider()
    st.subheader("Vendor Performance")

    vendor_df = pd.DataFrame(facts["top_vendors"])

    if not vendor_df.empty:
        st.caption("Share of total spend held by each vendor.")

        vendor_donut_df = top_n_plus_other(facts["top_vendors"], "vendor", "total_spend", n=5)
        render_donut_chart(vendor_donut_df, category_label="Vendor", height=280)

        vendor_table = vendor_df.rename(
            columns={"vendor": "Vendor", "total_spend": "Total Spend", "invoice_count": "Invoice Count"}
        )[["Vendor", "Total Spend", "Invoice Count"]]

        st.dataframe(vendor_table, use_container_width=True, hide_index=True)
    else:
        st.info("No vendor data available.")

    st.divider()
    st.subheader("Product Performance")

    product_df = pd.DataFrame(facts["top_products"])

    if not product_df.empty:
        st.caption("Share of total purchased-item spend held by each product.")

        # "Other" here is measured against total line-item spend, not total
        # invoice spend — see the note in executive_highlights().
        top5_item_spend = sum(row["spend"] for row in facts["top_products"])
        other_item_spend = round(facts["total_item_spend"] - top5_item_spend, 2)

        product_rows = [{"vendor": row["description"], "total_spend": row["spend"]} for row in facts["top_products"]]

        if other_item_spend > 0.005:
            product_rows.append({"vendor": "Other", "total_spend": other_item_spend})

        product_donut_df = pd.DataFrame(
            [{"label": row["vendor"], "value": row["total_spend"]} for row in product_rows]
        )
        render_donut_chart(product_donut_df, category_label="Product", height=280)

        display_products = product_df.rename(
            columns={"description": "Product", "quantity": "Quantity", "spend": "Total Spend"}
        )[["Product", "Quantity", "Total Spend"]]

        st.dataframe(display_products, use_container_width=True, hide_index=True)
    else:
        st.info("No purchased products found.")

    st.divider()
    st.subheader("Monthly Spending Trend")

    monthly_df = pd.DataFrame(facts["monthly_spending"])

    if not monthly_df.empty:
        monthly_chart = monthly_df.rename(
            columns={"month": "Month", "total_spend": "Spend", "invoice_count": "Invoices"}
        )

        chart_df = monthly_df.rename(columns={"month": "month", "total_spend": "total_spend"})
        st.altair_chart(configure_chart(monthly_area_chart(chart_df)), use_container_width=True)

        summary1, summary2, summary3 = st.columns(3)
        summary1.metric("Months", len(monthly_chart))
        summary2.metric("Average Monthly Spend", f"${monthly_chart['Spend'].mean():,.2f}")
        summary3.metric("Highest Month", monthly_chart.loc[monthly_chart["Spend"].idxmax(), "Month"])

        st.dataframe(monthly_chart, use_container_width=True, hide_index=True)
    else:
        st.info("No monthly trend available.")

    st.divider()
    st.subheader("Risk Assessment")

    risk1, risk2 = st.columns(2)

    with risk1:
        if validation["needs_review"] == 0:
            render_card("Review Queue", "No invoices currently require review.", status="success")
        elif validation["needs_review"] <= 3:
            render_card(
                "Review Queue",
                f"{validation['needs_review']} invoice(s) require manual review.",
                status="warning",
            )
        else:
            render_card(
                "Review Queue",
                f"{validation['needs_review']} invoices require immediate attention.",
                status="danger",
            )

    with risk2:
        duplicates = facts["duplicate_count"]

        if duplicates == 0:
            render_card("Duplicate Detection", "No duplicate invoices detected.", status="success")
        else:
            render_card(
                "Duplicate Detection", f"{duplicates} possible duplicate invoice(s) found.", status="danger"
            )

    risk3, risk4 = st.columns(2)

    with risk3:
        if top_vendor:
            percent = (top_vendor["total_spend"] / facts["total_spend"]) * 100
            status = "danger" if percent > 50 else "warning" if percent > 35 else "success"
            render_card(
                "Vendor Concentration",
                f"{top_vendor['vendor']} represents {percent:.1f}% of all spending.",
                status=status,
            )

    with risk4:
        avg = facts["average_invoice"]

        if avg < 500:
            render_card("Spending Health", "Average invoice size appears normal.", status="success")
        elif avg < 2500:
            render_card("Spending Health", "Average invoice value is moderately high.", status="warning")
        else:
            render_card("Spending Health", "Average invoice value is unusually high.", status="danger")

    st.divider()
    st.subheader("Recommendations")

    recommendations = []

    if validation["needs_review"]:
        recommendations.append("Review pending invoices before approving additional payments.")

    if facts["duplicate_count"]:
        recommendations.append("Investigate possible duplicate invoices before issuing payment.")

    if top_vendor:
        vendor_share = (top_vendor["total_spend"] / facts["total_spend"]) * 100

        if vendor_share > 35:
            recommendations.append(
                f"{top_vendor['vendor']} represents {vendor_share:.1f}% of spending. "
                "Consider diversifying suppliers."
            )

    if len(facts["top_products"]) > 3:
        recommendations.append("Frequently purchased products may qualify for bulk purchasing discounts.")

    recommendations.append("Continue monitoring monthly spending trends for unexpected increases.")
    recommendations.append("Generate this report regularly to identify emerging purchasing patterns.")

    for recommendation in recommendations:
        render_card("Recommendation", recommendation)


# ---------------------------------------------------------------------
# App entry point
# ---------------------------------------------------------------------


def main() -> None:
    """Run the Streamlit application."""

    st.set_page_config(
        page_title=APP_NAME,
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    apply_styles()
    initialize_database(DATABASE_PATH)

    render_sidebar_brand()

    navigation = st.sidebar.radio(
        "Navigation",
        ["Upload", "Database", "Insights", "Executive Report", "Export"],
        label_visibility="collapsed",
    )

    if navigation == "Upload":
        render_upload_page()

    elif navigation == "Database":
        render_database_page()

    elif navigation == "Insights":
        render_insights_page()

    elif navigation == "Executive Report":
        render_executive_report_page()

    elif navigation == "Export":
        render_export_page()


if __name__ == "__main__":
    main()