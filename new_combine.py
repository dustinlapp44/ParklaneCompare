from dataclasses import dataclass
from typing import List
from compare import Record

@dataclass
class CombinationEntry:
    """Represents a combination of records that match within a tolerance"""
    identifier: str
    invoices: List[Record]
    payments: List[Record]

    def get_invoices(self) -> List[Record]:
        """Returns the list of invoices in this combination"""
        return self.invoices
    
    def get_payments(self) -> List[Record]:
        """Returns the list of payments in this combination"""
        return self.payments
    
    def get_invoice_sum(self) -> float:
        """Calculates the total amount of the invoices in this combination"""
        return sum(r.amount for r in self.invoices)
    
    def get_payment_sum(self) -> float:
        """Calculates the total amount of the payments in this combination"""
        return sum(r.amount for r in self.payments)
    
    def get_difference(self) -> float:
        """Calculates the difference between invoice sum and payment sum"""
        return self.get_invoice_sum() - self.get_payment_sum()
    
    def get_invoice_ids(self) -> List[str]:
        """Returns a list of invoice IDs in this combination"""
        return [r.id for r in self.invoices]
    
    def get_payment_ids(self) -> List[str]:
        """Returns a list of payment IDs in this combination"""
        return [r.id for r in self.payments]
    
    def get_num_records(self) -> int:
        """Returns the total number of records in this combination"""
        return len(self.invoices) + len(self.payments)
    
    def to_csv(self) -> str:
        """Returns a CSV representation of this combination entry."""

        rows = []
        max_len = max(len(self.invoices), len(self.payments))

        # Build rows
        for i in range(max_len):
            invoice = self.invoices[i] if i < len(self.invoices) else None
            payment = self.payments[i] if i < len(self.payments) else None

            row = []

            # Invoice columns
            if invoice:
                row.extend([
                    invoice.date,
                    invoice.description,
                    str(invoice.amount)
                ])
            else:
                row.extend(['', '', ''])

            # Payment columns
            if payment:
                row.extend([
                    payment.date,
                    payment.description,
                    str(payment.amount)
                ])
            else:
                row.extend(['', '', ''])

            rows.append(','.join(row))

        # Add summary row
        summary = [
            '', '', str(self.get_invoice_sum()),
            '', '', str(self.get_payment_sum())
        ]
        rows.append(','.join(summary))
        ret_str = '\n'.join(rows)
        return ret_str
