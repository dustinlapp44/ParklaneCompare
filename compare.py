import re, sys, os
import math
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from dateutil import parser
from xero_client import authorize_xero, get_invoices

work_dir_template = f'Invoice Reconciliation/%s/'
invoice_file_template = f'%s - PMC Data.csv'
payment_file_template = f'%s - Property Data.csv'
output_file_template = f'%s - PMC vs Property.csv'
combination_file_template = f'%s - Combination Matches.csv'
invoice_path_template = f'{work_dir_template}{invoice_file_template}'
payment_path_template = f'{work_dir_template}{payment_file_template}'
output_path_template = f'{work_dir_template}{output_file_template}'
combination_path_template = f'{work_dir_template}{combination_file_template}'

headers = {
                'ACCREC':['Type','InvoiceNumber','DateString','DueDateString','Reference','Total','AmountDue','Status','InvoiceSent'],
                'ACCPAY':['Type','DateString', 'Contact', 'InvoiceNumber', 'DueDateString', 'Total', 'AmountDue', 'Status']
                }
    
property_aliases = {
    'Barcelona Apartments': ['Barcelona'],
    'Grove Street Apartments': ['Grove'],
    'Alaska Center': ['Alaska'],
    'Hillcreek Apartments': ['Hillcreek'],
    'Magnolia Apartments': ['Magnolia', 'Magonila'],
    'Parkhill Apartments': ['Parkhill'],
    'Parklane Apartments': ['Parklane'],
    'Premier Apartments': ['Premier'],
    'Quail Park Apartments': ['Quail Park'],
    'State Street Apartments': ['State Street'],
    'Villa Montagna Apartments': ['Villa Montagna'],
    'Offices-Warm Springs': ['Offices-Warm Springs', 'Offices Warm Springs', 'Offices', 'Office'],
    'Warm Springs Apartments': ['Warm Springs Apartments', 'Warm Springs Apts', 'Warm Springs'],
    'Washington Street Apartments': ['Washington'],
    'Parkcenter': ['ParkCenter'],
    'Franklin Plaza': ['Franklin Plaza', 'Plaza'],
    'Union Block Building': ['Union Block'],
    'Camels Back Apartment': ['Camels Back', 'Camels'],
    'Derr Building': ['Derr', 'Deer'],
    'Idaho Building': ['Idaho'],
    'Franklin Street': ['Franklin Street', 'Franklin St'],
    'Idanha': ['Idanha'],
    'Homestead Apartments': ['Homestead', 'Homestread', 'Homested'],
}

invoice_id_col = 'InvoiceID'   # replace with your actual ID column name
invoice_desc_col = 'Combined'
payment_id_col = 'PaymentID'   # replace with your actual ID column name
payment_desc_col = 'Reference'

pull_new_data = True

# ================================
# Data Classes
# ================================

@dataclass
class Record:
    """Represents a data record with text and numeric components"""
    id: str
    description: str
    date: str
    amount: float
    numbers: List[str]
    raw_data: Dict
    invoice: Optional[str] = None
    job: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)

    def to_csv(self) -> str:
        """Returns a CSV representation of this record."""
        return f"{self.date},{self.description},{self.amount}" 

@dataclass
class MatchResult:
    """Represents a match between two records"""
    record1: Record
    record2: Record
    similarity_score: float
    text_score: float
    number_score: float
    confidence: str

    def to_csv(self) -> str:
        """Returns a CSV representation of this match result."""
        return f"{self.record1.date},{self.record1.description},{self.record1.amount}," \
               f"{self.record2.date},{self.record2.description},{self.record2.amount}," 
               #f"{self.similarity_score:.3f},{self.text_score:.3f},{self.number_score:.3f},{self.confidence}"

# ================================
# Fuzzy Matcher Class
# ================================

class FuzzyMatcher:
    def __init__(self, text_weight=0.3, number_weight=0.6, amount_weight=0.1, similarity_threshold=0.6):
        self.text_weight = text_weight
        self.number_weight = number_weight
        self.similarity_threshold = similarity_threshold
        self.amount_weight = amount_weight

    def extract_numbers(self, text: str) -> List[str]:
        """Extract numeric sequences from text"""
        return re.findall(r'\d+', text or '')

    def jaro_winkler_similarity(self, s1: str, s2: str) -> float:
        if not s1 or not s2:
            return 0.0
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def cosine_similarity(self, s1: str, s2: str) -> float:
        words1, words2 = set(s1.lower().split()), set(s2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1.intersection(words2)
        return len(intersection) / (math.sqrt(len(words1)) * math.sqrt(len(words2)))

    def text_similarity(self, text1: str, text2: str) -> float:
        jaro = self.jaro_winkler_similarity(text1, text2)
        cosine = self.cosine_similarity(text1, text2)
        return (jaro + cosine) / 2

    def number_similarity(self, nums1: List[str], nums2: List[str]) -> float:
        if not nums1 or not nums2:
            return 0.0
        matches = sum(1 for n in nums1 if n in nums2)
        return matches / len(nums1)

    def amount_similarity(self, amount1: float, amount2: float) -> float:
        """Calculate similarity between two amounts"""
        if amount1 == 0 and amount2 == 0:
            return 1.0
        if amount1 == 0 or amount2 == 0:
            return 0.0
        return min(amount1, amount2) / max(amount1, amount2)

    def calculate_similarity(self, r1: Record, r2: Record) -> Tuple[float, float, float, float]:
        text_score = self.text_similarity(r1.description, r2.description)
        number_score = self.number_similarity(r1.numbers, r2.numbers)
        amount_score = self.amount_similarity(r1.raw_data.get('Gross', 0.0), r2.raw_data.get('Amount', 0.0))
        if r1.invoice is not None and r2.invoice is not None:
            if r1.invoice == r2.invoice:
                number_score = 1.0
        if r1.job is not None and r2.job is not None:
            if r1.job == r2.job:
                number_score = 1.0
        total_score = (text_score * self.text_weight) + (number_score * self.number_weight)+(amount_score * self.amount_weight)
        return total_score, text_score, number_score, amount_score

    def get_confidence(self, score: float) -> str:
        if score >= 0.8:
            return 'high'
        elif score >= 0.6:
            return 'medium'
        else:
            return 'low'

    def create_record(self, row: Dict, id_col: str, desc_col: str) -> Record:
        desc = str(row.get(desc_col, ''))
        rec_id = str(row.get(id_col, desc))  # Fallback to description if ID missing
        amount = row.get('Gross', 0.0) if 'Gross' in row else row.get('Amount', 0.0)
        date = row.get('Date', '') if 'Date' in row else row.get('DateString', '')
        numbers = self.extract_numbers(desc)
        invoice = self.extract_invoice(desc)
        job = self.extract_job(desc)
        return Record(id=rec_id, description=desc, amount=amount, date=date, numbers=numbers, raw_data=row, invoice=invoice, job=job)

    def extract_invoice(self, row: str) -> Optional[str]:
        """Extract invoice number from row data"""
        # This finds "INV-" followed by one or more digits
        match = re.search(r'(INV-\d+)', row)
        if match:
            return match.group(1)
        else:
            return None
    
    def extract_job(self, row: str) -> Optional[str]:
        """Extract job number from row data"""
       # - 'JB' optionally followed by ':' and/or spaces
        # - then captures one or more digits
        match = re.search(r'JB[:\s]*\.?(\d+)', row, re.IGNORECASE)
        if match:
            return match.group(1)
        else:
            return None
    
    def find_best_matches(self, table1: List[Record], table2: List[Record]) -> Tuple[List[MatchResult], List[Record], List[Record]]:
        """Find best matches globally between table1 and table2 with deduplication"""

        potential_matches = []
        matched_invoices = set()
        matched_payments = set()

        # Build list of all possible matches above threshold
        for inv in table1:
            for pay in table2:
                score, text_score, number_score, amount_score = self.calculate_similarity(inv, pay)

                if score >= self.similarity_threshold:
                    potential_matches.append(MatchResult(
                        record1=inv,
                        record2=pay,
                        similarity_score=score,
                        text_score=text_score,
                        number_score=number_score,
                        confidence=self.get_confidence(score)
                    ))

        # Sort all potential matches by descending similarity score
        potential_matches.sort(key=lambda x: x.similarity_score, reverse=True)

        final_matches = []
        for match in potential_matches:
            inv_id = match.record1.id
            pay_id = match.record2.id

            if inv_id not in matched_invoices and pay_id not in matched_payments:
                final_matches.append(match)
                matched_invoices.add(inv_id)
                matched_payments.add(pay_id)

        # Identify unmatched invoices and payments
        unmatched_invoices = [inv for inv in table1 if inv.id not in matched_invoices]
        unmatched_payments = [pay for pay in table2 if pay.id not in matched_payments]

        return final_matches, unmatched_invoices, unmatched_payments


# ================================
# Helper Functions
# ================================

def load_table(df, id_col: str, desc_col: str) -> List[Record]:
    
    # Add unique payment_id based on index
    #for i in df.index:
    #    df[id_col]=str(i)
    df[id_col] = [str(i) for i in df.index]
    
    matcher = FuzzyMatcher()
    tmp=[]
    for _,row in df.iterrows():
        #print(type(row))
        #print(row)
        #break
        tmp.append(matcher.create_record(row, id_col, desc_col))
    return tmp
    #return [matcher.create_record(row, id_col, desc_col) for _, row in df.iterrows()]

def output_matches(matches: List[MatchResult], unmatched_invoices: List[Record], unmatched_payments: List[Record], output_path: str):
    with open(output_path, 'w') as f:
        f.write("Date,PMC Description,PMC Amount,Date,Property Description,Property Amount,Similarity,TextScore,NumberScore,Confidence\n")
        inv_total= 0.0
        pay_total = 0.0
        for m in matches:
            f.write(f"{m.record1.date},{m.record1.description},{m.record1.amount},"
                    f"{m.record2.date},{m.record2.description},{m.record2.amount},"
                    f"{m.similarity_score:.3f},{m.text_score:.3f},{m.number_score:.3f},{m.confidence}\n")
            inv_total += m.record1.amount
            pay_total += m.record2.amount
        #f.write("Invoice_ID,Payment_ID,Invoice_Desc,Payment_Desc,Similarity,TextScore,NumberScore,Confidence\n")
        #for m in matches:
        #    f.write(f"{m.record1_id},{m.record2_id},{m.record1_desc},{m.record2_desc},"
        #            f"{m.similarity_score:.3f},{m.text_score:.3f},{m.number_score:.3f},{m.confidence}\n")
        # Output unmatched invoices and payments
        f.write(f",,{inv_total:.2f},,,{pay_total:.2f},,,\n")
        f.write('\n')

        # Unmatched Invoices
        for i in unmatched_invoices:
            f.write(f"{i.date},{i.description},{i.amount},,,,\n")

        # Unmatched Payments
        for p in unmatched_payments:
            f.write(f",,,{p.date},{p.description},{p.amount},\n")


    print(f"✅ Matches saved to {output_path}")
    print(f"🔴 Unmatched Invoices: {len(unmatched_invoices)}")
    print(f"🔴 Unmatched Payments: {len(unmatched_payments)}")

def pull_pmc_data(start_date="2025-07-01", end_date="2025-07-02", headers=None, itype=None, contact=None):

    # Implement PMC data pulling logic here
    access_token, tenant_id = authorize_xero(org_name="PMC")
    invoices = get_invoices(access_token, tenant_id, start_date, end_date, itype, contact=contact)
    if not invoices:
        print("No invoices found.")
    else:
        print(f"Found {len(invoices)} invoices.")

    ret_invoices = []
    if headers is not None:
        for invoice in invoices:
            pass
            if invoice['Type'] not in headers.keys():
                print(f"Skipping invoice with unsupported type: {invoice['Type']}")
                continue
            ret_invoice = {}
            for col in headers[invoice['Type']]:
                if col in invoice:
                    ret_invoice[col] = invoice[col]
                else:
                    ret_invoice[col] = None
            ret_invoices.append(ret_invoice)
    else:
        for invoice in invoices:
            ret_invoices.append(invoice)

    return ret_invoices

def pull_property_data(start_date="2025-07-01", end_date="2025-07-02", headers=None, itype=None):

    # Implement PMC data pulling logic here
    access_token, tenant_id = authorize_xero(org_name="Parklane Properties")
    invoices = get_invoices(access_token, tenant_id, start_date, end_date, itype, contact="Parklane Management Company")
    if not invoices:
        print("No invoices found.")
    else:
        print(f"Found {len(invoices)} invoices.")

    ret_invoices = []
    if headers is not None:
        for invoice in invoices:
            if invoice['Type'] not in headers.keys():
                print(f"Skipping invoice with unsupported type: {invoice['Type']}")
                continue
            ret_invoice = {}
            for col in headers[invoice['Type']]:
                if col in invoice:
                    ret_invoice[col] = invoice[col]
                else:
                    ret_invoice[col] = None
            ret_invoices.append(ret_invoice)
    else:
        for invoice in invoices:
            ret_invoices.append(invoice)

    return ret_invoices

def get_examples():
    invoices = pull_pmc_data(start_date="2025-05-01", headers=None, itype=None)
    tmp_pmc = {}
    for invoice in invoices:
        if invoice['Type'] in tmp_pmc.keys():
            continue
        else:
            tmp_pmc[invoice['Type']] = invoice
    
    payments = pull_property_data(start_date="2025-05-01", headers=None, itype=None)
    tmp_parklane = {}
    for payment in payments:
        if payment['Type'] in tmp_parklane.keys():
            continue
        else:
            tmp_parklane[payment['Type']] = payment

    for x in tmp_pmc:
        print(x, tmp_pmc[x].keys())
    print()
    for x in tmp_parklane:
        print(x, tmp_parklane[x].keys())

def get_test_data():
    invoices = pull_pmc_data(start_date="2025-05-01", headers=None, itype='ACCREC')
    payments = pull_property_data(start_date="2025-05-01", headers=None, itype='ACCPAY')
    # Example data for testing
    df = pd.DataFrame(invoices)
    df.to_csv('test_data_pmc.csv', index=False)
    df = pd.DataFrame(payments)
    df.to_csv('test_data_payments.csv', index=False)

def pmc_data_cleanup(in_dict: list[dict]):
    ret_list = []
    source_str=''
    source_flag = False
    ref_str = ''
    inv_str= ''
    com_flag = False
    for item in in_dict:
        new_dict = {}
        for key, value in item.items():
            if source_flag:
                new_dict['Source'] = source_str
                source_flag = False
            elif key == 'Status':
                source_flag = True

            if com_flag:
                new_dict['Combined'] = f"{ref_str} {inv_str}"
                com_flag = False
                ref_str = ''
                inv_str = ''    

            if key == 'DateString':
                if value is not None:
                    new_dict['Date'] = parser.parse(value).strftime('%d %b %Y')
                else:
                    new_dict['Date'] = None
            elif key == 'DueDateString':
                if value is not None:
                    new_dict['DueDate'] = parser.parse(value).strftime('%d %b %Y')
                else:
                    new_dict['DueDate'] = None
            elif key == 'InvoiceSent':
                if value is None:
                    new_dict['InvoiceSent'] = "Not Sent"
                elif value:
                    new_dict['InvoiceSent'] = "Sent"
            elif key == 'Type':
                if value == 'ACCREC':
                    source_str = 'Recievable Invoice'
                elif value == 'ACCPAY':
                    source_str = 'Payable Invoice'
                continue
            elif key == 'Total':
                new_dict['Gross'] = value
            elif key == 'AmountDue':
                new_dict['Balance'] = value
            elif key == 'Reference':
                if value is not None:
                    ref_str = value
                com_flag = True
                new_dict[key] = value
            elif key == 'InvoiceNumber':
                if value is not None:
                    inv_str = value
                new_dict[key] = value
            else:
                new_dict[key] = value
            
        ret_list.append(new_dict)
    return ret_list

def property_data_cleanup(in_dict: list[dict]):
    ret_list = []
    source_str=''
    source_flag = False
    for item in in_dict:
        new_dict = {}
        for key, value in item.items():   
            if source_flag:
                new_dict['Source'] = source_str
                source_flag = False

            if key == 'DateString':
                if value is not None:
                    new_dict['Date'] = parser.parse(value).strftime('%d %b %Y')
                else:
                    new_dict['Date'] = None
            elif key == 'DueDateString':
                if value is not None:
                    new_dict['DueDate'] = parser.parse(value).strftime('%d %b %Y')
                else:
                    new_dict['DueDate'] = None
            elif key == 'Contact':
                if 'Name' in value:
                    new_dict['Contact'] = value['Name']
                else:
                    new_dict['Contact'] = None
                source_flag = True
            elif key == 'InvoiceNumber':
                if value is not None:
                    new_dict['Reference'] = value
                else:
                    new_dict['InvoiceNumber'] = None
            elif key == 'Type':
                if value == 'ACCREC':
                    source_str = 'Recievable Invoice'
                elif value == 'ACCPAY':
                    source_str = 'Payable Invoice'
                continue
            
            ## Will need to adjust these
            elif key == 'Total':
                new_dict['Amount'] = value
            elif key == 'AmountDue':
                new_dict['Balance'] = value
            
            else:
                new_dict[key] = value
            
        ret_list.append(new_dict)
    return ret_list

def create_file(data: List[Dict], filename: str):
    df = pd.DataFrame(data)

    # Save to CSV
    df.to_csv(filename, index=False)
    print(f"File created: {filename}")
    
def create_dir_file(data: List[Dict], filename: str, dir_name: str):
    df = pd.DataFrame(data)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
    filename = os.path.join(dir_name, filename)
    # Save to CSV
    df.to_csv(filename, index=False)
    print(f"File created: {filename}")

def float_conv(x):
    if pd.isnull(x):
        return np.nan
    elif isinstance(x, str):
        return float(x.replace(",", ""))
    else:
        return float(x)
    
def pull_all_data(start_date="2025-07-01", end_date="2025-07-02", headers=headers, pull_new_data=True):
        
        if pull_new_data:
            payments = pull_property_data(start_date=start_date, end_date=end_date, headers=headers, itype='ACCPAY')
            payments = property_data_cleanup(payments)
            create_file(payments, 'All Property Data.csv')
            unmatched_df = pd.read_csv('All Property Data.csv')


            all_length = len(unmatched_df)
            sum_length = 0
            for property_name, aliases in property_aliases.items():
                print(f"Processing property: {property_name}")

                invoices = pull_pmc_data(start_date=start_date, end_date=end_date, headers=headers, itype='ACCREC', contact=property_name)
                invoices = pmc_data_cleanup(invoices)

                create_dir_file(invoices, invoice_file_template%property_name, work_dir_template % property_name)

                # Build regex pattern to match any alias (case-insensitive)
                #pattern = '|'.join([f"(?i){alias}" for alias in aliases])
                pattern = '(?i)' + '|'.join(aliases)
                property_df = unmatched_df[unmatched_df['Reference'].str.contains(pattern, na=False, regex=True)]

                sum_length += len(property_df)
                create_dir_file(property_df, payment_file_template%property_name , work_dir_template % property_name)

                # Remove matched rows from unmatched_df
                unmatched_df = unmatched_df.drop(property_df.index)

            print(f"Number of unmatched rows: {len(unmatched_df)}")
            create_file(unmatched_df, 'Unmatched Property Data.csv')

            print(f"All Property Data Length: {all_length}")
            print(f"Sum of Property Data Lengths: {sum_length}")    

def overwrite_with_local_files(overwrite: List[str]):
    df = pd.read_csv(overwrite[0])
    df['Gross'] = df['Gross'].apply(float_conv)
    df['Balance'] = df['Balance'].apply(float_conv)
    invoices = load_table(df, invoice_id_col, invoice_desc_col)
    df = pd.read_csv(overwrite[1])
    df['Amount'] = df['Amount'].apply(float_conv)
    df = df[df['Contact'] == 'Parklane Management Company']
    payments = load_table(df, payment_id_col, payment_desc_col) 
    return invoices, payments 

def compare_property_data(property_name: str, overwrite=False):
    if overwrite!=False:
        invoices, payments = overwrite_with_local_files(overwrite)
        matcher = FuzzyMatcher(text_weight=0.25, number_weight=0.55, amount_weight=0.2, similarity_threshold=0.6)
        matches, unmatched_invoices, unmatched_payments = matcher.find_best_matches(invoices, payments)
        return matches, unmatched_invoices, unmatched_payments
    
    # Read csv into df
    df = pd.read_csv(invoice_path_template % (property_name, property_name))
    df['Gross'] = df['Gross'].apply(float_conv)
    df['Balance'] = df['Balance'].apply(float_conv)
    invoices = load_table(df, invoice_id_col, invoice_desc_col)

    df = pd.read_csv(payment_path_template % (property_name, property_name))
    df['Amount'] = df['Amount'].apply(float_conv)
    df = df[df['Contact'] == 'Parklane Management Company']
    payments = load_table(df, payment_id_col, payment_desc_col)   

    # Match
    matcher = FuzzyMatcher(text_weight=0.25, number_weight=0.55, amount_weight=0.2, similarity_threshold=0.6)
    matches, unmatched_invoices, unmatched_payments = matcher.find_best_matches(invoices, payments)

    # Output
    output_matches(matches, [inv for inv in unmatched_invoices], [pay for pay in unmatched_payments], output_path=output_path_template % (property_name, property_name))
    return matches, unmatched_invoices, unmatched_payments

def compare_all_data():
    all_data = {}
    for property_name, aliases in property_aliases.items():
        matches, unmatched_invoices, unmatched_payments =  compare_property_data(property_name)
        all_data['property_name'] = {}
        all_data['property_name']['matches'] = matches
        all_data['property_name']['unmatched_invoices'] = unmatched_invoices
        all_data['property_name']['unmatched_payments'] = unmatched_payments

    return all_data
        

# Main
# ================================

if __name__ == "__main__":
    
    

    
    start_date = "2024-01-01"
    end_date = "2025-05-31"

    #pull_all_data(start_date=start_date, end_date=end_date, pull_new_data=pull_new_data)
    compare_all_data()
    





    
    


  
    