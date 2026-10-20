import unittest
from decimal import Decimal
from pathlib import Path

from routes.registrar import _initial_enrollment_payment_amount


ROOT = Path(__file__).resolve().parents[1]
REGISTRAR = (ROOT / "routes" / "registrar.py").read_text(encoding="utf-8")
CASHIER = (ROOT / "routes" / "cashier.py").read_text(encoding="utf-8")
CREATE_BILL = (ROOT / "templates" / "cashier_create_bill.html").read_text(encoding="utf-8")


class FakeCursor:
    def __init__(self, amount):
        self.amount = amount
        self.sql = ""
        self.params = None

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchone(self):
        return {"amount": self.amount}


class EnrollmentPaymentGateTests(unittest.TestCase):
    def test_payment_lookup_is_scoped_and_accepts_any_positive_cash_amount(self):
        cursor = FakeCursor(Decimal("100.00"))
        amount = _initial_enrollment_payment_amount(cursor, 41, 7, 12)
        self.assertEqual(amount, Decimal("100.00"))
        self.assertEqual(cursor.params, (41, 7, 12))
        self.assertIn("p.enrollment_id = %s", cursor.sql)
        self.assertIn("p.branch_id = %s", cursor.sql)
        self.assertIn("p.year_id = %s", cursor.sql)
        self.assertIn("p.amount > 0", cursor.sql)
        self.assertIn("payment_method", cursor.sql)

    def test_no_payment_returns_zero(self):
        cursor = FakeCursor(None)
        self.assertEqual(_initial_enrollment_payment_amount(cursor, 1, 2, 3), 0)

    def test_registrar_approval_has_server_side_payment_gate(self):
        approval = REGISTRAR[
            REGISTRAR.index('if action == "approved":'):
            REGISTRAR.index('if action == "rejected":')
        ]
        self.assertIn("FOR UPDATE", approval)
        self.assertIn("_initial_enrollment_payment_amount", approval)
        self.assertIn("if initial_payment <= 0:", approval)
        self.assertIn("db.rollback()", approval)

    def test_cashier_registry_includes_pending_applicants(self):
        registry = CASHIER[
            CASHIER.index("def billing_registry"):
            CASHIER.index("def create_bill")
        ]
        self.assertIn("('pending', 'approved', 'enrolled')", registry)

    def test_pending_applicant_payment_is_cash_and_enrollment_fee_only(self):
        payment = CASHIER[
            CASHIER.index("def process_payment"):
            CASHIER.index("@cashier_bp.route", CASHIER.index("def process_payment"))
        ]
        self.assertIn('bill.get("enrollment_status") == "pending"', payment)
        self.assertIn('payment_method.lower() != "cash"', payment)
        self.assertIn('target_type not in ("general", "tuition")', payment)

    def test_tuition_bill_has_no_twenty_thousand_cap(self):
        self.assertNotIn('max="20000"', CREATE_BILL)
        self.assertNotIn("tuition_fee > 20000", CASHIER)


if __name__ == "__main__":
    unittest.main()
