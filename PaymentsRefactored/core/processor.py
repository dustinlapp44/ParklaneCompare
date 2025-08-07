from typing import List
from models.payment import Payment
from data.db import PaymentDatabase
import logging


class PaymentProcessor:
    def __init__(self, db: PaymentDatabase):
        self.db = db
        self.logger = logging.getLogger("payments")

    def apply_payments(self, payments: List[Payment]):
        """Apply each payment to the database with logging."""
        added, skipped = 0, 0

        for payment in payments:
            try:
                self.db.add_payment(payment)
                added += 1
            except Exception as e:
                skipped += 1
                self.logger.error(f"❌ Failed to add payment: {payment} — {e}")

        self.logger.info(f"✅ Payments processed. Added: {added}, Skipped: {skipped}")

