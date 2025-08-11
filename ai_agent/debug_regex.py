"""
Debug script to test regex patterns
"""

import re

# Test the property pattern
property_pattern = re.compile(r"\*([A-Za-z0-9 &\-]+) - Rent \(Non-Integrated\)\*")

# Test with actual data from sample email
test_text = "Camels Back - Rent (Non-Integrated)"
print(f"Testing property pattern with: '{test_text}'")
match = property_pattern.search(test_text)
print(f"Match found: {match is not None}")

if match:
    print(f"Matched property: {match.group(1)}")

# Test without asterisks
property_pattern_no_asterisks = re.compile(r"([A-Za-z0-9 &\-]+) - Rent \(Non-Integrated\)")
match2 = property_pattern_no_asterisks.search(test_text)
print(f"Match without asterisks: {match2 is not None}")

if match2:
    print(f"Matched property: {match2.group(1)}")

# Test payment pattern
payment_pattern = re.compile(
    r"(?P<ref>\d+)\s+"
    r"(?P<date>\d{1,2}\s\w+\s\d{4}\s[\d:]+\s\w+)\s+"
    r"(?P<method>(?:ACH|VISA|CREDIT|DEBIT|MASTERCARD)(?:\s\w+)*\s#[0-9]+)\s+"
    r"(?P<person>.+?)\s+"
    r"(?P<unit>[\w\-]+)\s+"
    r"(?P<amount>\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
)

test_payment = "132510794	20 Jul 2025 23:41:04 MDT	VISA DEBIT #5553	Anna Camacho	1426-103	$505.00"
print(f"\nTesting payment pattern with: '{test_payment}'")
payment_match = payment_pattern.search(test_payment)
print(f"Payment match found: {payment_match is not None}")

if payment_match:
    print(f"Payment details: {payment_match.groupdict()}")
