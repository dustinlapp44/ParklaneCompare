from google_drive_client import GoogleDriveClient
import compare as compare
from combine import find_combination_matches, consolidate_combination_matches, write_reconciliation_csv
from excel_output import write_reconciliation_report

if __name__ == "__main__":
    start_date = "2024-01-01"
    end_date = "2025-05-31"

    #compare.pull_all_data(start_date=start_date, end_date=end_date, pull_new_data=True)
    
    matches, unmatched_invoices, unmatched_payments = compare.compare_property_data(property,['Test_Data/Test- PMC Data Combo.csv', 'Test_Data/Test- Property Data Combo.csv'])
    combination_matches = find_combination_matches(
            existing_matches=matches,
            unmatched_invoices=unmatched_invoices,  # your list of unmatched invoice Record objects
            unmatched_payments=unmatched_payments,  # your list of unmatched payment Record objects
            tolerance=100,
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

    for x in final_combined_rows:
        print(x)

    write_reconciliation_csv(
    final_combined_rows=final_combined_rows,
    all_invoices=all_invoices,
    all_payments=all_payments,
    output_file="reconciliation_report.csv"
    )
    
    #output_combined_rows()
    #for line in final_combined_rows:
    #    print(line)
    #    if line.get('Status') == 'Group Match':
    #        print(f"Group ID: {line['Group ID']}, Invoice IDs: {line['Invoice IDs']}, Payment IDs: {line['Payment IDs']}, Difference: {line['Difference']}")

    #summarize_combined_matches(grouped_matches)
    #write_reconciliation_report(
    #        matches=matches,
    #        grouped_matches=grouped_matches,
    #        unmatched_invoices=unmatched_invoices,
    #        unmatched_payments=unmatched_payments,
    #        output_file="reconciliation_report_test.xlsx"
    #    )

    #for property in compare.property_aliases:
    #    
    #    if property.count('Alaska'):
    #        pass
    #    else:
    #        continue
    #    matches, unmatched_invoices, unmatched_payments = compare.compare_property_data(property)
    #    
    #    grouped_matches = find_combination_matches(
    #        existing_matches=matches,
    #        unmatched_invoices=unmatched_invoices,  # your list of unmatched invoice Record objects
    #        unmatched_payments=unmatched_payments,  # your list of unmatched payment Record objects
    #        tolerance=0.8,
    #        max_combination_size=3
    #    )
#
    #    summarize_combined_matches(grouped_matches)


        # Write final Excel report
        #write_reconciliation_report(
        #    matches=matches,
        #    grouped_matches=grouped_matches,
        #    unmatched_invoices=unmatched_invoices,
        #    unmatched_payments=unmatched_payments,
        #    output_file="reconciliation_report.xlsx"
        #)
        
        
        
        
        
        # If you want to save the matches, uncomment the following line
        # compare.save_matches_to_csv(matches, property)
    #drive_client = GoogleDriveClient()
#
    #for property in compare.property_aliases:
    #    invoice_path = compare.invoice_path_template % (property, property)
    #    paymnt_path = compare.payment_path_template % (property, property)
    #    output_path = compare.output_path_template % (property, property)
    #    work_dir = compare.work_dir_template % property
#
    #    drive_client.upload_file_to_folder_path(invoice_path, work_dir)
    #    drive_client.upload_file_to_folder_path(paymnt_path, work_dir)
    #    drive_client.upload_file_to_folder_path(output_path, work_dir)
