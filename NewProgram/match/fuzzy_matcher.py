import re
from typing import List, Tuple
from .models import Record, MatchResult
from difflib import SequenceMatcher
import math

class FuzzyMatcher:
    def __init__(self, text_weight=0.5, number_weight=0.5, similarity_threshold=0.55):
        self.text_weight = text_weight
        self.number_weight = number_weight
        self.similarity_threshold = similarity_threshold

    def extract_numbers(self, text: str) -> List[str]:
        return re.findall(r'\d+', text or '')

    def extract_invoice_number(self, text: str) -> str:
        m = re.search(r'(INV-\d+)', text, re.IGNORECASE)
        return m.group(1) if m else None

    def extract_job_number(self, text: str) -> str:
        m = re.search(r'JB[:\s]*\.?(\d+)', text, re.IGNORECASE)
        return m.group(1) if m else None

    def jaro_winkler_similarity(self, s1: str, s2: str) -> float:
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio() if s1 and s2 else 0.0

    def cosine_similarity(self, s1: str, s2: str) -> float:
        words1, words2 = set(s1.lower().split()), set(s2.lower().split())
        if not words1 or not words2:
            return 0.0
        return len(words1 & words2) / (math.sqrt(len(words1)) * math.sqrt(len(words2)))

    def text_similarity(self, s1: str, s2: str) -> float:
        return (self.jaro_winkler_similarity(s1, s2) + self.cosine_similarity(s1, s2)) / 2

    def number_similarity(self, nums1: List[str], nums2: List[str]) -> float:
        if not nums1 or not nums2:
            return 0.0
        matches = 0
        for n1 in nums1:
            for n2 in nums2:
                if n1 == n2:
                    matches += 1
                elif n1 in n2 or n2 in n1:
                    matches += 0.5
        return matches / len(nums1)

    def calculate_similarity(self, r1: Record, r2: Record) -> Tuple[float, float, float]:
        text = self.text_similarity(r1.description, r2.description)
        number = self.number_similarity(r1.numbers, r2.numbers)
        score = text * self.text_weight + number * self.number_weight
        return score, text, number

    def get_confidence(self, score: float) -> str:
        if score >= 0.8: return "high"
        if score >= 0.6: return "medium"
        if score >= 0.5: return "review"
        return "low"

    def create_record(self, row: dict, id_col: str, desc_col: str, amount_col: str) -> Record:
        desc = str(row.get(desc_col, ''))
        uid = str(row.get(id_col, f'AUTO-{hash(desc)}'))
        amount = float(row.get(amount_col, 0))
        record = Record(
            id=uid,
            description=desc,
            numbers=self.extract_numbers(desc),
            raw_data=row,
            invoice=self.extract_invoice_number(desc),
            job=self.extract_job_number(desc),
            amount=amount
        )
        return record

    def find_best_matches(self, table1: List[Record], table2: List[Record]) -> Tuple[List[MatchResult], List[Tuple[str, str]], List[Tuple[str, str]]]:
        matches, matched1, matched2 = [], set(), set()

        for r1 in table1:
            best_score, best_r2 = 0, None
            for r2 in table2:
                if r2.id in matched2:
                    continue
                score, t_score, n_score = self.calculate_similarity(r1, r2)
                if score >= self.similarity_threshold and score > best_score:
                    best_score, best_r2 = score, (r2, t_score, n_score)
            if best_r2:
                r2, t_score, n_score = best_r2
                matches.append(MatchResult(
                    r1.id, r2.id, r1.description, r2.description,
                    r1.amount, r2.amount, best_score, t_score, n_score,
                    self.get_confidence(best_score)
                ))
                matched1.add(r1.id)
                matched2.add(r2.id)

        unmatched1 = [(r.id, r.description) for r in table1 if r.id not in matched1]
        unmatched2 = [(r.id, r.description) for r in table2 if r.id not in matched2]
        return matches, unmatched1, unmatched2
