import sqlite3
from pathlib import Path
from typing import Any, Dict


def initialize_database(database_path: Path) -> None:
    """Create the invoices table if it does not already exist."""

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

    connection.commit()
    connection.close()


def save_invoice(
    database_path: Path,
    invoice: Dict[str, Any],
) -> None:
    """Save one invoice dictionary into the database."""

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
            invoice.get("vendor"),
            invoice.get("invoice_number"),
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