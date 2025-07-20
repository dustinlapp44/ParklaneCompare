from match.fuzzy_matcher import FuzzyMatcher
from match.data_cleaner import pmc_data_cleanup, property_data_cleanup
from match.models import Record
import pandas as pd

def main():
    matcher = FuzzyMatcher()

    df1 = pd.read_csv("PMC.csv")
    df2 = pd.read_csv("Property.csv")

    df1 = pmc_data_cleanup(df1)
    df2 = property_data_cleanup(df2)

    table1 = [matcher.create_record(row, "InvoiceID", "Combined", "Gross") for _, row in df1.iterrows()]
    table2 = [matcher.create_record(row, "PaymentID", "Reference", "Amount") for _, row in df2.iterrows()]

    matches, unmatched_inv, unmatched_pay = matcher.find_best_matches(table1, table2)

    # Save matches nicely
    out = pd.DataFrame([m.__dict__ for m in matches])
    out.to_excel("output/matches.xlsx", index=False)

    print(f"✅ Matches: {len(matches)}  |  Unmatched Invoices: {len(unmatched_inv)}  |  Unmatched Payments: {len(unmatched_pay)}")

if __name__ == "__main__":
    main()
