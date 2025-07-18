import re
import math
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher

# ================================
# Data Classes
# ================================

@dataclass
class Record:
    """Represents a data record with text and numeric components"""
    id: str
    description: str
    numbers: List[str]
    raw_data: Dict
    invoice: Optional[str] = None
    job: Optional[str] = None

@dataclass
class MatchResult:
    """Represents a match between two records"""
    record1_id: str
    record2_id: str
    record1_desc: str
    record2_desc: str
    record1_amount: float
    record2_amount: float
    similarity_score: float
    text_score: float
    number_score: float
    confidence: str

# ================================
# Fuzzy Matcher Class
# ================================

class FuzzyMatcher:
    def __init__(self, text_weight=0.3, number_weight=0.7, similarity_threshold=0.6):
        self.text_weight = text_weight
        self.number_weight = number_weight
        self.similarity_threshold = similarity_threshold

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

    def calculate_similarity(self, r1: Record, r2: Record) -> Tuple[float, float, float]:
        if r1.id.count('Alaska Common JB'):
            pass
        text_score = self.text_similarity(r1.description, r2.description)
        number_score = self.number_similarity(r1.numbers, r2.numbers)
        if r1.invoice is not None and r2.invoice is not None:
            if r1.invoice == r2.invoice:
                number_score = 1.0
        if r1.job is not None and r2.job is not None:
            if r1.job == r2.job:
                number_score = 1.0
        total_score = (text_score * self.text_weight) + (number_score * self.number_weight)
        return total_score, text_score, number_score

    def get_confidence(self, score: float) -> str:
        if score >= 0.8:
            return 'high'
        elif score >= 0.6:
            return 'medium'
        else:
            return 'low'

    def create_record(self, row: Dict, id_col: str, desc_col: str) -> Record:
        desc = str(row.get(desc_col, ''))
        if desc.count('Alaska Common JB28235'):
             pass
        rec_id = str(row.get(id_col, desc))  # Fallback to description if ID missing
        numbers = self.extract_numbers(desc)
        invoice = self.extract_invoice(desc)
        job = self.extract_job(desc)
        return Record(id=rec_id, description=desc, numbers=numbers, raw_data=row, invoice=invoice, job=job)

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
    
    def find_best_matches(self, table1: List[Record], table2: List[Record]) -> Tuple[List[MatchResult], List[str], List[str]]:
        """Find best matches between table1 and table2 with deduplication"""
        matches = []
        matched_invoices = set()
        matched_payments = set()

        # Pass 1: Invoices -> Payments
        for inv in table1:
            best_score = 0
            best_match = None
            for pay in table2:
                if pay.id in matched_payments:
                    continue
                score, text_score, number_score = self.calculate_similarity(inv, pay)
                if score >= self.similarity_threshold and score > best_score:
                    best_score = score
                    best_match = (pay, score, text_score, number_score)

            if best_match:
                pay, score, text_score, number_score = best_match
                matches.append(MatchResult(
                    record1_id=inv.id,
                    record2_id=pay.id,
                    record1_desc=inv.description,
                    record2_desc=pay.description,
                    record1_amount=float(inv.raw_data.get('Gross').replace(",","")),
                    record2_amount=float(pay.raw_data.get('Amount').replace(",","")),
                    similarity_score=score,
                    text_score=text_score,
                    number_score=number_score,
                    confidence=self.get_confidence(score)
                ))
                matched_invoices.add(inv.id)
                matched_payments.add(pay.id)

        # Pass 2: Payments -> Invoices for unmatched payments
        for pay in table2:
            if pay.id in matched_payments:
                ## Already matched on the first pass
                continue
            best_score = 0
            best_match = None
            for inv in table1:
                if inv.id in matched_invoices:
                    ## Already matched on the first pass
                    continue
                score, text_score, number_score = self.calculate_similarity(inv, pay)
                if score >= self.similarity_threshold and score > best_score:
                    best_score = score
                    best_match = (inv, score, text_score, number_score)

            if best_match:
                inv, score, text_score, number_score = best_match
                matches.append(MatchResult(
                    record1_id=inv.id,
                    record2_id=pay.id,
                    record1_desc=inv.description,
                    record2_desc=pay.description,
                    record1_amount=float(inv.raw_data.get('Gross').replace(",","")),
                    record2_amount=float(pay.raw_data.get('Amount').replace(",","")),
                    similarity_score=score,
                    text_score=text_score,
                    number_score=number_score,
                    confidence=self.get_confidence(score)
                ))
                matched_invoices.add(inv.id)
                matched_payments.add(pay.id)

        unmatched_invoices = [(inv.id,inv.description,float(inv.raw_data.get('Gross').replace(",",""))) for inv in table1 if inv.id not in matched_invoices]
        unmatched_payments = [(pay.id,pay.description,float(pay.raw_data.get('Amount'.replace(",","")))) for pay in table2 if pay.id not in matched_payments]

        # Sort matches by descending similarity score
        matches.sort(key=lambda x: x.similarity_score, reverse=True)

        return matches, unmatched_invoices, unmatched_payments

# ================================
# Helper Functions
# ================================

def load_table(filepath: str, id_col: str, desc_col: str) -> List[Record]:
    df = pd.read_csv(filepath, skiprows=1)
    
    # Add unique payment_id based on index
    df[id_col] = [str(i) for i in df.index]
    
    matcher = FuzzyMatcher()
    tmp = []
    for _,row in df.iterrows():
        tmp.append(matcher.create_record(row, id_col, desc_col))
    return tmp
    #return [matcher.create_record(row, id_col, desc_col) for _, row in df.iterrows()]

def output_matches(matches: List[MatchResult], unmatched_invoices: List[str], unmatched_payments: List[str], output_path: str):
    with open(output_path, 'w') as f:
        f.write("Invoice_Desc,Invoice Amount,Payment_Desc,Patyment Amount,Similarity,TextScore,NumberScore,Confidence\n")
        inv_total= 0.0
        pay_total = 0.0
        for m in matches:
            f.write(f"{m.record1_desc},{m.record1_amount},{m.record2_desc},{m.record2_amount},"
                    f"{m.similarity_score:.3f},{m.text_score:.3f},{m.number_score:.3f},{m.confidence}\n")
            inv_total += m.record1_amount
            pay_total += m.record2_amount
        #f.write("Invoice_ID,Payment_ID,Invoice_Desc,Payment_Desc,Similarity,TextScore,NumberScore,Confidence\n")
        #for m in matches:
        #    f.write(f"{m.record1_id},{m.record2_id},{m.record1_desc},{m.record2_desc},"
        #            f"{m.similarity_score:.3f},{m.text_score:.3f},{m.number_score:.3f},{m.confidence}\n")
        # Output unmatched invoices and payments
        f.write(f",{inv_total:.2f},,{pay_total:.2f},,,\n")
        f.write('\n')

        # Unmatched Invoices
        for i in unmatched_invoices:
            f.write(f"{i},,,,,\n")

        # Unmatched Payments
        for p in unmatched_payments:
            f.write(f",{p},,\n")


    print(f"✅ Matches saved to {output_path}")
    print(f"🔴 Unmatched Invoices: {len(unmatched_invoices)}")
    print(f"🔴 Unmatched Payments: {len(unmatched_payments)}")

def output_unmatched(unmatched_invoices: List[str], unmatched_payments: List[str], no_invoice_file: str, no_payment_file: str):
    pd.DataFrame(unmatched_invoices, columns=['Invoice Description']).to_csv(no_invoice_file, index=False)
    pd.DataFrame(unmatched_payments, columns=['Payment Description']).to_csv(no_payment_file, index=False)
    print(f"🔴 Unmatched Invoices saved to {no_invoice_file}")
    print(f"🔴 Unmatched Payments saved to {no_payment_file}")

def output_all_results(matches: List[Tuple[str, str, float]], unmatched_invoices: List[Tuple[str, str]], unmatched_payments: List[Tuple[str, str]], output_file: str):
    """
    matches: list of tuples (invoice_id, payment_id, score)
    unmatched_invoices: list of tuples (invoice_id, invoice_description)
    unmatched_payments: list of tuples (payment_id, payment_description)
    """

    # Create DataFrame for matches
    matches_df = pd.DataFrame(matches, columns=['Invoice ID', 'Payment ID', 'Score'])

    # Create DataFrame for unmatched invoices with extra empty columns for spacing
    unmatched_invoices_df = pd.DataFrame(unmatched_invoices, columns=['Invoice ID', 'Invoice Description'])
    # Add empty columns for spacing
    for i in range(3):  # Assuming 3 columns in matches
        unmatched_invoices_df.insert(0, f'Empty_{i}', '')

    # Create DataFrame for unmatched payments with extra empty columns before their data
    unmatched_payments_df = pd.DataFrame(unmatched_payments, columns=['Payment ID', 'Payment Description'])
    # Add empty columns for spacing
    for i in range(3 + unmatched_invoices_df.shape[1]):  # Shift to the right after matches and unmatched_invoices
        unmatched_payments_df.insert(0, f'Empty_{i}', '')

    # Concatenate all parts
    final_df = pd.concat([matches_df, unmatched_invoices_df, unmatched_payments_df], ignore_index=True)

    # Save to CSV
    final_df.to_csv(output_file, index=False)
    print(f"✅ All results saved to {output_file}")

# ================================
# Main
# ================================

if __name__ == "__main__":
    # Filepaths and column names
    invoice_file = 'Alaska Center - PMC Data.csv'
    no_payment_file = 'Alaska Center - No Matching Payments Data.csv'

    payment_file = 'Alaska Center - Property Data.csv'
    no_invoice_file = 'Alaska Center - No Matching Invoices Data.csv'

    output_file = 'output_matches.csv'

    invoice_id_col = 'InvoiceID'   # replace with your actual ID column name
    invoice_desc_col = 'Combined'

    payment_id_col = 'PaymentID'   # replace with your actual ID column name
    payment_desc_col = 'Reference'

    # Load tables
    invoices = load_table(invoice_file, invoice_id_col, invoice_desc_col)
    payments = load_table(payment_file, payment_id_col, payment_desc_col)

    # Match
    matcher = FuzzyMatcher(text_weight=0.3, number_weight=0.7, similarity_threshold=0.5)
    matches, unmatched_invoices, unmatched_payments = matcher.find_best_matches(invoices, payments)

    # Output
    output_matches(matches, [i[1] for i in unmatched_invoices], [p[1] for p in unmatched_payments], output_file)
    #output_unmatched(unmatched_invoices, unmatched_payments, no_invoice_file, no_payment_file)
