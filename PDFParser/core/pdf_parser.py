import pdfplumber
import pandas as pd
import re
import logging

class PDFParser:
    ENTRY_HEADER_RE = re.compile(
        r"^(?P<job_id>JB\d+)\s+"
        r"(?P<customer>.+?)\s+"
        r"(?P<staff>[A-Z][a-zA-Z .'-]+(?:\s[A-Z][a-zA-Z .'-]+)*)\s+"
        r"(?P<billing_rate>.+?)\s+"
        r"(?P<date>\d{1,2} \w+ \d{4})\s+"
        r"(?P<hours>\d{1,2}:\d{2})$"
    )

    def __init__(self, pdf_path, debug=False):
        self.pdf_path = pdf_path
        self.logger = logging.getLogger(__name__)
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

    def parse_to_dataframe(self) -> pd.DataFrame:
        rows = []
        current_entry = None
        last_job_id = None
        last_customer = None

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                self.logger.debug(f"Extracted text from page {page.page_number}: {text[:100]}...")

                if not text:
                    continue

                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        continue

                    match = self.ENTRY_HEADER_RE.match(line)
                    if match:
                        if current_entry:
                            # Clean notes before appending
                            current_entry["notes"] = " ".join(current_entry["notes"].split())
                            rows.append(current_entry)

                        groups = match.groupdict()

                        last_job_id = groups["job_id"]
                        last_customer = groups["customer"]

                        current_entry = {
                            "job_id": last_job_id,
                            "customer": last_customer,
                            "staff": groups["staff"],
                            "billing_rate": groups["billing_rate"],
                            "date": groups["date"],
                            "hours": groups["hours"],
                            "notes": ""
                        }
                        self.logger.debug(f"New entry detected: {current_entry}")
                    else:
                        # Append to notes
                        if current_entry:
                            current_entry["notes"] += " " + line
                        else:
                            self.logger.debug(f"Skipping line outside entries: {line}")

        # Append last entry if exists
        if current_entry:
            current_entry["notes"] = " ".join(current_entry["notes"].split())
            rows.append(current_entry)

        if not rows:
            raise ValueError("No entries found in PDF.")

        df = pd.DataFrame(rows)
        return df
