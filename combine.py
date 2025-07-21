import itertools
from typing import List, Dict, Tuple
from compare import Record, MatchResult
from collections import defaultdict

def group_by_identifier(records: List[Record]) -> Dict[str, List[Record]]:
    """
    Groups records by JB or INV. Returns dict: {identifier: [records]}
    """
    groups = {}
    for r in records:
        key = r.job or r.invoice
        if key:
            groups.setdefault(key, []).append(r)
    return groups

#def find_combination_matches(
#    existing_matches: List[MatchResult],
#    unmatched_invoices: List[Record],
#    unmatched_payments: List[Record],
#    tolerance: float = 1.0,
#    max_combination_size: int = 3
#) -> List[Dict]:
#    """
#    Finds combination matches between invoices and payments,
#    consolidating overlapping groups for analysis and output clarity.
#    """
#
#    # Combine matched + unmatched records
#    all_invoices = [m.record1 for m in existing_matches] + unmatched_invoices
#    all_payments = [m.record2 for m in existing_matches] + unmatched_payments
#
#    invoice_groups = group_by_identifier(all_invoices)
#    payment_groups = group_by_identifier(all_payments)
#
#    consolidated_groups = defaultdict(lambda: {
#        'invoice_ids': set(),
#        'payment_ids': set(),
#        'invoice_sum': 0,
#        'payment_sum': 0
#    })
#
#    for identifier, inv_group in invoice_groups.items():
#        pay_group = payment_groups.get(identifier, [])
#        if not pay_group:
#            continue
#
#        for i in range(1, min(max_combination_size, len(inv_group)) + 1):
#            for inv_combo in itertools.combinations(inv_group, i):
#                inv_sum = sum(r.amount for r in inv_combo)
#
#                for j in range(1, min(max_combination_size, len(pay_group)) + 1):
#                    for pay_combo in itertools.combinations(pay_group, j):
#                        pay_sum = sum(r.amount for r in pay_combo)
#
#                        if abs(inv_sum - pay_sum) <= tolerance:
#                            group = consolidated_groups[identifier]
#                            group['invoice_ids'].update(r.id for r in inv_combo)
#                            group['payment_ids'].update(r.id for r in pay_combo)
#                            group['invoice_sum'] += inv_sum
#                            group['payment_sum'] += pay_sum
#
#    # Convert to final output format
#    combined_matches = []
#    for identifier, data in consolidated_groups.items():
#        diff = data['invoice_sum'] - data['payment_sum']
#        combined_matches.append({
#            'identifier': identifier,
#            'invoice_ids': list(data['invoice_ids']),
#            'payment_ids': list(data['payment_ids']),
#            'invoice_sum': data['invoice_sum'],
#            'payment_sum': data['payment_sum'],
#            'difference': round(diff, 2)
#        })
#
#    return combined_matches
def find_combination_matches(
    existing_matches: List[MatchResult],
    unmatched_invoices: List[Record],
    unmatched_payments: List[Record],
    tolerance: float = 1.0,
    max_combination_size: int = 3
    ) -> List[Dict]:
    """
    Finds combination matches between invoices and payments.
    Returns distinct valid combinations without accumulating sums.
    """

    # Combine matched + unmatched records
    all_invoices = [m.record1 for m in existing_matches] + unmatched_invoices
    all_payments = [m.record2 for m in existing_matches] + unmatched_payments

    invoice_groups = group_by_identifier(all_invoices)
    payment_groups = group_by_identifier(all_payments)

    combined_matches = []

    for identifier, inv_group in invoice_groups.items():
        pay_group = payment_groups.get(identifier, [])
        if not pay_group:
            continue

        # Generate combinations of invoices
        for i in range(1, min(max_combination_size, len(inv_group)) + 1):
            for inv_combo in itertools.combinations(inv_group, i):
                inv_sum = sum(r.amount for r in inv_combo)

                # Generate combinations of payments
                for j in range(1, min(max_combination_size, len(pay_group)) + 1):
                    for pay_combo in itertools.combinations(pay_group, j):
                        pay_sum = sum(r.amount for r in pay_combo)

                        if abs(inv_sum - pay_sum) <= tolerance:
                            combined_matches.append({
                                'identifier': identifier,
                                'invoice_ids': [r.id for r in inv_combo],
                                'payment_ids': [r.id for r in pay_combo],
                                'invoice_sum': inv_sum,
                                'payment_sum': pay_sum,
                                'difference': round(inv_sum - pay_sum, 2)
                            })

    return combined_matches

def summarize_combined_matches(combined_matches: List[Dict]) -> None:
    """
    Prints a summary of combined matches for quick CLI inspection.
    """
    print(f"✅ Combined Matches Found: {len(combined_matches)}")
    for cm in combined_matches:
        if cm['difference'] == 0:
            status = "✅"
        else:
            status = "⚠️"
            print(f"Identifier: {cm['identifier']}, "
                  f"Invoices: {cm['invoice_ids']} (${cm['invoice_sum']}), "
                  f"Payments: {cm['payment_ids']} (${cm['payment_sum']}), "
                  f"Diff: {cm['difference']}")
            
def consolidate_combination_matches(
    combination_matches: List[Dict],
    all_invoices: List[Record],
    all_payments: List[Record],
    consolidate: bool = True
) -> List[Dict]:
    """
    Consolidates combination matches by identifier with correct group sums.
    Requires all_invoices and all_payments to lookup actual amounts.
    """

    from collections import defaultdict

    # Build lookup dictionaries
    invoice_lookup = {r.id: r.amount for r in all_invoices}
    payment_lookup = {r.id: r.amount for r in all_payments}

    output_rows = []

    if consolidate:
        consolidated = defaultdict(lambda: {'invoice_ids': set(), 'payment_ids': set()})

        for cm in combination_matches:
            group = consolidated[cm['identifier']]
            group['invoice_ids'].update(cm['invoice_ids'])
            group['payment_ids'].update(cm['payment_ids'])

        # Build consolidated output rows with recalculated sums
        for identifier, data in consolidated.items():
            inv_ids = data['invoice_ids']
            pay_ids = data['payment_ids']

            invoice_sum = sum(invoice_lookup.get(id, 0) for id in inv_ids)
            payment_sum = sum(payment_lookup.get(id, 0) for id in pay_ids)
            diff = invoice_sum - payment_sum

            output_rows.append({
                'Group ID': identifier,
                'Status': 'Group Match',
                'Invoice IDs': ', '.join(inv_ids),
                'Invoice Sum': invoice_sum,
                'Payment IDs': ', '.join(pay_ids),
                'Payment Sum': payment_sum,
                'Difference': round(diff, 2)
            })

            # Related invoices
            for inv_id in inv_ids:
                output_rows.append({
                    'Group ID': identifier,
                    'Status': 'Related Invoice',
                    'Invoice ID': inv_id
                })

            # Related payments
            for pay_id in pay_ids:
                output_rows.append({
                    'Group ID': identifier,
                    'Status': 'Related Payment',
                    'Payment ID': pay_id
                })

    else:
        # No consolidation, each combination as its own group
        output_rows.extend(combination_matches)

    return output_rows

import csv

def write_reconciliation_csv(
    final_combined_rows: List[Dict],
    all_invoices: List[Record],
    all_payments: List[Record],
    output_file: str
    ):
    """
    Writes final combined rows to a CSV file with invoice and payment columns.
    """

    # Build lookup dictionaries for quick access
    invoice_lookup = {r.id: r for r in all_invoices}
    payment_lookup = {r.id: r for r in all_payments}

    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = [
            'Group ID', 'Status',
            'Invoice Date', 'Invoice Desc', 'Invoice Amount',
            'Payment Date', 'Payment Desc', 'Payment Amount',
            'Difference'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in final_combined_rows:
            output = {
                'Group ID': row.get('Group ID'),
                'Status': row.get('Status'),
                'Difference': row.get('Difference', '')
            }

            # === For Matches and Group Matches ===
            if row['Status'] in ['Match', 'Group Match']:
                # For group match, just show combined summary
                if row['Status'] == 'Group Match':
                    output.update({
                        'Invoice Date': '',
                        'Invoice Desc': row.get('Invoice IDs'),
                        'Invoice Amount': row.get('Invoice Sum'),
                        'Payment Date': '',
                        'Payment Desc': row.get('Payment IDs'),
                        'Payment Amount': row.get('Payment Sum')
                    })
                else:  # One-to-one match
                    inv = invoice_lookup.get(row.get('Invoice ID'))
                    pay = payment_lookup.get(row.get('Payment ID'))
                    output.update({
                        'Invoice Date': inv.raw_data.get('Date') if inv else '',
                        'Invoice Desc': inv.description if inv else '',
                        'Invoice Amount': inv.amount if inv else '',
                        'Payment Date': pay.raw_data.get('Date') if pay else '',
                        'Payment Desc': pay.description if pay else '',
                        'Payment Amount': pay.amount if pay else ''
                    })

            # === For Related Invoice ===
            elif row['Status'] == 'Related Invoice':
                inv = invoice_lookup.get(row.get('Invoice ID'))
                output.update({
                    'Invoice Date': inv.raw_data.get('Date') if inv else '',
                    'Invoice Desc': inv.description if inv else '',
                    'Invoice Amount': inv.amount if inv else '',
                    'Payment Date': '',
                    'Payment Desc': '',
                    'Payment Amount': ''
                })

            # === For Related Payment ===
            elif row['Status'] == 'Related Payment':
                pay = payment_lookup.get(row.get('Payment ID'))
                output.update({
                    'Invoice Date': '',
                    'Invoice Desc': '',
                    'Invoice Amount': '',
                    'Payment Date': pay.raw_data.get('Date') if pay else '',
                    'Payment Desc': pay.description if pay else '',
                    'Payment Amount': pay.amount if pay else ''
                })

            writer.writerow(output)

    print(f"✅ CSV output saved to {output_file}")
