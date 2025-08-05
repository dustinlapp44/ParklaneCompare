import re
from bs4 import BeautifulSoup

property_pattern = re.compile(r"\*([A-Za-z0-9 &\-]+) - Rent \(Non-Integrated\)\*")
payment_pattern = re.compile(
    r"(?P<ref>\d+)\s+"
    r"(?P<date>\d{1,2}\s\w+\s\d{4}\s[\d:]+\s\w+)\s+"
    r"(?P<method>(?:ACH|VISA|CREDIT|DEBIT|MASTERCARD)(?:\s\w+)*\s#[0-9]+)\s+"
    r"(?P<person>.+?)\s+"
    r"(?P<unit>[\w\-]+)\s+"
    r"(?P<amount>\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
)

def parse_aptexx_email(lines):
    full_text = " ".join(lines)
    results = []

    sections = property_pattern.split(full_text)

    for i in range(1, len(sections), 2):
        property_name = sections[i].strip()
        section_text = sections[i+1]

        payments = []
        for match in payment_pattern.finditer(section_text):
            payments.append(match.groupdict())

        if payments:
            results.append({
                "property": property_name,
                "payments": payments
            })

    return results

def print_data(parsed_payments):
    subtotals=0
    for property in parsed_payments:
        print(f"Property: {property['property']}")
        for payment in property['payments']:
            subtotals += float(payment['amount'].replace('$', '').replace(',', ''))
            print(f"  Ref: {payment['ref']} | Date: {payment['date']} | Method: {payment['method']} | Person: {payment['person']} | Unit: {payment['unit']} | Amount: {payment['amount']}")
        print(f"Total for this property: ${sum(float(p['amount'].replace('$', '').replace(',', '')) for p in property['payments'])}")
        print()
    print(f"Subtotal for all payments: ${subtotals:.2f}")

def parse_html_payments(html):
    soup = BeautifulSoup(html, 'html.parser')

    results = []
    current_property = None
    rows = soup.find_all('tr')
    i = 0

    while i < len(rows):
        row = rows[i]
        bold = row.find('b')
        if bold:
            current_property = bold.get_text(strip=True)
            i += 1
            continue

        cols = row.find_all('td')
        if len(cols) == 6:
            try:
                payment = {
                    'property': current_property,
                    'ref': cols[0].get_text(strip=True),
                    'date': cols[1].get_text(strip=True),
                    'method': cols[2].get_text(strip=True),
                    'person': cols[3].get_text(strip=True),
                    'unit': cols[4].get_text(strip=True),
                    'amount': float(cols[5].get_text(strip=True).replace('$', '').replace(',', ''))
                }

                # Check next row for Memo
                if i + 1 < len(rows):
                    next_row = rows[i + 1]
                    memo_label = next_row.find('td', string=lambda x: x and 'Memo:' in x)
                    if memo_label:
                        memo_value = next_row.find_all('td')[1].get_text(strip=True)
                        payment['memo'] = memo_value
                        i += 1  # skip memo row

                results.append(payment)
            except Exception as e:
                print(f"Skipping row due to error: {e}")
        i += 1

    return results

# Example usage
if __name__ == "__main__":
    with open("sample_email.txt") as f:
        lines = f.readlines()
    parsed = parse_aptexx_email(lines)
    print(parsed)
