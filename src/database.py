import sqlite3
from pathlib import Path
from typing import Any, Dict, List


def initialize_database(database_path: Path) -> None:
    """Create the invoices table and indexes if they do not exist."""

    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT,
            vendor TEXT,
            invoice_number TEXT,
            invoice_date TEXT,
            due_date TEXT,
            description TEXT,
            subtotal REAL,
            tax REAL,
            shipping REAL,
            total_due REAL,
            validation_status TEXT,
            validation_errors TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_invoice_number
        ON invoices(invoice_number)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_vendor
        ON invoices(vendor)
        """
    )

    connection.commit()
    connection.close()


def invoice_exists(
    database_path: Path,
    vendor: str,
    invoice_number: str,
) -> bool:
    """Return True when the vendor and invoice number already exist."""

    if not vendor or not invoice_number:
        return False

    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT 1
        FROM invoices
        WHERE LOWER(vendor) = LOWER(?)
          AND LOWER(invoice_number) = LOWER(?)
        LIMIT 1
        """,
        (vendor.strip(), invoice_number.strip()),
    )

    exists = cursor.fetchone() is not None

    connection.close()

    return exists


def save_invoice(
    database_path: Path,
    invoice: Dict[str, Any],
) -> bool:
    """
    Save one invoice unless it is a duplicate.

    Return True when saved and False when skipped.
    """

    vendor = invoice.get("vendor")
    invoice_number = invoice.get("invoice_number")

    if invoice_exists(database_path, vendor, invoice_number):
        return False

    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO invoices (
            source_file,
            vendor,
            invoice_number,
            invoice_date,
            due_date,
            description,
            subtotal,
            tax,
            shipping,
            total_due,
            validation_status,
            validation_errors
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            invoice.get("source_file"),
            vendor,
            invoice_number,
            invoice.get("invoice_date"),
            invoice.get("due_date"),
            invoice.get("description"),
            invoice.get("subtotal"),
            invoice.get("tax"),
            invoice.get("shipping"),
            invoice.get("total_due"),
            invoice.get("validation_status"),
            invoice.get("validation_errors"),
        ),
    )

    connection.commit()
    connection.close()

    return True


def search_invoices(
    database_path: Path,
    search_term: str,
) -> List[Dict[str, Any]]:
    """Search invoices by vendor, invoice number, or source filename."""

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    search_pattern = f"%{search_term.strip()}%"

    cursor.execute(
        """
        SELECT *
        FROM invoices
        WHERE vendor LIKE ? COLLATE NOCASE
           OR invoice_number LIKE ? COLLATE NOCASE
           OR source_file LIKE ? COLLATE NOCASE
        ORDER BY created_at DESC
        """,
        (
            search_pattern,
            search_pattern,
            search_pattern,
        ),
    )

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]


def get_all_invoices(
    database_path: Path,
) -> List[Dict[str, Any]]:
    """Return every stored invoice, newest first."""

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM invoices
        ORDER BY created_at DESC
        """
    )

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]