from pathlib import Path
from typing import Any, Dict, List

import altair as alt
import pandas as pd
import streamlit as st

from src.ai_parser import extract_invoice_fields_with_ai
from src.database import (
    get_all_invoices,
    initialize_database,
    save_invoice,
    search_invoices,
)
from src.excel_export import export_invoices_to_excel
from src.parser import extract_invoice_fields
from src.pdf_reader import extract_text_from_file
from src.validator import validate_invoice


DATABASE_PATH = Path("data/invoices.db")
UPLOAD_FOLDER = Path("invoices/uploads")
EXCEL_PATH = Path("excel/ap_accounts_payable_ledger.xlsx")
LOGO_PATH = Path("assets/ap_logo.png")


def apply_styles() -> None:
    """Apply simple, clean styling."""

    st.markdown(
        """
        <style>
        .stApp {
            background-color: #f7f8fa;
        }

        #MainMenu,
        footer {
            visibility: hidden;
        }

        header {
            background: transparent;
        }

        .block-container {
            max-width: 1180px;
            padding-top: 1.5rem;
            padding-bottom: 4rem;
        }

        h1,
        h2,
        h3,
        h4 {
            color: #18181b !important;
        }

        p,
        label {
            color: #52525b;
        }

        .top-header {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 8px 0 20px;
            margin-bottom: 18px;
            border-bottom: 1px solid #e4e4e7;
        }

        .top-header img {
            width: 58px;
            height: 58px;
            object-fit: contain;
        }

        .top-header-title {
            margin: 0;
            color: #18181b !important;
            font-size: 1.7rem;
            font-weight: 750;
            letter-spacing: -0.03em;
        }

        .top-header-subtitle {
            margin: 3px 0 0;
            color: #71717a;
            font-size: 0.9rem;
        }

        .section-label {
            margin-bottom: 4px;
            color: #f15a24;
            font-size: 0.72rem;
            font-weight: 750;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }

        .section-title {
            margin: 0 0 6px;
            color: #18181b !important;
            font-size: 1.8rem;
            font-weight: 750;
        }

        .section-description {
            margin-bottom: 24px;
            color: #71717a;
        }

        /* Top navigation */
        [data-testid="stRadio"] {
            width: fit-content;
            min-width: 600px;
            padding: 6px;
            margin-bottom: 30px;
            background: white;
            border: 1px solid #e4e4e7;
            border-radius: 12px;
        }

        [data-testid="stRadio"] > div {
            display: flex;
            gap: 5px;
        }

        [data-testid="stRadio"] label {
            min-width: 135px;
            padding: 9px 18px;
            border-radius: 8px;
            justify-content: center;
            color: #52525b;
            font-weight: 650;
            cursor: pointer;
        }

        [data-testid="stRadio"] label:has(input:checked) {
            background: #f15a24;
            color: white;
        }

        [data-testid="stRadio"] label > div:first-child {
            display: none;
        }

        /* Upload box */
        [data-testid="stFileUploaderDropzone"] {
            min-height: 180px;
            padding: 38px;
            background: white;
            border: 1.5px dashed #a1a1aa;
            border-radius: 14px;
        }

        [data-testid="stFileUploaderDropzone"]:hover {
            background: #fffaf7;
            border-color: #f15a24;
        }

        /* Buttons */
        .stButton > button,
        .stDownloadButton > button {
            min-height: 46px;
            border-radius: 9px;
            font-weight: 650;
        }

        .stButton > button[kind="primary"] {
            color: white;
            background: #f15a24;
            border-color: #f15a24;
        }

        .stButton > button[kind="primary"]:hover {
            background: #d94b17;
            border-color: #d94b17;
        }

        /* Metrics */
        [data-testid="stMetric"] {
            min-height: 105px;
            padding: 17px;
            background: white;
            border: 1px solid #e4e4e7;
            border-radius: 12px;
        }

        [data-testid="stMetricLabel"] {
            color: #71717a;
        }

        [data-testid="stMetricValue"] {
            color: #18181b;
            font-size: 1.65rem;
            font-weight: 750;
        }

        /* Inputs */
        .stTextInput input {
            min-height: 44px;
            color: #18181b;
            background: white;
            border: 1px solid #d4d4d8;
            border-radius: 9px;
        }

        .stSelectbox [data-baseweb="select"] {
            color: #18181b;
            background: white;
            border-color: #d4d4d8;
            border-radius: 9px;
        }

        /* Tables */
        [data-testid="stDataFrame"] {
            overflow: hidden;
            border: 1px solid #e4e4e7;
            border-radius: 12px;
        }

        /* Charts */
        [data-testid="stVegaLiteChart"] {
            padding: 12px;
            background: white;
            border: 1px solid #e4e4e7;
            border-radius: 12px;
        }

        details {
            background: white !important;
            border: 1px solid #e4e4e7 !important;
            border-radius: 10px !important;
        }

        @media (max-width: 800px) {
            [data-testid="stRadio"] {
                width: 100%;
                min-width: 0;
            }

            [data-testid="stRadio"] label {
                min-width: 0;
                padding: 8px 10px;
            }

            .top-header img {
                width: 46px;
                height: 46px;
            }

            .top-header-title {
                font-size: 1.35rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    """Render the application header."""

    logo_html = ""

    if LOGO_PATH.exists():
        import base64

        logo_data = base64.b64encode(
            LOGO_PATH.read_bytes()
        ).decode("utf-8")

        logo_html = (
            f'<img src="data:image/png;base64,{logo_data}" '
            'alt="AP Accounts Payable Ledger logo">'
        )

    st.markdown(
        f"""
        <div class="top-header">
            {logo_html}
            <div>
                <h1 class="top-header-title">
                    AP Accounts Payable Ledger
                </h1>
                <p class="top-header-subtitle">
                    AI-powered invoice processing, accounts payable management and reporting
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section(
    label: str,
    title: str,
    description: str,
) -> None:
    """Render a section heading."""

    st.markdown(
        f"""
        <div class="section-label">{label}</div>
        <h2 class="section-title">{title}</h2>
        <p class="section-description">{description}</p>
        """,
        unsafe_allow_html=True,
    )


def format_money(value: Any) -> str:
    """Format a value as U.S. currency."""

    if value is None:
        return "Missing"

    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def prepare_invoice(
    invoice_data: Dict[str, Any],
    source_file: str,
) -> Dict[str, Any]:
    """Add validation and source information."""

    validation_result = validate_invoice(invoice_data)

    invoice_data["source_file"] = source_file

    invoice_data["validation_status"] = (
        "Valid"
        if validation_result["is_valid"]
        else "Needs Review"
    )

    invoice_data["validation_errors"] = "; ".join(
        validation_result["errors"]
    )

    return invoice_data


def process_uploaded_file(
    uploaded_file: Any,
) -> Dict[str, Any]:
    """Process one uploaded invoice."""

    UPLOAD_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

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

    invoice_data = prepare_invoice(
        invoice_data,
        uploaded_file.name,
    )

    was_saved = save_invoice(
        DATABASE_PATH,
        invoice_data,
    )

    invoice_data["parser_used"] = parser_used
    invoice_data["database_result"] = (
        "Saved"
        if was_saved
        else "Duplicate skipped"
    )

    return invoice_data


def invoices_to_dataframe(
    invoices: List[Dict[str, Any]],
) -> pd.DataFrame:
    """Convert invoice dictionaries to a DataFrame."""

    if not invoices:
        return pd.DataFrame()

    dataframe = pd.DataFrame(invoices)

    preferred_columns = [
        "id",
        "source_file",
        "vendor",
        "invoice_number",
        "invoice_date",
        "due_date",
        "description",
        "subtotal",
        "tax",
        "shipping",
        "total_due",
        "validation_status",
        "created_at",
    ]

    available_columns = [
        column
        for column in preferred_columns
        if column in dataframe.columns
    ]

    return dataframe[available_columns]


def display_processed_invoice(
    invoice: Dict[str, Any],
) -> None:
    """Display one processed invoice."""

    status = invoice.get("validation_status")

    if status == "Valid":
        st.success("Invoice passed validation.")
    else:
        st.warning("Invoice needs review.")

    details_column, money_column, system_column = st.columns(3)

    with details_column:
        st.subheader("Invoice details")
        st.write(f"**Vendor:** {invoice.get('vendor') or 'Missing'}")
        st.write(
            f"**Invoice number:** "
            f"{invoice.get('invoice_number') or 'Missing'}"
        )
        st.write(
            f"**Invoice date:** "
            f"{invoice.get('invoice_date') or 'Missing'}"
        )
        st.write(
            f"**Due date:** "
            f"{invoice.get('due_date') or 'Missing'}"
        )

    with money_column:
        st.subheader("Financials")
        st.write(
            f"**Subtotal:** {format_money(invoice.get('subtotal'))}"
        )
        st.write(
            f"**Tax:** {format_money(invoice.get('tax'))}"
        )
        st.write(
            f"**Shipping:** {format_money(invoice.get('shipping'))}"
        )
        st.write(
            f"**Total due:** {format_money(invoice.get('total_due'))}"
        )

    with system_column:
        st.subheader("Processing")
        st.write(
            f"**Parser:** {invoice.get('parser_used', 'Unknown')}"
        )
        st.write(
            f"**Database:** "
            f"{invoice.get('database_result', 'Unknown')}"
        )
        st.write(
            f"**Source:** {invoice.get('source_file', 'Unknown')}"
        )
        st.write(f"**Status:** {status}")

    if invoice.get("description"):
        st.write(
            f"**Description:** {invoice.get('description')}"
        )

    if invoice.get("validation_errors"):
        st.error(invoice["validation_errors"])


def render_upload_page() -> None:
    """Render the upload page."""

    render_section(
        "Upload",
        "Process invoice files",
        (
            "Drag and drop digital PDFs, scanned PDFs, "
            "PNG images, JPGs or JPEGs."
        ),
    )

    uploaded_files = st.file_uploader(
        "Upload invoice files",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        st.caption(
            f"{len(uploaded_files)} file(s) selected."
        )

        if st.button(
            "Process invoices",
            type="primary",
            use_container_width=True,
        ):
            processed_invoices = []
            progress_bar = st.progress(0)

            for index, uploaded_file in enumerate(uploaded_files):
                with st.spinner(
                    f"Processing {uploaded_file.name}..."
                ):
                    try:
                        invoice = process_uploaded_file(
                            uploaded_file
                        )
                        processed_invoices.append(invoice)

                    except Exception as error:
                        st.error(
                            f"Could not process "
                            f"{uploaded_file.name}: {error}"
                        )

                progress_bar.progress(
                    (index + 1) / len(uploaded_files)
                )

            st.session_state["processed_invoices"] = (
                processed_invoices
            )

            if processed_invoices:
                st.success(
                    f"Processed "
                    f"{len(processed_invoices)} invoice(s)."
                )

    processed_invoices = st.session_state.get(
        "processed_invoices",
        [],
    )

    if processed_invoices:
        st.divider()
        st.subheader("Processing results")

        for invoice in processed_invoices:
            title = (
                f"{invoice.get('source_file', 'Invoice')} — "
                f"{invoice.get('validation_status', 'Unknown')}"
            )

            with st.expander(
                title,
                expanded=True,
            ):
                display_processed_invoice(invoice)


def render_database_page() -> None:
    """Render the database page."""

    render_section(
        "Database",
        "Stored invoice records",
        "Search and review invoices stored in SQLite.",
    )

    search_term = st.text_input(
        "Search records",
        placeholder=(
            "Search vendor, invoice number, or filename..."
        ),
        label_visibility="collapsed",
    )

    if search_term.strip():
        invoices = search_invoices(
            DATABASE_PATH,
            search_term,
        )
    else:
        invoices = get_all_invoices(DATABASE_PATH)

    dataframe = invoices_to_dataframe(invoices)

    if dataframe.empty:
        st.info("No invoice records found.")
        return

    dataframe["total_due"] = pd.to_numeric(
        dataframe["total_due"],
        errors="coerce",
    ).fillna(0)

    total_value = dataframe["total_due"].sum()

    valid_count = (
        dataframe["validation_status"]
        .fillna("")
        .eq("Valid")
        .sum()
    )

    metric_one, metric_two, metric_three = st.columns(3)

    metric_one.metric("Invoices", len(dataframe))
    metric_two.metric("Total value", f"${total_value:,.2f}")
    metric_three.metric("Validated", int(valid_count))

    st.divider()
    st.subheader("Invoice list")

    table_columns = [
        "vendor",
        "invoice_number",
        "invoice_date",
        "total_due",
        "validation_status",
    ]

    table_columns = [
        column
        for column in table_columns
        if column in dataframe.columns
    ]

    display_dataframe = dataframe[table_columns].copy()

    st.dataframe(
        display_dataframe,
        use_container_width=True,
        hide_index=True,
        height=min(420, 90 + (len(display_dataframe) * 38)),
        row_height=38,
        column_config={
            "vendor": st.column_config.TextColumn(
                "Vendor",
                width="large",
            ),
            "invoice_number": st.column_config.TextColumn(
                "Invoice Number",
                width="medium",
            ),
            "invoice_date": st.column_config.TextColumn(
                "Invoice Date",
                width="medium",
            ),
            "total_due": st.column_config.NumberColumn(
                "Total Due",
                format="$%.2f",
                width="small",
            ),
            "validation_status": st.column_config.TextColumn(
                "Status",
                width="medium",
            ),
        },
    )

    st.divider()
    st.subheader("Full invoice details")

    record_options = []

    for index, invoice in enumerate(invoices):
        vendor = invoice.get("vendor") or "Unknown vendor"
        invoice_number = (
            invoice.get("invoice_number")
            or f"Record {invoice.get('id', index + 1)}"
        )
        record_options.append(f"{vendor} — {invoice_number}")

    selected_label = st.selectbox(
        "Choose an invoice",
        record_options,
    )

    selected_index = record_options.index(selected_label)
    selected_invoice = invoices[selected_index]

    detail_one, detail_two, detail_three = st.columns(3)

    with detail_one:
        st.write(
            f"**Vendor:** "
            f"{selected_invoice.get('vendor') or 'Missing'}"
        )
        st.write(
            f"**Invoice number:** "
            f"{selected_invoice.get('invoice_number') or 'Missing'}"
        )
        st.write(
            f"**Invoice date:** "
            f"{selected_invoice.get('invoice_date') or 'Missing'}"
        )
        st.write(
            f"**Due date:** "
            f"{selected_invoice.get('due_date') or 'Missing'}"
        )

    with detail_two:
        st.write(
            f"**Subtotal:** "
            f"{format_money(selected_invoice.get('subtotal'))}"
        )
        st.write(
            f"**Tax:** "
            f"{format_money(selected_invoice.get('tax'))}"
        )
        st.write(
            f"**Shipping:** "
            f"{format_money(selected_invoice.get('shipping'))}"
        )
        st.write(
            f"**Total due:** "
            f"{format_money(selected_invoice.get('total_due'))}"
        )

    with detail_three:
        st.write(
            f"**Status:** "
            f"{selected_invoice.get('validation_status') or 'Unknown'}"
        )
        st.write(
            f"**Source file:** "
            f"{selected_invoice.get('source_file') or 'Unknown'}"
        )
        st.write(
            f"**Created:** "
            f"{selected_invoice.get('created_at') or 'Unknown'}"
        )

    if selected_invoice.get("description"):
        st.write(
            f"**Description:** "
            f"{selected_invoice.get('description')}"
        )

    if selected_invoice.get("validation_errors"):
        st.error(selected_invoice.get("validation_errors"))

def render_export_page() -> None:
    """Render the Excel export page."""

    render_section(
        "Export",
        "Download invoice spreadsheet",
        "Generate a master Excel report from all stored invoices.",
    )

    invoices = get_all_invoices(DATABASE_PATH)

    if not invoices:
        st.info("There are no invoices available to export.")
        return

    dataframe = invoices_to_dataframe(invoices)

    metric_one, metric_two = st.columns(2)

    metric_one.metric(
        "Records included",
        len(dataframe),
    )

    metric_two.metric(
        "Combined value",
        f"${dataframe['total_due'].fillna(0).sum():,.2f}",
    )

    st.divider()

    if st.button(
        "Generate Excel spreadsheet",
        type="primary",
        use_container_width=True,
    ):
        export_invoices_to_excel(
            invoices,
            EXCEL_PATH,
        )

        st.success("Excel spreadsheet generated.")

    if EXCEL_PATH.exists():
        st.download_button(
            "Download Excel spreadsheet",
            data=EXCEL_PATH.read_bytes(),
            file_name="ap_accounts_payable_ledger.xlsx",
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            use_container_width=True,
        )


def create_vendor_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize spending by vendor."""

    summary = dataframe.copy()

    summary["vendor"] = summary["vendor"].fillna(
        "Unknown vendor"
    )

    summary["total_due"] = pd.to_numeric(
        summary["total_due"],
        errors="coerce",
    ).fillna(0)

    return (
        summary.groupby(
            "vendor",
            as_index=False,
        )["total_due"]
        .sum()
        .sort_values(
            "total_due",
            ascending=False,
        )
    )


def create_monthly_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize spending by month."""

    summary = dataframe.copy()

    summary["parsed_date"] = pd.to_datetime(
        summary["invoice_date"],
        errors="coerce",
    )

    summary["total_due"] = pd.to_numeric(
        summary["total_due"],
        errors="coerce",
    ).fillna(0)

    summary = summary.dropna(
        subset=["parsed_date"],
    )

    if summary.empty:
        return pd.DataFrame()

    summary["month"] = (
        summary["parsed_date"]
        .dt.to_period("M")
        .astype(str)
    )

    return (
        summary.groupby(
            "month",
            as_index=False,
        )["total_due"]
        .sum()
        .sort_values("month")
    )


def configure_chart(
    chart: alt.Chart,
) -> alt.Chart:
    """Apply consistent light chart styling."""

    return (
        chart.configure_view(
            strokeWidth=0,
        )
        .configure_axis(
            gridColor="#e4e4e7",
            domainColor="#a1a1aa",
            tickColor="#a1a1aa",
            labelColor="#3f3f46",
            titleColor="#3f3f46",
            labelFontSize=12,
            titleFontSize=12,
        )
        .configure_title(
            color="#18181b",
            fontSize=16,
            anchor="start",
        )
    )


def render_overview_page() -> None:
    """Render analytics and charts."""

    render_section(
        "Overview",
        "Invoice data overview",
        "Review spending, validation status, and invoice trends.",
    )

    invoices = get_all_invoices(DATABASE_PATH)
    dataframe = invoices_to_dataframe(invoices)

    if dataframe.empty:
        st.info("There is no invoice data available.")
        return

    dataframe["total_due"] = pd.to_numeric(
        dataframe["total_due"],
        errors="coerce",
    ).fillna(0)

    total_value = dataframe["total_due"].sum()
    average_value = dataframe["total_due"].mean()

    valid_count = (
        dataframe["validation_status"]
        .fillna("")
        .eq("Valid")
        .sum()
    )

    review_count = len(dataframe) - valid_count

    metric_one, metric_two, metric_three, metric_four = (
        st.columns(4)
    )

    metric_one.metric(
        "Invoices",
        len(dataframe),
    )

    metric_two.metric(
        "Total spending",
        f"${total_value:,.2f}",
    )

    metric_three.metric(
        "Average invoice",
        f"${average_value:,.2f}",
    )

    metric_four.metric(
        "Needs review",
        int(review_count),
    )

    st.divider()

    chart_option = st.selectbox(
        "Choose a report",
        [
            "Spending by vendor",
            "Monthly spending",
            "Validation status",
            "Largest invoices",
        ],
    )

    if chart_option == "Spending by vendor":
        vendor_summary = create_vendor_summary(
            dataframe
        ).head(10)

        st.subheader("Top vendors by spending")

        chart = (
            alt.Chart(vendor_summary)
            .mark_bar(
                cornerRadiusTopRight=4,
                cornerRadiusBottomRight=4,
            )
            .encode(
                y=alt.Y(
                    "vendor:N",
                    sort="-x",
                    title=None,
                    axis=alt.Axis(
                        labelLimit=260,
                    ),
                ),
                x=alt.X(
                    "total_due:Q",
                    title="Total spending",
                    axis=alt.Axis(
                        format="$,.0f",
                    ),
                ),
                tooltip=[
                    alt.Tooltip(
                        "vendor:N",
                        title="Vendor",
                    ),
                    alt.Tooltip(
                        "total_due:Q",
                        title="Total spending",
                        format="$,.2f",
                    ),
                ],
            )
            .properties(
                height=max(
                    180,
                    min(360, len(vendor_summary) * 48),
                )
            )
        )

        st.altair_chart(
            configure_chart(chart),
            use_container_width=True,
        )

        st.dataframe(
            vendor_summary,
            use_container_width=True,
            hide_index=True,
            height=230,
            column_config={
                "vendor": st.column_config.TextColumn(
                    "Vendor",
                    width="large",
                ),
                "total_due": st.column_config.NumberColumn(
                    "Total Spending",
                    format="$%.2f",
                ),
            },
        )

    elif chart_option == "Monthly spending":
        monthly_summary = create_monthly_summary(
            dataframe
        )

        if monthly_summary.empty:
            st.info(
                "No usable invoice dates were found."
            )
            return

        st.subheader("Monthly spending")

        chart = (
            alt.Chart(monthly_summary)
            .mark_line(
                point=True,
                strokeWidth=3,
            )
            .encode(
                x=alt.X(
                    "month:N",
                    title="Month",
                    axis=alt.Axis(
                        labelAngle=0,
                    ),
                ),
                y=alt.Y(
                    "total_due:Q",
                    title="Total spending",
                    axis=alt.Axis(
                        format="$,.0f",
                    ),
                ),
                tooltip=[
                    alt.Tooltip(
                        "month:N",
                        title="Month",
                    ),
                    alt.Tooltip(
                        "total_due:Q",
                        title="Total spending",
                        format="$,.2f",
                    ),
                ],
            )
            .properties(
                height=300,
            )
        )

        st.altair_chart(
            configure_chart(chart),
            use_container_width=True,
        )

        st.dataframe(
            monthly_summary,
            use_container_width=True,
            hide_index=True,
            height=220,
            column_config={
                "month": "Month",
                "total_due": st.column_config.NumberColumn(
                    "Total Spending",
                    format="$%.2f",
                ),
            },
        )

    elif chart_option == "Validation status":
        status_summary = pd.DataFrame(
            {
                "status": [
                    "Valid",
                    "Needs Review",
                ],
                "count": [
                    int(valid_count),
                    int(review_count),
                ],
            }
        )

        st.subheader("Validation status")

        chart = (
            alt.Chart(status_summary)
            .mark_bar(
                cornerRadiusTopLeft=4,
                cornerRadiusTopRight=4,
            )
            .encode(
                x=alt.X(
                    "status:N",
                    title=None,
                    axis=alt.Axis(
                        labelAngle=0,
                    ),
                ),
                y=alt.Y(
                    "count:Q",
                    title="Invoice count",
                    axis=alt.Axis(
                        tickMinStep=1,
                    ),
                ),
                tooltip=[
                    alt.Tooltip(
                        "status:N",
                        title="Status",
                    ),
                    alt.Tooltip(
                        "count:Q",
                        title="Invoices",
                        format="d",
                    ),
                ],
            )
            .properties(
                height=280,
            )
        )

        st.altair_chart(
            configure_chart(chart),
            use_container_width=True,
        )

    elif chart_option == "Largest invoices":
        largest = (
            dataframe[
                [
                    "vendor",
                    "invoice_number",
                    "total_due",
                ]
            ]
            .sort_values(
                "total_due",
                ascending=False,
            )
            .head(10)
            .copy()
        )

        largest["display_name"] = largest.apply(
            lambda row: (
                str(row["invoice_number"])
                if pd.notna(row["invoice_number"])
                and str(row["invoice_number"]) != "None"
                else str(row["vendor"])
            ),
            axis=1,
        )

        st.subheader("Largest invoices")

        chart = (
            alt.Chart(largest)
            .mark_bar(
                cornerRadiusTopRight=4,
                cornerRadiusBottomRight=4,
            )
            .encode(
                y=alt.Y(
                    "display_name:N",
                    sort="-x",
                    title=None,
                    axis=alt.Axis(
                        labelLimit=260,
                    ),
                ),
                x=alt.X(
                    "total_due:Q",
                    title="Total due",
                    axis=alt.Axis(
                        format="$,.0f",
                    ),
                ),
                tooltip=[
                    alt.Tooltip(
                        "vendor:N",
                        title="Vendor",
                    ),
                    alt.Tooltip(
                        "invoice_number:N",
                        title="Invoice number",
                    ),
                    alt.Tooltip(
                        "total_due:Q",
                        title="Total due",
                        format="$,.2f",
                    ),
                ],
            )
            .properties(
                height=max(
                    180,
                    min(360, len(largest) * 48),
                )
            )
        )

        st.altair_chart(
            configure_chart(chart),
            use_container_width=True,
        )

        st.dataframe(
            largest[
                [
                    "vendor",
                    "invoice_number",
                    "total_due",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            height=250,
            column_config={
                "vendor": st.column_config.TextColumn(
                    "Vendor",
                    width="large",
                ),
                "invoice_number": st.column_config.TextColumn(
                    "Invoice Number",
                ),
                "total_due": st.column_config.NumberColumn(
                    "Total Due",
                    format="$%.2f",
                ),
            },
        )


def main() -> None:
    """Run the Streamlit application."""

    st.set_page_config(
        page_title="AP Accounts Payable Ledger",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    apply_styles()
    initialize_database(DATABASE_PATH)

    render_header()

    navigation = st.radio(
        "Navigation",
        [
            "Upload",
            "Database",
            "Export",
            "Overview",
        ],
        horizontal=True,
        label_visibility="collapsed",
    )

    if navigation == "Upload":
        render_upload_page()

    elif navigation == "Database":
        render_database_page()

    elif navigation == "Export":
        render_export_page()

    elif navigation == "Overview":
        render_overview_page()


if __name__ == "__main__":
    main()