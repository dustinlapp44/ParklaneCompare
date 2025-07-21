import pandas as pd
from compare import MatchResult, Record
from typing import List, Dict

def write_reconciliation_report(
    matches: List[MatchResult],
    grouped_matches: List[Dict],
    unmatched_invoices: List[Record],
    unmatched_payments: List[Record],
    output_file: str
):
    """
    Writes all reconciliation data to a single Excel workbook.
    """

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:

        # === 1. Matches ===
        match_rows = []
        for m in matches:
            match_rows.append({
                'Status': 'Match',
                'Identifier': m.record1.invoice or m.record1.job,
                'Invoice ID': m.record1.id,
                'Invoice Desc': m.record1.description,
                'Invoice Amount': m.record1.amount,
                'Payment ID': m.record2.id,
                'Payment Desc': m.record2.description,
                'Payment Amount': m.record2.amount,
                'Similarity Score': m.similarity_score,
                'Confidence': m.confidence
            })
        pd.DataFrame(match_rows).to_excel(writer, sheet_name='Matches', index=False)

        # === 2. Grouped Matches ===
        grouped_rows = []
        for gm in grouped_matches:
            grouped_rows.append({
                'Status': 'Group Match',
                'Identifier': gm['identifier'],
                'Invoice IDs': ', '.join(gm['invoice_ids']),
                'Payment IDs': ', '.join(gm['payment_ids']),
                'Invoice Sum': gm['invoice_sum'],
                'Payment Sum': gm['payment_sum'],
                'Difference': gm['difference']
            })
        pd.DataFrame(grouped_rows).to_excel(writer, sheet_name='Grouped Matches', index=False)

        # === 3. Unmatched Invoices ===
        unmatched_inv_rows = []
        for inv in unmatched_invoices:
            unmatched_inv_rows.append({
                'Status': 'Unmatched Invoice',
                'Identifier': inv.invoice or inv.job,
                'Invoice ID': inv.id,
                'Description': inv.description,
                'Amount': inv.amount
            })
        pd.DataFrame(unmatched_inv_rows).to_excel(writer, sheet_name='Unmatched Invoices', index=False)

        # === 4. Unmatched Payments ===
        unmatched_pay_rows = []
        for pay in unmatched_payments:
            unmatched_pay_rows.append({
                'Status': 'Unmatched Payment',
                'Identifier': pay.invoice or pay.job,
                'Payment ID': pay.id,
                'Description': pay.description,
                'Amount': pay.amount
            })
        pd.DataFrame(unmatched_pay_rows).to_excel(writer, sheet_name='Unmatched Payments', index=False)

    print(f"✅ Reconciliation report saved to {output_file}")
