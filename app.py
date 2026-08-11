import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import altair as alt
import pandas as pd
import streamlit as st

from src.ai_parser import extract_invoice_fields_with_ai
from src.line_item_parser import extract_line_items_with_ai
from src.ai_assistant import answer_question
from src.executive_summary import (
    build_full_executive_report,
)

from src.database import (
    initialize_database,
    save_invoice,
    get_all_invoices,
    search_invoices,
    get_invoice_line_items,
    get_vendor_statistics,
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

        .invoice-preview {
            padding: 12px;
            background: white;
            border: 1px solid #e4e4e7;
            border-radius: 12px;
        }

        .invoice-preview iframe {
            width: 100%;
            height: 720px;
            border: none;
            border-radius: 8px;
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

        logo_data = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")

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
        "Valid" if validation_result["is_valid"] else "Needs Review"
    )

    invoice_data["validation_errors"] = "; ".join(validation_result["errors"])

    return invoice_data


def process_uploaded_file(uploaded_file: Any) -> Dict[str, Any]:
    """
    Process an uploaded invoice without immediately saving it.
    """

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

    #
    # NEW
    # Extract purchased items using GPT
    #

    try:

        invoice_data["line_items"] = extract_line_items_with_ai(text)

    except Exception:

        invoice_data["line_items"] = []

    invoice_data = prepare_invoice(
        invoice_data,
        uploaded_file.name,
    )

    invoice_data["parser_used"] = parser_used

    invoice_data["database_result"] = "Awaiting approval"

    invoice_data["saved"] = False

    return invoice_data


def clean_text_value(value: Any) -> str:
    """Convert an extracted value into editable text."""

    if value is None:
        return ""

    return str(value)


def clean_number_value(value: Any) -> float:
    """Convert an extracted value into a safe number."""

    if value in (None, ""):
        return 0.0

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def prepare_line_items(invoice: Dict[str, Any]) -> pd.DataFrame:
    """
    Convert extracted line items into a dataframe that can be
    edited inside Streamlit.
    """

    items = invoice.get("line_items", [])

    if not items:
        items = [
            {
                "description": "",
                "quantity": 1,
                "unit_price": 0.0,
                "line_total": 0.0,
            }
        ]

    return pd.DataFrame(items)


def calculate_line_item_total(items: pd.DataFrame) -> float:
    """
    Calculate total from edited line items.
    """

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
    """
    Convert dataframe back into JSON for SQLite.
    """

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
            (
                '<div class="invoice-preview">'
                f'<iframe src="data:application/pdf;base64,{pdf_data}">'
                "</iframe>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    elif suffix in {".png", ".jpg", ".jpeg"}:
        st.image(
            str(file_path),
            use_container_width=True,
        )

    else:
        st.info("Preview is unavailable for this file type.")


def render_invoice_review_form(
    invoice: Dict[str, Any],
    invoice_index: int,
) -> None:
    """Show the original invoice beside editable extracted data."""

    source_file = invoice.get("source_file", "Invoice")
    parser_used = invoice.get("parser_used", "Unknown")
    form_key = f"invoice_review_{invoice_index}"

    if invoice.get("saved"):
        st.success(f"{source_file} has already been saved.")

        preview_column, data_column = st.columns(
            [1.15, 1],
            gap="large",
        )

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
                    column_config={
                        "description": st.column_config.TextColumn(
                            "Description",
                            width="large",
                        ),
                        "quantity": st.column_config.NumberColumn(
                            "Qty",
                            format="%.2f",
                        ),
                        "unit_price": st.column_config.NumberColumn(
                            "Unit Price",
                            format="$%.2f",
                        ),
                        "line_total": st.column_config.NumberColumn(
                            "Line Total",
                            format="$%.2f",
                        ),
                    },
                )

        return

    st.caption(
        f"Extracted using {parser_used}. "
        "Compare the original invoice with the extracted data "
        "before approving."
    )

    preview_column, review_column = st.columns(
        [1.05, 1],
        gap="large",
    )

    with preview_column:
        st.subheader("Original invoice")
        render_invoice_preview(source_file)

    with review_column:
        st.subheader("Review extracted data")

        with st.form(form_key):
            vendor = st.text_input(
                "Vendor",
                value=clean_text_value(invoice.get("vendor")),
            )

            invoice_number = st.text_input(
                "Invoice Number",
                value=clean_text_value(invoice.get("invoice_number")),
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
                    "Subtotal",
                    value=clean_number_value(invoice.get("subtotal")),
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                )

                tax = st.number_input(
                    "Tax",
                    value=clean_number_value(invoice.get("tax")),
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                )

            with money_right:
                shipping = st.number_input(
                    "Shipping",
                    value=clean_number_value(invoice.get("shipping")),
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                )

                total_due = st.number_input(
                    "Total Due",
                    value=clean_number_value(invoice.get("total_due")),
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                )

            description = st.text_area(
                "Description",
                value=clean_text_value(invoice.get("description")),
                height=90,
            )

            st.markdown("#### Purchased Items")

            st.caption("Edit, add, or delete extracted line items.")

            edited_items = st.data_editor(
                prepare_line_items(invoice),
                hide_index=True,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "description": st.column_config.TextColumn(
                        "Description",
                        width="large",
                    ),
                    "quantity": st.column_config.NumberColumn(
                        "Qty",
                        min_value=0,
                        step=1,
                    ),
                    "unit_price": st.column_config.NumberColumn(
                        "Unit Price",
                        format="$%.2f",
                    ),
                    "line_total": st.column_config.NumberColumn(
                        "Line Total",
                        format="$%.2f",
                    ),
                },
            )

            calculated_total = calculate_line_item_total(edited_items)

            st.metric(
                "Purchased Items Total",
                f"${calculated_total:,.2f}",
            )

            difference = round(
                total_due - calculated_total,
                2,
            )

            if abs(difference) < 0.01:
                st.success("Invoice total matches purchased items.")
            else:
                st.warning(
                    "Difference between invoice and item totals: " f"${difference:,.2f}"
                )

            approve = st.form_submit_button(
                "Approve and Save",
                type="primary",
                use_container_width=True,
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

    corrected_invoice = prepare_invoice(
        corrected_invoice,
        source_file,
    )

    was_saved = save_invoice(
        DATABASE_PATH,
        corrected_invoice,
    )

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
        column for column in preferred_columns if column in dataframe.columns
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
            f"**Invoice number:** " f"{invoice.get('invoice_number') or 'Missing'}"
        )
        st.write(f"**Invoice date:** " f"{invoice.get('invoice_date') or 'Missing'}")
        st.write(f"**Due date:** " f"{invoice.get('due_date') or 'Missing'}")

    with money_column:
        st.subheader("Financials")
        st.write(f"**Subtotal:** {format_money(invoice.get('subtotal'))}")
        st.write(f"**Tax:** {format_money(invoice.get('tax'))}")
        st.write(f"**Shipping:** {format_money(invoice.get('shipping'))}")
        st.write(f"**Total due:** {format_money(invoice.get('total_due'))}")

    with system_column:
        st.subheader("Processing")
        st.write(f"**Parser:** {invoice.get('parser_used', 'Unknown')}")
        st.write(f"**Database:** " f"{invoice.get('database_result', 'Unknown')}")
        st.write(f"**Source:** {invoice.get('source_file', 'Unknown')}")
        st.write(f"**Status:** {status}")

    if invoice.get("description"):
        st.write(f"**Description:** {invoice.get('description')}")

    if invoice.get("validation_errors"):
        st.error(invoice["validation_errors"])


def render_upload_page() -> None:
    """Render invoice extraction and manual approval."""

    render_section(
        "Upload",
        "Process and review invoice files",
        (
            "Upload invoices, review the extracted fields, "
            "correct any mistakes, and approve each record."
        ),
    )

    uploaded_files = st.file_uploader(
        "Upload invoice files",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        st.caption(f"{len(uploaded_files)} file(s) selected.")

        if st.button(
            "Extract invoice data",
            type="primary",
            use_container_width=True,
        ):
            processed_invoices = []
            progress_bar = st.progress(0)

            for index, uploaded_file in enumerate(uploaded_files):
                with st.spinner(f"Extracting {uploaded_file.name}..."):
                    try:
                        invoice = process_uploaded_file(uploaded_file)
                        processed_invoices.append(invoice)

                    except Exception as error:
                        st.error(f"Could not process " f"{uploaded_file.name}: {error}")

                progress_bar.progress((index + 1) / len(uploaded_files))

            st.session_state["processed_invoices"] = processed_invoices

            if processed_invoices:
                st.success(
                    f"Extracted {len(processed_invoices)} invoice(s). "
                    "Review and approve them below."
                )

    processed_invoices = st.session_state.get(
        "processed_invoices",
        [],
    )

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

        with st.expander(
            title,
            expanded=not invoice.get("saved"),
        ):
            render_invoice_review_form(
                invoice,
                index,
            )

    if st.button(
        "Clear completed upload session",
        use_container_width=True,
    ):
        st.session_state.pop("processed_invoices", None)
        st.rerun()


def render_database_page() -> None:
    """Search and review invoices stored in SQLite."""

    render_section(
        "Database",
        "Invoice Database",
        (
            "Search invoices, inspect purchased items, "
            "and review the original source file."
        ),
    )

    search_term = st.text_input(
        "Search",
        placeholder="Vendor, invoice number, purchased item...",
        label_visibility="collapsed",
    )

    if search_term.strip():
        invoices = search_invoices(DATABASE_PATH, search_term)
    else:
        invoices = get_all_invoices(DATABASE_PATH)

    if not invoices:
        st.info("No invoices found.")
        return

    dataframe = invoices_to_dataframe(invoices)
    dataframe["total_due"] = pd.to_numeric(
        dataframe["total_due"],
        errors="coerce",
    ).fillna(0)

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Invoices", len(dataframe))
    metric2.metric(
        "Total Spending",
        f"${dataframe['total_due'].sum():,.2f}",
    )
    metric3.metric(
        "Average Invoice",
        f"${dataframe['total_due'].mean():,.2f}",
    )

    st.divider()
    st.subheader("Invoice List")

    display_columns = [
        "vendor",
        "invoice_number",
        "invoice_date",
        "total_due",
        "validation_status",
    ]

    available_columns = [
        column for column in display_columns if column in dataframe.columns
    ]

    st.dataframe(
        dataframe[available_columns].copy(),
        hide_index=True,
        use_container_width=True,
        column_config={
            "vendor": st.column_config.TextColumn(
                "Vendor",
                width="large",
            ),
            "invoice_number": st.column_config.TextColumn(
                "Invoice #",
            ),
            "invoice_date": "Invoice Date",
            "total_due": st.column_config.NumberColumn(
                "Total",
                format="$%.2f",
            ),
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

    selected = st.selectbox(
        "Choose an invoice",
        options,
    )
    invoice = invoices[options.index(selected)]

    preview_col, info_col = st.columns(
        [1.15, 1],
        gap="large",
    )

    with preview_col:
        st.markdown("### Original Invoice")
        source_file = invoice.get("source_file")

        if source_file:
            render_invoice_preview(source_file)
        else:
            st.info("Original invoice unavailable.")

    with info_col:
        st.markdown("### Invoice Information")
        st.write(f"**Vendor:** " f"{invoice.get('vendor') or 'Missing'}")
        st.write(f"**Invoice #:** " f"{invoice.get('invoice_number') or 'Missing'}")
        st.write(f"**Invoice Date:** " f"{invoice.get('invoice_date') or 'Missing'}")
        st.write(f"**Due Date:** " f"{invoice.get('due_date') or 'Missing'}")
        st.write(f"**Description:** " f"{invoice.get('description') or 'Missing'}")

        st.divider()
        st.markdown("### Financials")

        finance_left, finance_right = st.columns(2)

        with finance_left:
            st.metric(
                "Subtotal",
                format_money(invoice.get("subtotal")),
            )
            st.metric(
                "Tax",
                format_money(invoice.get("tax")),
            )

        with finance_right:
            st.metric(
                "Shipping",
                format_money(invoice.get("shipping")),
            )
            st.metric(
                "Total Due",
                format_money(invoice.get("total_due")),
            )

    st.divider()
    st.subheader("Purchased Items")

    items = get_invoice_line_items(
        DATABASE_PATH,
        invoice["id"],
    )

    item_df = pd.DataFrame()

    if items:
        item_df = pd.DataFrame(items)

        item_columns = [
            column
            for column in [
                "description",
                "quantity",
                "unit_price",
                "line_total",
            ]
            if column in item_df.columns
        ]

        st.dataframe(
            item_df[item_columns],
            hide_index=True,
            use_container_width=True,
            column_config={
                "description": st.column_config.TextColumn(
                    "Description",
                    width="large",
                ),
                "quantity": st.column_config.NumberColumn(
                    "Qty",
                    format="%.2f",
                ),
                "unit_price": st.column_config.NumberColumn(
                    "Unit Price",
                    format="$%.2f",
                ),
                "line_total": st.column_config.NumberColumn(
                    "Line Total",
                    format="$%.2f",
                ),
            },
        )
    else:
        st.info("No purchased items stored for this invoice.")

    st.divider()
    st.subheader("Invoice Summary")

    items_total = 0.0

    if not item_df.empty and "line_total" in item_df.columns:
        items_total = float(
            pd.to_numeric(
                item_df["line_total"],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )

    invoice_total = clean_number_value(invoice.get("total_due"))
    difference = round(
        invoice_total - items_total,
        2,
    )

    summary_left, summary_middle, summary_right = st.columns(3)

    summary_left.metric(
        "Purchased Items",
        len(items),
    )
    summary_middle.metric(
        "Items Total",
        f"${items_total:,.2f}",
    )
    summary_right.metric(
        "Invoice Total",
        f"${invoice_total:,.2f}",
    )

    if abs(difference) < 0.01:
        st.success("Invoice and purchased-item totals match.")
    else:
        st.warning("Difference between invoice and item totals: " f"${difference:,.2f}")

    st.divider()
    st.subheader("System Information")

    system_left, system_right = st.columns(2)

    with system_left:
        st.write(
            f"**Validation Status:** "
            f"{invoice.get('validation_status') or 'Unknown'}"
        )
        st.write(f"**Source File:** " f"{invoice.get('source_file') or 'Unknown'}")

    with system_right:
        st.write(f"**Created:** " f"{invoice.get('created_at') or 'Unknown'}")

        if invoice.get("validation_errors"):
            st.error(invoice["validation_errors"])


def render_vendor_page() -> None:
    """
    Display vendor spending analytics.
    """

    render_section(
        "Vendors",
        "Vendor Analytics",
        "Analyze spending patterns across vendors.",
    )

    vendors = get_vendor_statistics(DATABASE_PATH)

    if not vendors:
        st.info("No vendor information available.")
        return

    vendor_df = pd.DataFrame(vendors)

    st.subheader("Vendor Summary")

    st.dataframe(
        vendor_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "vendor": st.column_config.TextColumn(
                "Vendor",
                width="large",
            ),
            "invoice_count": st.column_config.NumberColumn("Invoices"),
            "total_spend": st.column_config.NumberColumn(
                "Total Spend",
                format="$%.2f",
            ),
            "average_invoice": st.column_config.NumberColumn(
                "Average Invoice",
                format="$%.2f",
            ),
            "largest_invoice": st.column_config.NumberColumn(
                "Largest Invoice",
                format="$%.2f",
            ),
        },
    )

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Vendors",
        len(vendor_df),
    )

    col2.metric(
        "Total Spend",
        f"${vendor_df['total_spend'].sum():,.2f}",
    )

    col3.metric(
        "Invoices",
        int(vendor_df["invoice_count"].sum()),
    )

    col4.metric(
        "Average Vendor Spend",
        f"${vendor_df['total_spend'].mean():,.2f}",
    )

    st.divider()

    st.subheader("Top Vendors")

    chart = (
        alt.Chart(
            vendor_df.sort_values(
                "total_spend",
                ascending=False,
            ).head(10)
        )
        .mark_bar(
            cornerRadiusTopRight=4,
            cornerRadiusBottomRight=4,
        )
        .encode(
            y=alt.Y(
                "vendor:N",
                sort="-x",
                title=None,
            ),
            x=alt.X(
                "total_spend:Q",
                title="Total Spend",
            ),
            tooltip=[
                "vendor",
                alt.Tooltip(
                    "total_spend:Q",
                    format="$,.2f",
                ),
                "invoice_count",
            ],
        )
        .properties(
            height=400,
        )
    )

    st.altair_chart(
        configure_chart(chart),
        use_container_width=True,
    )

    st.divider()

    st.subheader("Vendor Details")

    vendor_name = st.selectbox(
        "Choose a vendor",
        vendor_df["vendor"].tolist(),
    )

    invoices = [
        invoice
        for invoice in get_all_invoices(DATABASE_PATH)
        if invoice.get("vendor") == vendor_name
    ]

    if not invoices:
        return

    spend = sum(float(i.get("total_due") or 0) for i in invoices)

    largest = max(float(i.get("total_due") or 0) for i in invoices)

    avg = spend / len(invoices)

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Invoices",
        len(invoices),
    )

    c2.metric(
        "Total Spend",
        f"${spend:,.2f}",
    )

    c3.metric(
        "Largest Invoice",
        f"${largest:,.2f}",
    )

    st.metric(
        "Average Invoice",
        f"${avg:,.2f}",
    )

    st.subheader("Invoices")

    invoice_df = pd.DataFrame(invoices)

    st.dataframe(
        invoice_df[
            [
                "invoice_number",
                "invoice_date",
                "total_due",
                "validation_status",
            ]
        ],
        hide_index=True,
        use_container_width=True,
        column_config={
            "invoice_number": "Invoice #",
            "invoice_date": "Date",
            "total_due": st.column_config.NumberColumn(
                "Total",
                format="$%.2f",
            ),
            "validation_status": "Status",
        },
    )

    st.subheader("Purchased Items")

    all_items = []

    for invoice in invoices:

        items = get_invoice_line_items(
            DATABASE_PATH,
            invoice["id"],
        )

        all_items.extend(items)

    if all_items:

        st.dataframe(
            pd.DataFrame(all_items),
            hide_index=True,
            use_container_width=True,
            column_config={
                "description": st.column_config.TextColumn(
                    "Description",
                    width="large",
                ),
                "quantity": st.column_config.NumberColumn(
                    "Qty",
                ),
                "unit_price": st.column_config.NumberColumn(
                    "Unit Price",
                    format="$%.2f",
                ),
                "line_total": st.column_config.NumberColumn(
                    "Total",
                    format="$%.2f",
                ),
            },
        )


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
            line_items=[
                {
                    **item,
                    "vendor": invoice["vendor"],
                    "invoice_number": invoice["invoice_number"],
                }
                for invoice in invoices
                for item in get_invoice_line_items(
                    DATABASE_PATH,
                    invoice["id"],
                )
            ],
            vendor_summary=get_vendor_statistics(
                DATABASE_PATH,
            ),
        )

        st.success("Excel spreadsheet generated.")

    if EXCEL_PATH.exists():
        st.download_button(
            "Download Excel spreadsheet",
            data=EXCEL_PATH.read_bytes(),
            file_name="ap_accounts_payable_ledger.xlsx",
            mime=(
                "application/vnd.openxmlformats-" "officedocument.spreadsheetml.sheet"
            ),
            use_container_width=True,
        )


def create_vendor_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize spending by vendor."""

    summary = dataframe.copy()

    summary["vendor"] = summary["vendor"].fillna("Unknown vendor")

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

    summary["month"] = summary["parsed_date"].dt.to_period("M").astype(str)

    return (
        summary.groupby(
            "month",
            as_index=False,
        )["total_due"]
        .sum()
        .sort_values("month")
    )


def create_item_summary(
    invoices: List[Dict[str, Any]],
) -> pd.DataFrame:
    """Summarize quantity, spending, and pricing by purchased item."""

    rows = []

    for invoice in invoices:
        vendor = invoice.get("vendor") or "Unknown vendor"
        invoice_date = invoice.get("invoice_date")

        for item in invoice.get("line_items", []) or []:
            description = str(item.get("description") or "").strip()

            if not description:
                continue

            rows.append(
                {
                    "description": description,
                    "vendor": vendor,
                    "invoice_date": invoice_date,
                    "quantity": clean_number_value(item.get("quantity")),
                    "unit_price": clean_number_value(item.get("unit_price")),
                    "line_total": clean_number_value(item.get("line_total")),
                }
            )

    if not rows:
        return pd.DataFrame()

    item_dataframe = pd.DataFrame(rows)

    summary = (
        item_dataframe.groupby(
            "description",
            as_index=False,
        )
        .agg(
            total_quantity=("quantity", "sum"),
            total_spend=("line_total", "sum"),
            average_unit_price=("unit_price", "mean"),
            vendor_count=("vendor", "nunique"),
            invoice_count=("invoice_date", "count"),
        )
        .sort_values(
            "total_spend",
            ascending=False,
        )
    )

    return summary


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

    valid_count = dataframe["validation_status"].fillna("").eq("Valid").sum()

    review_count = len(dataframe) - valid_count

    metric_one, metric_two, metric_three, metric_four = st.columns(4)

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
            "Purchased item analytics",
        ],
    )

    if chart_option == "Spending by vendor":
        vendor_summary = create_vendor_summary(dataframe).head(10)

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
        monthly_summary = create_monthly_summary(dataframe)

        if monthly_summary.empty:
            st.info("No usable invoice dates were found.")
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

    elif chart_option == "Purchased item analytics":
        item_summary = create_item_summary(invoices)

        if item_summary.empty:
            st.info("No purchased line-item data is available yet.")
            return

        total_item_spend = item_summary["total_spend"].sum()
        total_quantity = item_summary["total_quantity"].sum()
        unique_items = len(item_summary)

        item_metric_one, item_metric_two, item_metric_three = st.columns(3)

        item_metric_one.metric(
            "Unique items",
            unique_items,
        )

        item_metric_two.metric(
            "Total item spend",
            f"${total_item_spend:,.2f}",
        )

        item_metric_three.metric(
            "Units purchased",
            f"{total_quantity:,.2f}",
        )

        st.divider()

        item_view = st.selectbox(
            "Choose an item report",
            [
                "Highest-spend items",
                "Most-purchased items",
                "Average unit price",
            ],
            key="item_report_type",
        )

        if item_view == "Highest-spend items":
            chart_data = item_summary.head(12)

            st.subheader("Highest-spend purchased items")

            chart = (
                alt.Chart(chart_data)
                .mark_bar(
                    cornerRadiusTopRight=4,
                    cornerRadiusBottomRight=4,
                )
                .encode(
                    y=alt.Y(
                        "description:N",
                        sort="-x",
                        title=None,
                        axis=alt.Axis(
                            labelLimit=300,
                        ),
                    ),
                    x=alt.X(
                        "total_spend:Q",
                        title="Total spend",
                        axis=alt.Axis(
                            format="$,.0f",
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "description:N",
                            title="Item",
                        ),
                        alt.Tooltip(
                            "total_spend:Q",
                            title="Total spend",
                            format="$,.2f",
                        ),
                        alt.Tooltip(
                            "total_quantity:Q",
                            title="Quantity",
                            format=".2f",
                        ),
                        alt.Tooltip(
                            "vendor_count:Q",
                            title="Vendors",
                            format="d",
                        ),
                    ],
                )
                .properties(
                    height=max(
                        240,
                        min(520, len(chart_data) * 44),
                    )
                )
            )

        elif item_view == "Most-purchased items":
            chart_data = item_summary.sort_values(
                "total_quantity",
                ascending=False,
            ).head(12)

            st.subheader("Most-purchased items")

            chart = (
                alt.Chart(chart_data)
                .mark_bar(
                    cornerRadiusTopRight=4,
                    cornerRadiusBottomRight=4,
                )
                .encode(
                    y=alt.Y(
                        "description:N",
                        sort="-x",
                        title=None,
                        axis=alt.Axis(
                            labelLimit=300,
                        ),
                    ),
                    x=alt.X(
                        "total_quantity:Q",
                        title="Total quantity",
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "description:N",
                            title="Item",
                        ),
                        alt.Tooltip(
                            "total_quantity:Q",
                            title="Quantity",
                            format=".2f",
                        ),
                        alt.Tooltip(
                            "total_spend:Q",
                            title="Total spend",
                            format="$,.2f",
                        ),
                    ],
                )
                .properties(
                    height=max(
                        240,
                        min(520, len(chart_data) * 44),
                    )
                )
            )

        else:
            chart_data = (
                item_summary[item_summary["average_unit_price"] > 0]
                .sort_values(
                    "average_unit_price",
                    ascending=False,
                )
                .head(12)
            )

            if chart_data.empty:
                st.info("No usable unit-price data is available.")
                return

            st.subheader("Highest average unit prices")

            chart = (
                alt.Chart(chart_data)
                .mark_bar(
                    cornerRadiusTopRight=4,
                    cornerRadiusBottomRight=4,
                )
                .encode(
                    y=alt.Y(
                        "description:N",
                        sort="-x",
                        title=None,
                        axis=alt.Axis(
                            labelLimit=300,
                        ),
                    ),
                    x=alt.X(
                        "average_unit_price:Q",
                        title="Average unit price",
                        axis=alt.Axis(
                            format="$,.0f",
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "description:N",
                            title="Item",
                        ),
                        alt.Tooltip(
                            "average_unit_price:Q",
                            title="Average price",
                            format="$,.2f",
                        ),
                        alt.Tooltip(
                            "vendor_count:Q",
                            title="Vendors",
                            format="d",
                        ),
                    ],
                )
                .properties(
                    height=max(
                        240,
                        min(520, len(chart_data) * 44),
                    )
                )
            )

        st.altair_chart(
            configure_chart(chart),
            use_container_width=True,
        )

        st.subheader("Purchased-item summary")

        st.dataframe(
            item_summary,
            use_container_width=True,
            hide_index=True,
            height=420,
            column_config={
                "description": st.column_config.TextColumn(
                    "Item",
                    width="large",
                ),
                "total_quantity": st.column_config.NumberColumn(
                    "Total Quantity",
                    format="%.2f",
                ),
                "total_spend": st.column_config.NumberColumn(
                    "Total Spend",
                    format="$%.2f",
                ),
                "average_unit_price": (
                    st.column_config.NumberColumn(
                        "Average Unit Price",
                        format="$%.2f",
                    )
                ),
                "vendor_count": st.column_config.NumberColumn(
                    "Vendors",
                    format="%d",
                ),
                "invoice_count": st.column_config.NumberColumn(
                    "Invoice Rows",
                    format="%d",
                ),
            },
        )


def render_ai_assistant_page() -> None:
    """
    AI assistant for asking questions about invoices.
    """

    render_section(
        "AI Assistant",
        "Financial Intelligence",
        ("Ask questions about vendors, invoices, spending, " "and purchased products."),
    )

    st.info("This assistant answers questions using your invoice database.")

    st.markdown("### Suggested Questions")

    suggestions = [
        "Who do we spend the most with?",
        "What are our top 5 purchased products?",
        "How much have we spent?",
        "Tell me about Staples",
        "Show invoices containing printer ink",
        "What invoices need review?",
        "What did we spend this month?",
    ]

    cols = st.columns(2)

    selected_question = None

    for i, question in enumerate(suggestions):

        column = cols[i % 2]

        with column:
            if st.button(
                question,
                use_container_width=True,
                key=f"ai_{i}",
            ):
                selected_question = question

    question = st.text_input(
        "Ask anything",
        value=selected_question or "",
        placeholder="Example: Which vendor do we spend the most with?",
    )

    if not question:
        return

    with st.spinner("Analyzing invoices..."):

        result = answer_question(
            DATABASE_PATH,
            question,
        )

    if not result["success"]:
        st.error(result["message"])
        return

    intent = result["intent"]
    data = result["data"]

    st.divider()

    #
    # Top Vendors
    #

    if intent == "top_vendors":

        st.subheader("Top Vendors")

        dataframe = pd.DataFrame(data)

        if dataframe.empty:
            st.info("No vendor information available.")
            return

        st.dataframe(
            dataframe,
            hide_index=True,
            use_container_width=True,
            column_config={
                "vendor": st.column_config.TextColumn(
                    "Vendor",
                    width="large",
                ),
                "total_spend": st.column_config.NumberColumn(
                    "Total Spend",
                    format="$%.2f",
                ),
                "average_invoice": st.column_config.NumberColumn(
                    "Average",
                    format="$%.2f",
                ),
                "largest_invoice": st.column_config.NumberColumn(
                    "Largest",
                    format="$%.2f",
                ),
            },
        )

    #
    # Products
    #

    elif intent == "top_products":

        st.subheader("Top Purchased Products")

        dataframe = pd.DataFrame(data)

        st.dataframe(
            dataframe,
            hide_index=True,
            use_container_width=True,
            column_config={
                "description": st.column_config.TextColumn(
                    "Item",
                    width="large",
                ),
                "total_spend": st.column_config.NumberColumn(
                    "Spend",
                    format="$%.2f",
                ),
                "total_quantity": st.column_config.NumberColumn(
                    "Qty",
                ),
            },
        )

    #
    # Overall summary
    #

    elif intent == "overall_summary":

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Invoices",
            data["invoice_count"],
        )

        c2.metric(
            "Vendors",
            data["vendor_count"],
        )

        c3.metric(
            "Total Spend",
            f"${data['total_spend']:,.2f}",
        )

        c4.metric(
            "Average Invoice",
            f"${data['average_invoice']:,.2f}",
        )

    #
    # Vendor lookup
    #

    elif intent == "vendor_lookup":

        if data is None:
            st.warning("Vendor not found.")
            return

        st.subheader(data["vendor"])

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Invoices",
            data["invoice_count"],
        )

        c2.metric(
            "Total Spend",
            f"${data['total_spend']:,.2f}",
        )

        c3.metric(
            "Largest Invoice",
            f"${data['largest_invoice']:,.2f}",
        )

        st.markdown("### Top Purchased Items")

        st.dataframe(
            pd.DataFrame(data["top_items"]),
            hide_index=True,
            use_container_width=True,
        )

    #
    # Search results
    #

    elif intent in [
        "item_search",
        "general_search",
    ]:

        matches = data["matches"]

        if not matches:
            st.info("No matching invoices found.")
            return

        st.subheader(f"{len(matches)} Matching Results")

        st.dataframe(
            pd.DataFrame(matches),
            hide_index=True,
            use_container_width=True,
        )

    #
    # Needs review
    #

    elif intent == "review_queue":

        dataframe = pd.DataFrame(data)

        if dataframe.empty:
            st.success("No invoices currently need review.")
            return

        st.subheader("Invoices Requiring Review")

        st.dataframe(
            dataframe,
            hide_index=True,
            use_container_width=True,
        )

    #
    # Monthly summary
    #

    elif intent == "current_month_summary":

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Month",
            data["month"],
        )

        c2.metric(
            "Invoices",
            data["invoice_count"],
        )

        c3.metric(
            "Total Spend",
            f"${data['total_spend']:,.2f}",
        )

        if data["invoices"]:
            st.dataframe(
                pd.DataFrame(data["invoices"]),
                hide_index=True,
                use_container_width=True,
            )

    else:

        st.json(result)


def render_executive_report_page() -> None:
    """
    Professional Executive Report Dashboard
    """

    render_section(
        "Executive Report",
        "AI Financial Intelligence",
        (
            "Automatically generate an executive-level financial report "
            "from all processed invoices."
        ),
    )

    st.markdown("# 📋 Executive Financial Report")

    st.caption("AI-generated insights powered by your invoice database.")

    left, right = st.columns([3, 1])

    with left:

        st.info(
            "Generate a complete financial analysis including "
            "vendor performance, spending trends, purchasing "
            "behavior and executive recommendations."
        )

    with right:

        generate = st.button(
            "🚀 Generate Report",
            type="primary",
            use_container_width=True,
        )

    if generate:

        with st.spinner("Analyzing invoices..."):

            report = build_full_executive_report(DATABASE_PATH)

            st.session_state["executive_report"] = report

    if "executive_report" not in st.session_state:

        st.warning("Generate a report to begin.")

        return

    report = st.session_state["executive_report"]

    facts = report["facts"]
    today = datetime.now().strftime("%B %d, %Y")

    st.markdown(f"""
# 📋 Executive Financial Report

**Lehigh Valley Phantoms**

Generated: **{today}**

---
""")

    ai_report = report["report"]

    st.divider()

    ####################################################
    # Executive Summary
    ####################################################
    st.subheader("🧠 Executive Summary")

    if not ai_report or not ai_report.strip():
        st.error("No AI summary was generated.\n\n" "Check your OpenAI API key.")
    else:
        # Use an HTML entity for "$" instead of a literal dollar sign so
        # Streamlit doesn't treat it as a LaTeX math delimiter. A backslash
        # escape doesn't work here since this text renders as raw HTML.
        safe_report = ai_report.replace("$", "&#36;")

        # Split into paragraphs. If the report came back as one giant
        # block, break it into sentence groups so it isn't a wall of text.
        paragraphs = [p.strip() for p in safe_report.split(chr(10)) if p.strip()]
        if len(paragraphs) <= 1:
            sentences = re.split(r"(?<=[.!?])\s+", safe_report.strip())
            paragraphs = [
                " ".join(sentences[i : i + 2]) for i in range(0, len(sentences), 2)
            ]

        paragraphs_html = "".join(f"<p>{p}</p>" for p in paragraphs)

        st.markdown(
            f"""
<div style="
max-width:760px;
margin:0 auto;
background:#ffffff;
padding:28px 32px;
border-radius:14px;
border:1px solid #d9d9d9;
box-shadow:0px 2px 8px rgba(0,0,0,.08);
">
<style>
.exec-summary p {{
    margin:0 0 16px;
    line-height:1.75;
    font-size:16px;
    color:#27272a;
    text-align:left;
}}
.exec-summary p:last-child {{
    margin-bottom:0;
}}
</style>
<div class="exec-summary">
{paragraphs_html}
</div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.divider()

    ####################################################
    # KPI Dashboard
    ####################################################

    validation = facts["validation"]

    top_vendor = facts.get("top_vendor")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Invoices",
        facts["invoice_count"],
    )

    col2.metric(
        "Total Spend",
        f"${facts['total_spend']:,.2f}",
    )

    col3.metric(
        "Average",
        f"${facts['average_invoice']:,.2f}",
    )

    col4.metric(
        "Needs Review",
        validation["needs_review"],
    )

    if top_vendor:

        col5.metric(
            "Top Vendor",
            top_vendor["vendor"],
        )

    st.divider()

    ####################################################
    # Vendor Performance
    ####################################################

    st.subheader("🏢 Vendor Performance")

    vendor_df = pd.DataFrame(facts["top_vendors"])

    if not vendor_df.empty:

        left, right = st.columns([2, 1])

        with left:

            st.bar_chart(vendor_df.set_index("vendor")["total_spend"])

        with right:

            st.markdown("### Top Vendors")

            for _, row in vendor_df.head(5).iterrows():

                spend = (row["total_spend"] / facts["total_spend"]) * 100

                st.metric(
                    row["vendor"],
                    f"${row['total_spend']:,.2f}",
                    f"{spend:.1f}% of spend",
                )

        vendor_table = vendor_df.copy()

        vendor_table.columns = [
            "Vendor",
            "Total Spend",
            "Invoice Count",
        ]

        st.dataframe(
            vendor_table,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info("No vendor data available.")

    st.divider()

    ####################################################
    # Product Performance
    ####################################################

    st.subheader("📦 Product Performance")

    product_df = pd.DataFrame(facts["top_products"])

    if not product_df.empty:

        left, right = st.columns([2, 1])

        with left:

            st.bar_chart(product_df.set_index("description")["spend"])

        with right:

            st.markdown("### Highest Spend Items")

            for _, row in product_df.head(5).iterrows():

                st.metric(
                    row["description"],
                    f"${row['spend']:,.2f}",
                    f"{row['quantity']:.0f} purchased",
                )

        display_products = product_df.copy()

        display_products.columns = [
            "Product",
            "Quantity",
            "Total Spend",
        ]

        st.dataframe(
            display_products,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info("No purchased products found.")

    st.divider()

    ####################################################
    # Monthly Spending
    ####################################################

    st.subheader("📈 Monthly Spending Trend")

    monthly_df = pd.DataFrame(facts["monthly_spending"])

    if not monthly_df.empty:

        monthly_chart = monthly_df.rename(
            columns={
                "month": "Month",
                "total_spend": "Spend",
                "invoice_count": "Invoices",
            }
        )

        st.line_chart(monthly_chart.set_index("Month")["Spend"])

        summary1, summary2, summary3 = st.columns(3)

        summary1.metric(
            "Months",
            len(monthly_chart),
        )

        summary2.metric(
            "Average Monthly Spend",
            f"${monthly_chart['Spend'].mean():,.2f}",
        )

        summary3.metric(
            "Highest Month",
            monthly_chart.loc[
                monthly_chart["Spend"].idxmax(),
                "Month",
            ],
        )

        st.dataframe(
            monthly_chart,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info("No monthly trend available.")

    st.divider()

    ####################################################
    # AI Risk Assessment
    ####################################################

    st.subheader("⚠ AI Risk Assessment")

    risk1, risk2 = st.columns(2)

    with risk1:

        with st.container(border=True):

            st.markdown("### 📋 Review Queue")

            if validation["needs_review"] == 0:

                st.success("No invoices currently require review.")

            elif validation["needs_review"] <= 3:

                st.warning(
                    f"{validation['needs_review']} invoice(s) require manual review."
                )

            else:

                st.error(
                    f"{validation['needs_review']} invoices require immediate attention."
                )

    with risk2:

        with st.container(border=True):

            st.markdown("### 🔍 Duplicate Detection")

            duplicates = facts["duplicate_count"]

            if duplicates == 0:

                st.success("No duplicate invoices detected.")

            else:

                st.error(f"{duplicates} possible duplicate invoice(s) found.")

    st.write("")

    risk3, risk4 = st.columns(2)

    with risk3:

        with st.container(border=True):

            st.markdown("### 🏢 Vendor Concentration")

            if top_vendor:

                percent = (top_vendor["total_spend"] / facts["total_spend"]) * 100

                st.metric(
                    "Largest Vendor",
                    top_vendor["vendor"],
                )

                st.progress(min(percent / 100, 1.0))

                st.caption(f"{percent:.1f}% of all spending")

    with risk4:

        with st.container(border=True):

            st.markdown("### 💵 Spending Health")

            if facts["average_invoice"] < 500:

                st.success("Average invoice size appears normal.")

            elif facts["average_invoice"] < 2500:

                st.warning("Average invoice value is moderately high.")

            else:

                st.error("Average invoice value is unusually high.")

    st.divider()

    ####################################################
    # AI Recommendations
    ####################################################

    st.subheader("💡 AI Recommendations")

    recommendations = []

    if validation["needs_review"]:

        recommendations.append(
            ("📋 Review pending invoices before approving " "additional payments.")
        )

    if facts["duplicate_count"]:

        recommendations.append(
            ("🔍 Investigate possible duplicate invoices " "before issuing payment.")
        )

    if top_vendor:

        vendor_share = (top_vendor["total_spend"] / facts["total_spend"]) * 100

        if vendor_share > 35:

            recommendations.append(
                (
                    f"🏢 {top_vendor['vendor']} represents "
                    f"{vendor_share:.1f}% of spending. "
                    "Consider diversifying suppliers."
                )
            )

    if len(facts["top_products"]) > 3:

        recommendations.append(
            (
                "📦 Frequently purchased products may qualify "
                "for bulk purchasing discounts."
            )
        )

    recommendations.append(
        ("📈 Continue monitoring monthly spending trends " "for unexpected increases.")
    )

    recommendations.append(
        (
            "🤖 Generate this report regularly to identify "
            "emerging purchasing patterns."
        )
    )

    for recommendation in recommendations:

        with st.container(border=True):

            st.markdown(recommendation)

    st.divider()

    ####################################################
    # Financial Data Tables
    ####################################################

    st.subheader("📑 Supporting Financial Data")

    tabs = st.tabs(
        [
            "Summary",
            "Vendors",
            "Products",
            "Monthly",
        ]
    )

    with tabs[0]:

        summary_df = pd.DataFrame(
            {
                "Metric": [
                    "Invoices",
                    "Total Spend",
                    "Average Invoice",
                    "Needs Review",
                    "Duplicate Risk",
                ],
                "Value": [
                    facts["invoice_count"],
                    f"${facts['total_spend']:,.2f}",
                    f"${facts['average_invoice']:,.2f}",
                    validation["needs_review"],
                    facts["duplicate_count"],
                ],
            }
        )

        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
        )

    with tabs[1]:

        st.dataframe(
            vendor_table,
            use_container_width=True,
            hide_index=True,
        )

    with tabs[2]:

        st.dataframe(
            display_products,
            use_container_width=True,
            hide_index=True,
        )

    with tabs[3]:

        st.dataframe(
            monthly_chart,
            use_container_width=True,
            hide_index=True,
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
            "Vendors",
            "Export",
            "Overview",
            "AI Assistant",
            "Executive Report",
        ],
        horizontal=True,
        label_visibility="collapsed",
    )

    if navigation == "Upload":
        render_upload_page()

    elif navigation == "Database":
        render_database_page()

    elif navigation == "Vendors":
        render_vendor_page()

    elif navigation == "Export":
        render_export_page()

    elif navigation == "Overview":
        render_overview_page()

    elif navigation == "AI Assistant":
        render_ai_assistant_page()

    elif navigation == "Executive Report":
        render_executive_report_page()


if __name__ == "__main__":
    main()