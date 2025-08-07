import os
from parser.email_parser import EmailParser
from data.db import PaymentDatabase
from core.processor import PaymentProcessor
from utils.logger import setup_logger
import logging


class PaymentRunner:
    def __init__(self, email_file_path: str = "Payments/sample_email.txt", db_path: str = "payments.db"):
        self.email_file_path = email_file_path
        self.db_path = db_path
        setup_logger()  # configures logging to file + console
        self.logger = logging.getLogger("payments")

    def run(self):
        self.logger.info("🚀 Starting payment processing...")

        # Load email content
        if not os.path.exists(self.email_file_path):
            self.logger.error(f"❌ Email file not found: {self.email_file_path}")
            return

        with open(self.email_file_path, "r", encoding="utf-8") as f:
            raw_email = f.read()

        # Parse payments
        parser = EmailParser()
        payments = parser.parse_email(raw_email)

        self.logger.info(f"📨 Parsed {len(payments)} payments from email.")

        # Apply payments to DB
        db = PaymentDatabase(self.db_path)
        processor = PaymentProcessor(db)
        processor.apply_payments(payments)
        db.close()

        self.logger.info("✅ Payment processing completed.")
