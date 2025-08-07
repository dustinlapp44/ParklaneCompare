import pdfplumber
import pandas as pd
import re


class PDFParser:
    ENTRY_HEADER_RE = re.compile(
        r"^(?P<job_id>JB\d+)\s+(?P<customer>[A-Za-z\s]+)\s+(?P<staff>[A-Z][a-z]+ [A-Z][a-z]+).*?"
        r"(?P<date>\d{2} \w+ \d{4})\s+(?P<hours>\d{1,2}:\d{2})"
    )

    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def parse_to_dataframe(self) -> pd.DataFrame:
        rows = []
        current_entry = None

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                print(f"[DEBUG] Extracted text from page {page.page_number}: {text}...")  # Debug output
                print()
                print()
                #break
                if not text:
                    continue

                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        continue

                    match = self.ENTRY_HEADER_RE.match(line)
                    if match:
                        if current_entry:
                            rows.append(current_entry)

                        current_entry = match.groupdict()
                        current_entry["notes"] = ""
                    elif current_entry:
                        current_entry["notes"] += " " + line

        if current_entry:
            rows.append(current_entry)

        if not rows:
            raise ValueError("No entries found in PDF.")

        df = pd.DataFrame(rows)
        df["notes"] = df["notes"].str.strip()
        return df
