from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Payment:
    property: str
    date: datetime
    amount: float
    person: str
    unit: str
    method: str
    ref: Optional[str] = None
    memo: Optional[str] = None


@dataclass
class Invoice:
    invoice_id: str
    date: datetime
    amount_due: float
    tenant_name: str
    unit: str
    memo: Optional[str] = None

