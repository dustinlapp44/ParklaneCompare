from google_drive_client import GoogleDriveClient
import compare as compare
import combine as combine

if __name__ == "__main__":
    start_date = "2024-01-01"
    end_date = "2025-05-31"

    #compare.pull_all_data(start_date=start_date, end_date=end_date, pull_new_data=True)
    
    from combine import find_combination_matches, summarize_combined_matches

    for property in compare.property_aliases:
        matches, unmatched_invoices, unmatched_payments = compare.compare_property_data(property)
        
        #combined_matches = find_combination_matches(
        #    existing_matches=matches,
        #    unmatched_invoices=unmatched_invoices,  # your list of unmatched invoice Record objects
        #    unmatched_payments=unmatched_payments,  # your list of unmatched payment Record objects
        #    tolerance=1.0,
        #    max_combination_size=3
        #)

        #summarize_combined_matches(combined_matches)
        
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
