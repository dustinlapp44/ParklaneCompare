from google_drive_client import GoogleDriveClient
import compare as compare
from combine import find_combination_matches, consolidate_combination_matches, write_reconciliation_csv, full_combination_flow, find_combination_entries
from excel_output import write_reconciliation_report


if __name__ == "__main__":
    start_date = "2024-01-01"
    end_date = "2025-05-31"

    compare.pull_all_data(start_date=start_date, end_date=end_date, pull_new_data=True)
    
    #matches, unmatched_invoices, unmatched_payments = compare.compare_property_data(property,['Test_Data/Test- PMC Data Combo.csv', 'Test_Data/Test- Property Data Combo.csv'])
    #full_combination_flow(matches, unmatched_invoices, unmatched_payments, output_file='Test_Data/Combined_Results.csv')

    for property, aliases in compare.property_aliases.items():        
        unique_id = {}
        matches, unmatched_invoices, unmatched_payments = compare.compare_property_data(property)
        all_invoices = [m.record1 for m in matches] + unmatched_invoices
        all_payments = [m.record2 for m in matches] + unmatched_payments
        print(f"Total Invoices for {property}: {len(all_invoices)}")
        print(f"Total Payments for {property}: {len(all_payments)}")
        print(f"Total Entries for {property}: {len(all_invoices) + len(all_payments)}")
        print()
        
        print("Stats pre combination:")
        match_len = len(matches)*2
        print(f"Matches for {property}: {match_len}")
        unmatched_len = len(unmatched_invoices) + len(unmatched_payments)
        print(f"Unmatched for {property}: {unmatched_len}")
        total_len = match_len + unmatched_len
        print(f"Total for {property}: {total_len}")
        print()

        combined_matches, new_matches = find_combination_entries(matches, unmatched_invoices, unmatched_payments)
        unique_invoice_ids=[]
        unique_payment_ids=[]
        combo_match_len = 0
        for x in combined_matches:
            combo_match_len += x.get_num_records()
            unique_invoice_ids.extend(x.get_invoice_ids())
            unique_payment_ids.extend(x.get_payment_ids())
        
        new_unmatched_invoices = [i for i in unmatched_invoices if i.id not in unique_invoice_ids]
        new_unmatched_payments = [p for p in unmatched_payments if p.id not in unique_payment_ids]
        
        print("Stats post combination:")
        print(f"New Combination Matches for {property}: {combo_match_len}")
        print(f"New Single Matches for {property}: {len(new_matches)*2}")
        print(f"New Unmatched Invoices for {property}: {len(new_unmatched_invoices)}")
        print(f"New Unmatched Payments for {property}: {len(new_unmatched_payments)}")
        print(f"Total for {property}: {combo_match_len + len(new_unmatched_invoices) + len(new_unmatched_payments) + len(new_matches)*2}")
        
        outfile = compare.combination_file_template % (property, property)
        with open(outfile,'w') as f:
            f.write('Invoice Date,Invoice Description,Invoice Amount,Payment Date,Payment Description,Payment Amount\n')
            for x in combined_matches:
                f.write(x.to_csv())
                f.write('\n')
                f.write('\n')
            f.write('\n')
            for x in new_matches:
                f.write(x.to_csv())
                f.write('\n')
            f.write('\n')
            for x in new_unmatched_invoices:
                f.write(f"{x.date},{x.description},{x.amount},,,\n")
            f.write('\n')
            for x in new_unmatched_payments:
                f.write(f",,{x.amount},{x.date},{x.description},\n")
            f.write('\n')
            
        #full_combination_flow(matches, unmatched_invoices, unmatched_payments, output_file=compare.combination_path_template %(property,property))

  
        
        
        
        
        
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
