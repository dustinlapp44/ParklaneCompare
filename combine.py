import itertools
from typing import List, Dict, Tuple, Optional
from compare import Record, MatchResult

def group_by_identifier(records: List[Record]) -> Dict[str, List[Record]]:
    """
    Group records by JB or INV. Returns dict: {identifier: [records]}
    """
    groups = {}
    for r in records:
        key = r.job or r.invoice
        if key:
            groups.setdefault(key, []).append(r)
    return groups

def find_combination_matches(
    existing_matches: List[MatchResult],
    unmatched_invoices: List[Record],
    unmatched_payments: List[Record],
    tolerance: float = 1.0,
    max_combination_size: int = 3
) -> List[Dict]:
    """
    Find combination matches between invoices and payments.
    Considers previous matches and unmatched entries to combine for better matching.
    """
    # Prepare combined lists for analysis
    invoice_groups = group_by_identifier(unmatched_invoices)
    payment_groups = group_by_identifier(unmatched_payments)

    combined_matches = []

    for identifier in invoice_groups:
        inv_group = invoice_groups[identifier]
        pay_group = payment_groups.get(identifier, [])

        if not pay_group:
            continue

        # Generate combinations of invoices
        for i in range(1, min(max_combination_size, len(inv_group))+1):
            for inv_combo in itertools.combinations(inv_group, i):
                inv_sum = sum(r.amount for r in inv_combo)

                # Generate combinations of payments
                for j in range(1, min(max_combination_size, len(pay_group))+1):
                    for pay_combo in itertools.combinations(pay_group, j):
                        pay_sum = sum(r.amount for r in pay_combo)

                        if abs(inv_sum - pay_sum) <= tolerance:
                            combined_matches.append({
                                'identifier': identifier,
                                'invoices': [r.id for r in inv_combo],
                                'payments': [r.id for r in pay_combo],
                                'invoice_sum': inv_sum,
                                'payment_sum': pay_sum,
                                'difference': round(inv_sum - pay_sum, 2)
                            })

    # Also check for potential cross-matches with existing matches if needed
    # Example: combine existing matches with unmatched payments, if business rules allow
    # (Extend here if your pipeline will support multi-stage combination chains)

    return combined_matches

def summarize_combined_matches(combined_matches: List[Dict]) -> None:
    """
    Print a summary of combined matches for quick inspection.
    """
    print(f"✅ Combined Matches Found: {len(combined_matches)}")
    for cm in combined_matches:
        print(f"Identifier: {cm['identifier']}, "
              f"Invoices: {cm['invoices']}, "
              f"Payments: {cm['payments']}, "
              f"Invoice Sum: {cm['invoice_sum']}, "
              f"Payment Sum: {cm['payment_sum']}, "
              f"Diff: {cm['difference']}")

