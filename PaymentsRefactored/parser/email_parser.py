import re
from datetime import datetime
from typing import List
from models.payment import Payment


class EmailParser:
    def __init__(self):
        # Line pattern for batch-style payment summaries
        self.line_pattern = re.compile(
            r"(?P<person>.+?)\s+\|\s+(?P<unit>.+?)\s+\|\s+\$?(?P<amount>[0-9,]+\.\d{2})\s+\|\s+(?P<method>.+?)\s+\|\s+(?P<date>\d{1,2} \w{3} \d{4})",
            re.IGNORECASE
        )

    def parse_email(self, email_text: str) -> List[Payment]:
        payments = []

        for match in self.line_pattern.finditer(email_text):
            try:
                amount = float(match.group("amount").replace(",", ""))
                date = datetime.strptime(match.group("date"), "%d %b %Y")
                person = match.group("person").strip()
                unit = match.group("unit").strip()
                method = match.group("method").strip()

                # Infer property from unit if needed (you may want to adjust this)
                property_name = unit.split()[0] if unit else "Unknown"

                payments.append(Payment(
                    property=property_name,
                    date=date,
                    amount=amount,
                    person=person,
                    unit=unit,
                    memo="",  # optional to add from another field
                    method=method,
                    ref=None
                ))
            except Exception as e:
                print(f"⚠️ Skipping row due to parse error: {e}")

        return payments

