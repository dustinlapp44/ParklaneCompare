import itertools
from typing import List, Dict, Tuple
from Compare.compare import Record, MatchResult
from collections import defaultdict
from dataclasses import dataclass
from Compare.new_combine import CombinationEntry

tolerance = 1.0  # Default tolerance for matching amounts

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

def group_by_identifier_both(records: List[Record]) -> Dict[str, List[Record]]:
    """
    Groups records by both JB and INV.
    Returns dict: {identifier: [records]} including both keys if present.
    """
    groups = {}
    for r in records:
        keys = set(filter(None, [r.job, r.invoice]))  # Get all non-empty identifiers
        for key in keys:
            groups.setdefault(key, []).append(r)
    return groups

def find_combination_entries(
    existing_matches: List[MatchResult],
    unmatched_invoices: List[Record],
    unmatched_payments: List[Record],
    ) -> List[Dict]:

    # Combine matched + unmatched records
    all_invoices = [m.record1 for m in existing_matches] + unmatched_invoices
    all_payments = [m.record2 for m in existing_matches] + unmatched_payments

    invoice_groups = group_by_identifier_both(all_invoices)
    payment_groups = group_by_identifier_both(all_payments)

    combined_matches = []
    tmp_invoices = []
    tmp_payments = []
    for identifier, inv_group in invoice_groups.items():
        pay_group = payment_groups.get(identifier, [])
        if not pay_group:
            continue
        combined_matches.append(
            CombinationEntry(
                identifier=identifier,
                invoices=inv_group,
                payments=pay_group
            )
        )
    # Now we have a list of CombinationEntry objects
    # Remove single matches back to original matches
    new_combined_matches = []
    new_matches = []
    for entry in combined_matches:
        if entry.get_num_records() > 2:
            new_combined_matches.append(entry)
        else:
            # If the combination only has one invoice and one payment, we treat it as a match
            for match in existing_matches:
                if match.record1.id == entry.get_invoice_ids()[0] and match.record2.id == entry.get_payment_ids()[0]:
                    new_matches.append(match)
                    break  
    return new_combined_matches, new_matches

def find_combination_matches(
    existing_matches: List[MatchResult],
    unmatched_invoices: List[Record],
    unmatched_payments: List[Record],
    tolerance: float = tolerance,
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
            'Invoice Date', 'Invoice Desc', 'Invoice Amount','Payment Date', 'Payment Desc', 'Payment Amount','Difference', 'Status',
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        previous_group_info = {
            'Invoice Date': '',
            'Invoice Desc': '',
            'Invoice Amount': '',
            'Payment Date': '',
            'Payment Desc': '',
            'Payment Amount':'' 
            }
        for row in final_combined_rows:
            if row['Status'] == 'SpaceHolder':
                writer.writerow({})
                continue  # Write empty row, continue to next

            output = {
                'Status': row.get('Status'),
                'Difference': row.get('Difference', '')
            }
            
            # === For Matches and Group Matches ===
            if row['Status'] in ['Match', 'Group Match']:
                # For group match, just show combined summary
                if row['Status'] == 'Group Match':
                    output.update(previous_group_info)
                    writer.writerow(output)
                    writer.writerow({})

                    previous_group_info.update({
                        'Invoice Date': '',
                        'Invoice Desc': '',
                        'Invoice Amount': row.get('Invoice Sum'),
                        'Payment Date': '',
                        'Payment Desc': '',
                        'Payment Amount': row.get('Payment Sum')
                    })
                    continue
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
                    'Payment Amount': '',
                    'Status': ''
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
                    'Payment Amount': pay.amount if pay else '',
                    'Status': ''
                })

            elif row['Status'] == 'Unmatched Invoice':
                inv = invoice_lookup.get(row.get('Invoice ID'))
                output.update({
                'Invoice Amount': inv.amount,
                'Invoice Date': inv.raw_data.get('Date'),
                'Invoice Desc': inv.description,
                'Payment Date': '',
                'Payment Desc': '',
                'Payment Amount': '',
                'Status': '',
                })

            elif row['Status'] == 'Unmatched Payment':
                pay = payment_lookup.get(row.get('Payment ID'))
                output.update({
                    'Invoice Date': '',
                    'Invoice Desc': '',
                    'Invoice Amount': '',
                    'Payment Date': pay.raw_data.get('Date') if pay else '',
                    'Payment Desc': pay.description if pay else '',
                    'Payment Amount': pay.amount if pay else '',
                    'Status': '',
                })

            writer.writerow(output)

    print(f"✅ CSV output saved to {output_file}")

def full_combination_flow(matches, unmatched_invoices, unmatched_payments, output_file):
    combination_matches = find_combination_matches(
        existing_matches=matches,
        unmatched_invoices=unmatched_invoices,  # your list of unmatched invoice Record objects
        unmatched_payments=unmatched_payments,  # your list of unmatched payment Record objects
        tolerance=tolerance,
        max_combination_size=3
    )

    all_invoices = [m.record1 for m in matches] + unmatched_invoices
    all_payments = [m.record2 for m in matches] + unmatched_payments
    formatted_combined_matches = consolidate_combination_matches(combination_matches=combination_matches, all_invoices=all_invoices, all_payments=all_payments)


    matched_invoice_ids = set()
    matched_payment_ids = set()
    final_combined_rows = []

    # === 1. Process combination/grouped matches first ===
    for cm in formatted_combined_matches:
        inv_ids = set(filter(None, (cm.get('Invoice IDs', '').split(','))))
        pay_ids = set(filter(None, (cm.get('Payment IDs', '').split(','))))

        # Skip if any IDs already matched
        if not inv_ids.isdisjoint(matched_invoice_ids) or not pay_ids.isdisjoint(matched_payment_ids):
            continue

        # Add group match
        final_combined_rows.append(cm)

        # Update matched sets
        matched_invoice_ids.update(inv_ids)
        matched_payment_ids.update(pay_ids)
    final_combined_rows.append({
        'Status': 'SpaceHolder'  # Placeholder for better CSV formatting
    })

    # === 2. Process original one-to-one matches second ===
    for m in matches:
        inv_id = m.record1.id
        pay_id = m.record2.id

        # Skip if already matched by combination
        if inv_id in matched_invoice_ids or pay_id in matched_payment_ids:
            continue

        final_combined_rows.append({
            'Group ID': m.record1.invoice or m.record1.job,
            'Status': 'Match',
            'Invoice ID': inv_id,
            'Invoice Amount': m.record1.amount,
            'Payment ID': pay_id,
            'Payment Amount': m.record2.amount,
            'Difference': round((m.record1.amount or 0) - (m.record2.amount or 0), 2)
        })

        matched_invoice_ids.add(inv_id)
        matched_payment_ids.add(pay_id)
    
    final_combined_rows.append({
            'Status': 'SpaceHolder'  # Placeholder for better CSV formatting
        })


    updated_unmatched_invoices = [
    inv for inv in unmatched_invoices if inv.id not in matched_invoice_ids
    ]

    updated_unmatched_payments = [
        pay for pay in unmatched_payments if pay.id not in matched_payment_ids
    ]

    # === 3. Add unmatched invoices ===
    for inv in updated_unmatched_invoices:
        output = {
            'Invoice Date': inv.raw_data.get('Date'),
            'Invoice Desc': inv.description,
            'Invoice Amount': inv.amount,
            'Invoice ID': inv.id,
            'Status': 'Unmatched Invoice',
        }
        final_combined_rows.append(output)

    final_combined_rows.append({
            'Status': 'SpaceHolder'  # Placeholder for better CSV formatting
        })
    
    # === 4. Add unmatched payments ===
    for pay in updated_unmatched_payments:
        output = {
            'Payment Date': pay.raw_data.get('Date'),
            'Payment Desc': pay.description,
            'Payment Amount': pay.amount,
            'Payment ID': pay.id,
            'Status': 'Unmatched Payment',
        }
        final_combined_rows.append(output)

    final_combined_rows.append({
            'Status': 'SpaceHolder'  # Placeholder for better CSV formatting
        })
    write_reconciliation_csv(
    final_combined_rows=final_combined_rows,
    all_invoices=all_invoices,
    all_payments=all_payments,
    output_file=output_file
    )
