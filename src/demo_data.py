"""Sample invoice data for demos and fresh deployments.

Streamlit Community Cloud's filesystem resets on every redeploy and on
wake-up after the app sleeps from inactivity, so an empty database is the
normal cold-start state there — not a bug. seed_demo_data() fills that
empty state with realistic sample invoices (and matching PDFs, so the
"Original Invoice" preview has something real to show) rather than
greeting a visitor with a blank app.
"""

from pathlib import Path
from typing import Any, Dict, List

import fitz

from src.database import get_all_invoices, save_invoice
from src.validator import validate_invoice

INK = (0.10, 0.10, 0.12)
MUTED = (0.42, 0.42, 0.47)
RULE = (0.55, 0.55, 0.6)

# A minor-league hockey team's typical AP vendors: equipment, ice/arena
# maintenance, transportation, concessions, ticketing. One invoice
# (BH-90876) has an intentional subtotal/tax/total mismatch so the
# validation and review-queue features have something real to demonstrate.
DEMO_INVOICES: List[Dict[str, Any]] = [
    {
        "vendor": "Zamboni Company",
        "vendor_address": "1900 Kraft Ave SW, Grand Rapids, MI",
        "invoice_number": "ZC-45210",
        "invoice_date": "2026-03-10",
        "due_date": "2026-03-24",
        "description": "Ice resurfacer maintenance",
        "line_items": [
            {"description": "Ice resurfacer blade sharpening", "quantity": 2, "unit_price": 125.00, "line_total": 250.00},
            {"description": "Coolant fluid (drum)", "quantity": 1, "unit_price": 340.00, "line_total": 340.00},
        ],
        "subtotal": 590.00, "tax": 47.20, "shipping": 25.00, "total_due": 662.20,
    },
    {
        "vendor": "Bauer Hockey Group",
        "vendor_address": "85 Basaltic Rd, Concord, ON",
        "invoice_number": "BH-88213",
        "invoice_date": "2026-04-04",
        "due_date": "2026-04-18",
        "description": "Team equipment order",
        "line_items": [
            {"description": "Away jerseys", "quantity": 24, "unit_price": 145.00, "line_total": 3480.00},
            {"description": "Practice pucks (case)", "quantity": 10, "unit_price": 38.50, "line_total": 385.00},
            {"description": "Skate sharpening stones", "quantity": 5, "unit_price": 24.00, "line_total": 120.00},
        ],
        "subtotal": 3985.00, "tax": 318.80, "shipping": 0.00, "total_due": 4303.80,
    },
    {
        "vendor": "Aramark Concessions",
        "vendor_address": "2400 Market St, Philadelphia, PA",
        "invoice_number": "AR-33087",
        "invoice_date": "2026-04-22",
        "due_date": "2026-05-06",
        "description": "Concessions and staff catering",
        "line_items": [
            {"description": "Concession supplies - bulk", "quantity": 1, "unit_price": 1850.00, "line_total": 1850.00},
            {"description": "Catering - staff meals", "quantity": 1, "unit_price": 620.00, "line_total": 620.00},
        ],
        "subtotal": 2470.00, "tax": 197.60, "shipping": 0.00, "total_due": 2667.60,
    },
    {
        "vendor": "Ticketmaster",
        "vendor_address": "9348 Civic Center Dr, Beverly Hills, CA",
        "invoice_number": "TM-90144",
        "invoice_date": "2026-05-01",
        "due_date": "2026-05-15",
        "description": "Ticketing platform fees",
        "line_items": [
            {"description": "Ticketing platform fee - monthly", "quantity": 1, "unit_price": 1800.00, "line_total": 1800.00},
            {"description": "Payment processing fee", "quantity": 1, "unit_price": 450.00, "line_total": 450.00},
        ],
        "subtotal": 2250.00, "tax": 0.00, "shipping": 0.00, "total_due": 2250.00,
    },
    {
        "vendor": "First Student Inc",
        "vendor_address": "600 Vine St, Cincinnati, OH",
        "invoice_number": "FS-11209",
        "invoice_date": "2026-05-18",
        "due_date": "2026-06-01",
        "description": "Team charter transportation",
        "line_items": [
            {"description": "Charter bus - road trip (Hershey)", "quantity": 2, "unit_price": 650.00, "line_total": 1300.00},
            {"description": "Fuel surcharge", "quantity": 1, "unit_price": 95.00, "line_total": 95.00},
        ],
        "subtotal": 1395.00, "tax": 0.00, "shipping": 0.00, "total_due": 1395.00,
    },
    {
        "vendor": "PPL Center Facilities",
        "vendor_address": "701 Hamilton St, Allentown, PA",
        "invoice_number": "PC-77410",
        "invoice_date": "2026-06-03",
        "due_date": "2026-06-17",
        "description": "Arena maintenance",
        "line_items": [
            {"description": "HVAC maintenance - quarterly", "quantity": 1, "unit_price": 2400.00, "line_total": 2400.00},
            {"description": "Ice plant service", "quantity": 1, "unit_price": 3200.00, "line_total": 3200.00},
        ],
        "subtotal": 5600.00, "tax": 448.00, "shipping": 0.00, "total_due": 6048.00,
    },
    {
        "vendor": "Gatorade Sports Science",
        "vendor_address": "555 W Monroe St, Chicago, IL",
        "invoice_number": "GS-52290",
        "invoice_date": "2026-07-09",
        "due_date": "2026-07-23",
        "description": "Hydration and recovery supplies",
        "line_items": [
            {"description": "Hydration mix (case)", "quantity": 8, "unit_price": 42.50, "line_total": 340.00},
            {"description": "Recovery supplements", "quantity": 6, "unit_price": 58.00, "line_total": 348.00},
        ],
        "subtotal": 688.00, "tax": 55.04, "shipping": 15.00, "total_due": 758.04,
    },
    {
        "vendor": "Bauer Hockey Group",
        "vendor_address": "85 Basaltic Rd, Concord, ON",
        "invoice_number": "BH-90876",
        "invoice_date": "2026-08-05",
        "due_date": "2026-08-19",
        "description": "Home jersey and helmet order",
        "line_items": [
            {"description": "Home jerseys", "quantity": 24, "unit_price": 150.00, "line_total": 3600.00},
            {"description": "Helmets", "quantity": 12, "unit_price": 85.00, "line_total": 1020.00},
        ],
        # Intentional mismatch (should be 4,989.60) so validation and the
        # review queue have a real example to show.
        "subtotal": 4620.00, "tax": 369.60, "shipping": 0.00, "total_due": 5100.00,
    },
]


def _draw_invoice_pdf(path: Path, invoice: Dict[str, Any]) -> None:
    """Render a simple, readable one-page PDF for a demo invoice."""

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    y = 56
    page.insert_text((56, y), "INVOICE", fontsize=22, fontname="hebo", color=INK)

    y += 30
    page.insert_text((56, y), invoice["vendor"], fontsize=13, fontname="hebo", color=INK)
    y += 16
    page.insert_text((56, y), invoice.get("vendor_address", ""), fontsize=10, fontname="helv", color=MUTED)

    y += 34
    page.insert_text((56, y), f"Invoice Number: {invoice['invoice_number']}", fontsize=10, fontname="helv", color=INK)
    y += 15
    page.insert_text((56, y), f"Invoice Date: {invoice['invoice_date']}", fontsize=10, fontname="helv", color=INK)
    y += 15
    page.insert_text((56, y), f"Due Date: {invoice['due_date']}", fontsize=10, fontname="helv", color=INK)

    y += 30
    page.insert_text((56, y), "Bill To:", fontsize=10, fontname="hebo", color=INK)
    y += 14
    page.insert_text((56, y), "Lehigh Valley Phantoms", fontsize=10, fontname="helv", color=INK)
    y += 14
    page.insert_text((56, y), "701 Hamilton Street, Allentown, PA 18101", fontsize=10, fontname="helv", color=MUTED)

    y += 34
    page.insert_text((56, y), "Description", fontsize=10, fontname="hebo", color=INK)
    page.insert_text((330, y), "Qty", fontsize=10, fontname="hebo", color=INK)
    page.insert_text((390, y), "Unit Price", fontsize=10, fontname="hebo", color=INK)
    page.insert_text((480, y), "Line Total", fontsize=10, fontname="hebo", color=INK)
    y += 6
    page.draw_line((56, y), (556, y), color=RULE, width=0.6)
    y += 16

    for item in invoice["line_items"]:
        page.insert_text((56, y), item["description"], fontsize=9.5, fontname="helv", color=INK)
        page.insert_text((330, y), f"{item['quantity']:g}", fontsize=9.5, fontname="helv", color=INK)
        page.insert_text((390, y), f"${item['unit_price']:,.2f}", fontsize=9.5, fontname="helv", color=INK)
        page.insert_text((480, y), f"${item['line_total']:,.2f}", fontsize=9.5, fontname="helv", color=INK)
        y += 18

    y += 8
    page.draw_line((330, y), (556, y), color=RULE, width=0.6)
    y += 18

    for label, value in [
        ("Subtotal", invoice["subtotal"]),
        ("Tax", invoice["tax"]),
        ("Shipping", invoice["shipping"]),
        ("Total Due", invoice["total_due"]),
    ]:
        weight = "hebo" if label == "Total Due" else "helv"
        page.insert_text((390, y), label, fontsize=10, fontname=weight, color=INK)
        page.insert_text((480, y), f"${value:,.2f}", fontsize=10, fontname=weight, color=INK)
        y += 16

    doc.save(path)
    doc.close()


def seed_demo_data(database_path: Path, upload_folder: Path) -> None:
    """Populate an empty database with sample invoices and matching PDFs.

    Safe to call on every app start — it's a no-op the moment any invoice
    exists, so it never overwrites real data or duplicates the demo set.
    """

    if get_all_invoices(database_path):
        return

    upload_folder.mkdir(parents=True, exist_ok=True)

    for invoice in DEMO_INVOICES:
        source_file = f"demo_{invoice['invoice_number']}.pdf"
        pdf_path = upload_folder / source_file

        if not pdf_path.exists():
            _draw_invoice_pdf(pdf_path, invoice)

        validation_result = validate_invoice(invoice)

        record = {
            **invoice,
            "source_file": source_file,
            "validation_status": "Valid" if validation_result["is_valid"] else "Needs Review",
            "validation_errors": "; ".join(validation_result["errors"]),
        }

        save_invoice(database_path, record)