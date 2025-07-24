import re

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

# Example usage
if __name__ == "__main__":
    with open("sample_email.txt") as f:
        lines = f.readlines()
    parsed = parse_aptexx_email(lines)
    print(parsed)
