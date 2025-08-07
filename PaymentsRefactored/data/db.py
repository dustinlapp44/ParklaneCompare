import sqlite3
from typing import List
from models.payment import Payment


class PaymentDatabase:
    def __init__(self, db_path="payments.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """Create payments table if it doesn't exist."""
        query = """
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property TEXT,
            date TEXT,
            amount REAL,
            person TEXT,
            unit TEXT,
            memo TEXT,
            method TEXT,
            ref TEXT UNIQUE
        );
        """
        self.conn.execute(query)
        self.conn.commit()

    def add_payment(self, payment: Payment):
        """Insert a single Payment, skip if ref already exists."""
        try:
            self.conn.execute("""
                INSERT INTO payments (property, date, amount, person, unit, memo, method, ref)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payment.property,
                payment.date.strftime("%Y-%m-%d"),
                payment.amount,
                payment.person,
                payment.unit,
                payment.memo,
                payment.method,
                payment.ref
            ))
            self.conn.commit()
            print(f"✅ Payment added: {payment}")
        except sqlite3.IntegrityError:
            print(f"⚠️ Duplicate ref, skipping: {payment.ref}")

    def add_payments(self, payments: List[Payment]):
        for p in payments:
            self.add_payment(p)

    def list_payments(self) -> List[Payment]:
        """Return all payments from the DB."""
        rows = self.conn.execute("SELECT * FROM payments").fetchall()
        return [
            Payment(
                property=row["property"],
                date=row["date"],
                amount=row["amount"],
                person=row["person"],
                unit=row["unit"],
                memo=row["memo"],
                method=row["method"],
                ref=row["ref"]
            )
            for row in rows
        ]

    def close(self):
        self.conn.close()
