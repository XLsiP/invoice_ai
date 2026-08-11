import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


INVOICE_COLUMNS = [
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
    "validation_errors",
]


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(database_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path) -> None:
    with connect(database_path) as connection:
        connection.execute(
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

        existing_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(invoices)").fetchall()
        }

        migrations = {
            "source_file": "TEXT", "vendor": "TEXT", "invoice_number": "TEXT",
            "invoice_date": "TEXT", "due_date": "TEXT", "description": "TEXT",
            "subtotal": "REAL", "tax": "REAL", "shipping": "REAL", "total_due": "REAL",
            "validation_status": "TEXT", "validation_errors": "TEXT", "created_at": "TIMESTAMP",
        }

        for column, column_type in migrations.items():
            if column not in existing_columns:
                connection.execute(f"ALTER TABLE invoices ADD COLUMN {column} {column_type}")

        connection.execute("CREATE INDEX IF NOT EXISTS idx_invoice_number ON invoices(invoice_number)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_vendor ON invoices(vendor)")

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS invoice_line_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                quantity REAL DEFAULT 0,
                unit_price REAL DEFAULT 0,
                line_total REAL DEFAULT 0,
                FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
            )
            """
        )

        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_invoice_line_items_invoice ON invoice_line_items(invoice_id)"
        )


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def invoice_exists(
    database_path: Path,
    vendor: str,
    invoice_number: str,
    invoice_date: Optional[str] = None,
    total_due: Optional[float] = None,
) -> bool:
    with connect(database_path) as connection:
        vendor_key = normalize_text(vendor)
        invoice_key = normalize_text(invoice_number)

        if vendor_key and invoice_key:
            row = connection.execute(
                """
                SELECT id FROM invoices
                WHERE LOWER(TRIM(vendor)) = ? AND LOWER(TRIM(invoice_number)) = ?
                LIMIT 1
                """,
                (vendor_key, invoice_key),
            ).fetchone()

            if row:
                return True

        if vendor_key and invoice_date and total_due is not None:
            row = connection.execute(
                """
                SELECT id FROM invoices
                WHERE LOWER(TRIM(vendor)) = ? AND invoice_date = ? AND ROUND(total_due,2)=ROUND(?,2)
                LIMIT 1
                """,
                (vendor_key, invoice_date, total_due),
            ).fetchone()

            if row:
                return True

    return False


def safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def save_invoice(database_path: Path, invoice: Dict[str, Any]) -> bool:
    initialize_database(database_path)

    vendor = invoice.get("vendor")
    invoice_number = invoice.get("invoice_number")
    invoice_date = invoice.get("invoice_date")
    total_due = invoice.get("total_due")

    if invoice_exists(database_path, vendor, invoice_number, invoice_date, total_due):
        return False

    with connect(database_path) as connection:
        placeholders = ", ".join("?" for _ in INVOICE_COLUMNS)
        columns = ", ".join(INVOICE_COLUMNS)

        cursor = connection.execute(
            f"INSERT INTO invoices ({columns}) VALUES ({placeholders})",
            [invoice.get(column) for column in INVOICE_COLUMNS],
        )

        invoice_id = cursor.lastrowid
        line_items = invoice.get("line_items", [])

        for item in line_items:
            description = str(item.get("description", "")).strip()

            if not description:
                continue

            connection.execute(
                """
                INSERT INTO invoice_line_items(invoice_id, description, quantity, unit_price, line_total)
                VALUES(?, ?, ?, ?, ?)
                """,
                (
                    invoice_id, description,
                    safe_float(item.get("quantity")),
                    safe_float(item.get("unit_price")),
                    safe_float(item.get("line_total")),
                ),
            )

    return True


def update_invoice(database_path: Path, invoice_id: int, invoice: Dict[str, Any]) -> None:
    """
    Update an existing invoice's fields and replace its purchased items
    with the corrected set. Used by the Database page's Edit flow.
    """

    initialize_database(database_path)

    with connect(database_path) as connection:
        set_clause = ", ".join(f"{column} = ?" for column in INVOICE_COLUMNS)

        connection.execute(
            f"UPDATE invoices SET {set_clause} WHERE id = ?",
            [invoice.get(column) for column in INVOICE_COLUMNS] + [invoice_id],
        )

        connection.execute(
            "DELETE FROM invoice_line_items WHERE invoice_id = ?",
            (invoice_id,),
        )

        for item in invoice.get("line_items", []):
            description = str(item.get("description", "")).strip()

            if not description:
                continue

            connection.execute(
                """
                INSERT INTO invoice_line_items(invoice_id, description, quantity, unit_price, line_total)
                VALUES(?, ?, ?, ?, ?)
                """,
                (
                    invoice_id, description,
                    safe_float(item.get("quantity")),
                    safe_float(item.get("unit_price")),
                    safe_float(item.get("line_total")),
                ),
            )


def get_invoice_line_items(database_path: Path, invoice_id: int) -> List[Dict[str, Any]]:
    initialize_database(database_path)

    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, invoice_id, description, quantity, unit_price, line_total
            FROM invoice_line_items WHERE invoice_id = ? ORDER BY id
            """,
            (invoice_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def search_invoices(database_path: Path, search_term: str) -> List[Dict[str, Any]]:
    initialize_database(database_path)
    pattern = "%" + search_term.strip() + "%"

    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT invoices.*
            FROM invoices
            LEFT JOIN invoice_line_items ON invoice_line_items.invoice_id = invoices.id
            WHERE invoices.vendor LIKE ? COLLATE NOCASE
               OR invoices.invoice_number LIKE ? COLLATE NOCASE
               OR invoices.source_file LIKE ? COLLATE NOCASE
               OR invoices.description LIKE ? COLLATE NOCASE
               OR invoice_line_items.description LIKE ? COLLATE NOCASE
            ORDER BY invoices.created_at DESC
            """,
            (pattern, pattern, pattern, pattern, pattern),
        ).fetchall()

    return [dict(row) for row in rows]


def get_vendor_statistics(database_path: Path) -> List[Dict[str, Any]]:
    initialize_database(database_path)

    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT
                COALESCE(NULLIF(TRIM(vendor), ''), 'Unknown Vendor') AS vendor,
                COUNT(*) AS invoice_count,
                ROUND(SUM(COALESCE(total_due,0)), 2) AS total_spend,
                ROUND(AVG(COALESCE(total_due,0)), 2) AS average_invoice,
                ROUND(MAX(COALESCE(total_due,0)), 2) AS largest_invoice,
                MIN(invoice_date) AS first_invoice_date,
                MAX(invoice_date) AS last_invoice_date
            FROM invoices
            GROUP BY COALESCE(NULLIF(TRIM(vendor), ''), 'Unknown Vendor')
            ORDER BY total_spend DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_invoice(database_path: Path, invoice_id: int) -> Optional[Dict[str, Any]]:
    initialize_database(database_path)

    with connect(database_path) as connection:
        row = connection.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()

    return dict(row) if row else None


def delete_invoice(database_path: Path, invoice_id: int) -> None:
    initialize_database(database_path)

    with connect(database_path) as connection:
        connection.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))


def get_all_invoices(database_path: Path) -> List[Dict[str, Any]]:
    initialize_database(database_path)

    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM invoices ORDER BY datetime(created_at) DESC, id DESC"
        ).fetchall()

    invoices = []

    for row in rows:
        invoice = dict(row)
        invoice["line_items"] = get_invoice_line_items(database_path, invoice["id"])
        invoices.append(invoice)

    return invoices