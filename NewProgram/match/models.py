# match/models.py

from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class Record:
    id: str
    description: str
    numbers: List[str]
    raw_data: Dict
    invoice: Optional[str] = None
    job: Optional[str] = None

@dataclass
class MatchResult:
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

    def to_dict(self) -> Dict:
        return {
            "Invoice ID": self.record1_id,
            "Payment ID": self.record2_id,
            "Invoice Description": self.record1_desc,
            "Payment Description": self.record2_desc,
            "Invoice Amount": self.record1_amount,
            "Payment Amount": self.record2_amount,
            "Similarity Score": self.similarity_score,
            "Text Score": self.text_score,
            "Number Score": self.number_score,
            "Confidence": self.confidence
        }

# =======================
# End of models.py
# =======================

# Next: fuzzy_matcher.py will import these dataclasses and implement core logic cleanly.
