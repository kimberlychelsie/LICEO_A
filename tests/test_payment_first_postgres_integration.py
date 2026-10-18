import os
import threading
import unittest
from decimal import Decimal

import psycopg2
import psycopg2.extras

from utils.payment_first_events import (
    record_newly_unavailable,
    record_unavailable_reservations,
    resolve_available_events,
)
from utils.payment_first_lifecycle import cancel_inventory, claim_inventory
from utils.payment_first_payments import process_payment_first_batch
from utils.payment_first_reservations import (
    PaymentFirstError,
    PaymentFirstInventoryUnavailable,
    create_payment_first_reservations,
)
from utils.reservation_security import (
    deduct_reserved_inventory,
    lock_reservation,
    lock_reservation_for_cancellation,
    release_reserved_inventory,
    require_verified_direct_settlement,
)


def _connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ["PAYMENT_FIRST_TEST_DB_NAME"],
        user=os.environ.get("DB_USER", "liceo_db"),
        password=os.environ.get("DB_PASSWORD", "1234"),
    )


class PaymentFirstPostgresIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database = os.environ.get("PAYMENT_FIRST_TEST_DB_NAME", "")
        if not database.startswith("liceo_pf_test_"):
            raise unittest.SkipTest("Disposable payment-first PostgreSQL database is not configured.")
        os.environ["DB_NAME"] = database
        os.environ["RESERVATION_PAYMENT_FIRST_ENABLED"] = "true"
        os.environ["LICEO_RUN_STARTUP_MIGRATIONS"] = "false"
        with _connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT current_database(), COUNT(*) FROM reservations")
            current_database, _records = cur.fetchone()
            if current_database != database:
                raise RuntimeError("Integration tests are not connected to the disposable database.")

    def setUp(self):
        with _connection() as conn, conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                "TRUNCATE payment_transactions,reservation_availability_deliveries,"
                "reservation_availability_events,reservation_inventory_allocations,"
                "payments,billing,reservation_items,reservations,inventory_item_sizes,"
                "inventory_items,parent_notifications,student_notifications,parent_student,"
                "enrollments,school_years,users,branches RESTART IDENTITY CASCADE"
            )
            self.ids = self._insert_fixture(cur)

    @staticmethod
    def _one(cur, query, params=()):
        cur.execute(query, params)
        return cur.fetchone()

    def _insert_fixture(self, cur):
        branch = self._one(
            cur,
            "INSERT INTO branches (branch_name,branch_code) VALUES ('Test Branch','PFT') RETURNING branch_id",
        )["branch_id"]
        other_branch = self._one(
            cur,
            "INSERT INTO branches (branch_name,branch_code) VALUES ('Other Branch','PFO') RETURNING branch_id",
        )["branch_id"]
        year = self._one(
            cur,
            "INSERT INTO school_years (label,branch_id,is_active) VALUES ('2099-2100',%s,TRUE) RETURNING year_id",
            (branch,),
        )["year_id"]
        other_year = self._one(
            cur,
            "INSERT INTO school_years (label,branch_id,is_active) VALUES ('2099-2100',%s,TRUE) RETURNING year_id",
            (other_branch,),
        )["year_id"]

        users = {}
        for key, username, role, user_branch in (
            ("cashier", "pf_cashier", "cashier", branch),
            ("librarian", "pf_librarian", "librarian", branch),
            ("student1", "pf_student_1", "student", branch),
            ("student2", "pf_student_2", "student", branch),
            ("parent", "pf_parent", "parent", branch),
            ("other_cashier", "pf_other_cashier", "cashier", other_branch),
        ):
            users[key] = self._one(
                cur,
                "INSERT INTO users (branch_id,username,password,role,full_name) "
                "VALUES (%s,%s,'test-only',%s,%s) RETURNING user_id",
                (user_branch, username, role, username),
            )["user_id"]

        enrollments = {}
        for key, user_key, user_branch, year_id, number in (
            ("student1", "student1", branch, year, 9001),
            ("student2", "student2", branch, year, 9002),
        ):
            enrollments[key] = self._one(
                cur,
                "INSERT INTO enrollments (branch_id,user_id,year_id,branch_enrollment_no,"
                "grade_level,status,student_first_name,student_last_name) "
                "VALUES (%s,%s,%s,%s,'Grade 7','approved',%s,'Student') "
                "RETURNING enrollment_id",
                (user_branch, users[user_key], year_id, number, key.title()),
            )["enrollment_id"]
            cur.execute(
                "UPDATE users SET enrollment_id=%s,grade_level='Grade 7' WHERE user_id=%s",
                (enrollments[key], users[user_key]),
            )
        cur.execute(
            "INSERT INTO parent_student (parent_id,student_id) VALUES (%s,%s),(%s,%s)",
            (
                users["parent"], enrollments["student1"],
                users["parent"], enrollments["student2"],
            ),
        )

        bills = {}
        for key in ("student1", "student2"):
            bills[key] = self._one(
                cur,
                "INSERT INTO billing (enrollment_id,branch_id,tuition_fee,books_fee,"
                "total_amount,amount_paid,balance,status,created_by,year_id) "
                "VALUES (%s,%s,1000,0,1000,0,1000,'pending',%s,%s) RETURNING bill_id",
                (enrollments[key], branch, users["cashier"], year),
            )["bill_id"]

        items = {}
        for key, name, price, stock in (
            ("book1", "Payment First Book One", Decimal("100.00"), 5),
            ("book2", "Payment First Book Two", Decimal("200.00"), 3),
            ("final", "Final Copy Book", Decimal("300.00"), 1),
            ("zero", "Unpriced Book", Decimal("0.00"), 5),
            ("negative", "Negative Price Book", Decimal("-1.00"), 5),
            ("out", "Visible Out Of Stock Book", Decimal("150.00"), 0),
        ):
            items[key] = self._one(
                cur,
                "INSERT INTO inventory_items (branch_id,category,item_name,grade_level,"
                "is_common,price,stock_total,reserved_qty,is_active) "
                "VALUES (%s,'BOOK',%s,'Grade 7',TRUE,%s,%s,0,TRUE) RETURNING item_id",
                (branch, name, price, stock),
            )["item_id"]
        return {
            "branch": branch,
            "other_branch": other_branch,
            "year": year,
            "other_year": other_year,
            "users": users,
            "enrollments": enrollments,
            "bills": bills,
            "items": items,
        }

    def _make_reservations(self, student, selections):
        ids = self.ids
        with _connection() as conn, conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            lines = []
            for item_key, qty in selections:
                cur.execute(
                    "SELECT item_id,price FROM inventory_items WHERE item_id=%s FOR UPDATE",
                    (ids["items"][item_key],),
                )
                item = cur.fetchone()
                lines.append({
                    "item_id": item["item_id"],
                    "qty": qty,
                    "size_label": None,
                    "unit_price": item["price"],
                    "line_total": item["price"] * qty,
                })
            return create_payment_first_reservations(
                cur,
                book_lines=lines,
                student_user_id=ids["users"][student],
                branch_id=ids["branch"],
                student_grade="Grade 7",
                reserved_by_user_id=ids["users"][student],
                enrollment_id=ids["enrollments"][student],
            )

    def _client(self, role, user_key, enrollment_key=None, branch_key="branch"):
        from app import app

        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
        client = app.test_client()
        with client.session_transaction() as session:
            session["role"] = role
            session["user_id"] = self.ids["users"][user_key]
            session["branch_id"] = self.ids[branch_key]
            session["name"] = user_key
            if enrollment_key:
                session["enrollment_id"] = self.ids["enrollments"][enrollment_key]
        return client

    def _cashier_payment(self, bill_key, reservation_ids, amount, key):
        client = self._client("cashier", "cashier")
        return client.post(
            f"/cashier/process-payment/{self.ids['bills'][bill_key]}",
            data={
                "amount": str(amount),
                "payment_method": "cash",
                "notes": "integration test",
                "target_type": "reservation_batch",
                "target_id": "",
                "reservation_ids": ",".join(str(value) for value in reservation_ids),
                "idempotency_key": key,
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

    def test_student_checkout_creates_one_reservation_per_book_without_hold(self):
        client = self._client("student", "student1", "student1")
        single = client.post(
            "/reservation",
            data={f"qty_{self.ids['items']['book1']}": "1"},
        )
        self.assertEqual(single.status_code, 302)
        self.assertIn("success_ids=", single.location)
        response = client.post(
            "/reservation",
            data={
                f"qty_{self.ids['items']['book1']}": "1",
                f"qty_{self.ids['items']['book2']}": "2",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("success_ids=", response.location)
        with _connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*),COUNT(DISTINCT r.reservation_id),MIN(lines),MAX(lines) "
                "FROM (SELECT r.reservation_id,COUNT(ri.*) lines FROM reservations r "
                "JOIN reservation_items ri USING(reservation_id) GROUP BY r.reservation_id) r"
            )
            self.assertEqual(cur.fetchone(), (3, 3, 1, 1))
            cur.execute("SELECT SUM(reserved_qty) FROM inventory_items")
            self.assertEqual(cur.fetchone()[0], 0)

    def test_student_quantity_invalid_price_and_unpaid_cancellation(self):
        client = self._client("student", "student1", "student1")
        invalid = client.post(
            "/reservation", data={f"qty_{self.ids['items']['book1']}": "4"}
        )
        self.assertEqual(invalid.status_code, 200)
        zero = client.post(
            "/reservation", data={f"qty_{self.ids['items']['zero']}": "1"}
        )
        self.assertEqual(zero.status_code, 200)
        negative = client.post(
            "/reservation", data={f"qty_{self.ids['items']['negative']}": "1"}
        )
        self.assertEqual(negative.status_code, 200)
        unavailable = client.post(
            "/reservation", data={f"qty_{self.ids['items']['out']}": "1"}
        )
        self.assertEqual(unavailable.status_code, 200)
        reservation_id = self._make_reservations("student1", [("book1", 1)])[0]
        cancelled = client.post(f"/reservations/{reservation_id}/cancel")
        self.assertEqual(cancelled.status_code, 302)
        with _connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT status FROM reservations WHERE reservation_id=%s", (reservation_id,))
            self.assertEqual(cur.fetchone()[0], "CANCELLED")
            cur.execute(
                "SELECT stock_total,reserved_qty FROM inventory_items WHERE item_id=%s",
                (self.ids["items"]["book1"],),
            )
            self.assertEqual(cur.fetchone(), (5, 0))

    def test_cashier_full_combined_receipt_partial_general_and_duplicate_safety(self):
        reservations = self._make_reservations(
            "student1", [("book1", 1), ("book2", 1)]
        )
        partial = self._cashier_payment(
            "student1", reservations, "100.00", "partial_request_123456"
        )
        self.assertEqual(partial.status_code, 400)
        general = self._client("cashier", "cashier").post(
            f"/cashier/process-payment/{self.ids['bills']['student1']}",
            data={
                "amount": "50.00", "payment_method": "cash",
                "target_type": "general", "target_id": "",
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(general.status_code, 400)
        with _connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM reservation_availability_events")
            self.assertEqual(cur.fetchone()[0], 0)
        paid = self._cashier_payment(
            "student1", reservations, "300.00", "combined_request_123456"
        )
        self.assertEqual(paid.status_code, 200)
        payload = paid.get_json()
        self.assertEqual(len(payload["receipt"]["items"]), 2)
        duplicate = self._cashier_payment(
            "student1", reservations, "300.00", "combined_request_123456"
        )
        self.assertEqual(duplicate.status_code, 200)
        with _connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*),SUM(total_amount) FROM payment_transactions")
            self.assertEqual(cur.fetchone(), (1, Decimal("300.00")))
            cur.execute(
                "SELECT COUNT(*),COUNT(receipt_number),SUM(amount) FROM payments "
                "WHERE transaction_id IS NOT NULL"
            )
            self.assertEqual(cur.fetchone(), (2, 0, Decimal("300.00")))
            cur.execute("SELECT COUNT(*) FROM reservation_inventory_allocations")
            self.assertEqual(cur.fetchone()[0], 2)

    def test_insufficient_stock_rolls_back_every_payment_record(self):
        reservation = self._make_reservations("student1", [("final", 1)])[0]
        with _connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE inventory_items SET stock_total=0 WHERE item_id=%s",
                (self.ids["items"]["final"],),
            )
        response = self._cashier_payment(
            "student1", [reservation], "300.00", "shortage_request_123456"
        )
        self.assertEqual(response.status_code, 409)
        with _connection() as conn, conn.cursor() as cur:
            for table in ("payment_transactions", "payments", "reservation_inventory_allocations"):
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                self.assertEqual(cur.fetchone()[0], 0)
            cur.execute("SELECT status FROM reservations WHERE reservation_id=%s", (reservation,))
            self.assertEqual(cur.fetchone()[0], "RESERVED")

    def test_final_copy_concurrency_notifications_restock_and_claim_once(self):
        first = self._make_reservations("student1", [("final", 1)])[0]
        second = self._make_reservations("student2", [("final", 1)])[0]
        barrier = threading.Barrier(2)
        outcomes = []
        outcome_lock = threading.Lock()

        def pay(student, reservation, key):
            conn = _connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            try:
                barrier.wait(timeout=10)
                cur.execute("SELECT * FROM billing WHERE bill_id=%s FOR UPDATE", (self.ids["bills"][student],))
                bill = cur.fetchone()
                process_payment_first_batch(
                    cur,
                    bill=bill,
                    reservation_ids=[reservation],
                    amount=Decimal("300.00"),
                    payment_method="cash",
                    notes="concurrency",
                    received_by=self.ids["users"]["cashier"],
                    idempotency_key=key,
                )
                conn.commit()
                with _connection() as notify_conn, notify_conn.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor
                ) as notify_cur:
                    record_newly_unavailable(
                        notify_cur,
                        branch_id=self.ids["branch"],
                        paid_reservation_ids=[reservation],
                    )
                result = ("paid", reservation)
            except PaymentFirstInventoryUnavailable as exc:
                conn.rollback()
                with _connection() as notify_conn, notify_conn.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor
                ) as notify_cur:
                    record_unavailable_reservations(
                        notify_cur,
                        branch_id=self.ids["branch"],
                        reservation_ids=exc.reservation_ids,
                    )
                result = ("shortage", reservation)
            finally:
                cur.close()
                conn.close()
            with outcome_lock:
                outcomes.append(result)

        threads = [
            threading.Thread(target=pay, args=("student1", first, "race_request_student1")),
            threading.Thread(target=pay, args=("student2", second, "race_request_student2")),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(sorted(result[0] for result in outcomes), ["paid", "shortage"])
        winner = next(result[1] for result in outcomes if result[0] == "paid")

        with _connection() as conn, conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute("SELECT stock_total,reserved_qty FROM inventory_items WHERE item_id=%s", (self.ids["items"]["final"],))
            self.assertEqual(tuple(cur.fetchone().values()), (1, 1))
            cur.execute("SELECT COUNT(*) FROM payment_transactions")
            self.assertEqual(cur.fetchone()["count"], 1)
            cur.execute("SELECT COUNT(*) FROM student_notifications WHERE title LIKE '%Unavailable%'")
            self.assertEqual(cur.fetchone()["count"], 1)
            cur.execute("SELECT COUNT(*) FROM parent_notifications WHERE title LIKE '%Unavailable%'")
            self.assertEqual(cur.fetchone()["count"], 1)
            record_unavailable_reservations(
                cur,
                branch_id=self.ids["branch"],
                reservation_ids=[result[1] for result in outcomes if result[0] == "shortage"],
            )
            cur.execute("SELECT COUNT(*) FROM student_notifications WHERE title LIKE '%Unavailable%'")
            self.assertEqual(cur.fetchone()["count"], 1)
            cur.execute("UPDATE inventory_items SET stock_total=stock_total+1 WHERE item_id=%s", (self.ids["items"]["final"],))
            self.assertEqual(resolve_available_events(cur, branch_id=self.ids["branch"], item_id=self.ids["items"]["final"]), 1)
            self.assertEqual(resolve_available_events(cur, branch_id=self.ids["branch"], item_id=self.ids["items"]["final"]), 0)
            cur.execute("SELECT COUNT(*) FROM student_notifications WHERE title LIKE '%Available Again%'")
            self.assertEqual(cur.fetchone()["count"], 1)
            cur.execute("SELECT COUNT(*) FROM parent_notifications WHERE title LIKE '%Available Again%'")
            self.assertEqual(cur.fetchone()["count"], 1)

        with _connection() as conn, conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            reservation = lock_reservation(cur, winner, self.ids["branch"])
            claim_inventory(
                cur,
                reservation,
                legacy_settlement=require_verified_direct_settlement,
                legacy_deduct=deduct_reserved_inventory,
            )
            cur.execute(
                "UPDATE reservations SET status='CLAIMED',claimed_at=NOW() "
                "WHERE reservation_id=%s AND status='PAID'",
                (winner,),
            )
        with _connection() as conn, conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            reservation = lock_reservation(cur, winner, self.ids["branch"])
            with self.assertRaises(PaymentFirstError):
                claim_inventory(
                    cur,
                    reservation,
                    legacy_settlement=require_verified_direct_settlement,
                    legacy_deduct=deduct_reserved_inventory,
                )
            conn.rollback()
            cur.execute("SELECT stock_total,reserved_qty FROM inventory_items WHERE item_id=%s", (self.ids["items"]["final"],))
            self.assertEqual(tuple(cur.fetchone().values()), (1, 0))

    def test_legacy_claim_cancel_receipt_and_branch_isolation(self):
        ids = self.ids
        with _connection() as conn, conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                "UPDATE inventory_items SET reserved_qty=2 WHERE item_id=%s",
                (ids["items"]["book1"],),
            )
            legacy_paid = self._one(
                cur,
                "INSERT INTO reservations (student_user_id,branch_id,student_grade_level,status,"
                "reserved_by_user_id,enrollment_id,inventory_policy) "
                "VALUES (%s,%s,'Grade 7','PAID',%s,%s,NULL) RETURNING reservation_id",
                (ids["users"]["student1"], ids["branch"], ids["users"]["student1"], ids["enrollments"]["student1"]),
            )["reservation_id"]
            cur.execute(
                "INSERT INTO reservation_items (reservation_id,item_id,qty,unit_price,line_total) "
                "VALUES (%s,%s,1,100,100)",
                (legacy_paid, ids["items"]["book1"]),
            )
            cur.execute(
                "INSERT INTO payments (bill_id,enrollment_id,branch_id,amount,payment_method,"
                "receipt_number,received_by,year_id,target_type,target_id) "
                "VALUES (%s,%s,%s,100,'cash','OR-LEGACY-KEEP',%s,%s,'reservation',%s)",
                (ids["bills"]["student1"], ids["enrollments"]["student1"], ids["branch"], ids["users"]["cashier"], ids["year"], legacy_paid),
            )
            legacy_cancel = self._one(
                cur,
                "INSERT INTO reservations (student_user_id,branch_id,status,reserved_by_user_id,"
                "enrollment_id,inventory_policy) VALUES (%s,%s,'RESERVED',%s,%s,NULL) RETURNING reservation_id",
                (ids["users"]["student1"], ids["branch"], ids["users"]["student1"], ids["enrollments"]["student1"]),
            )["reservation_id"]
            cur.execute(
                "INSERT INTO reservation_items (reservation_id,item_id,qty,unit_price,line_total) VALUES (%s,%s,1,100,100)",
                (legacy_cancel, ids["items"]["book1"]),
            )

        with _connection() as conn, conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            paid = lock_reservation(cur, legacy_paid, ids["branch"])
            claim_inventory(cur, paid, legacy_settlement=require_verified_direct_settlement, legacy_deduct=deduct_reserved_inventory)
            cur.execute("UPDATE reservations SET status='CLAIMED' WHERE reservation_id=%s", (legacy_paid,))
            cancellable = lock_reservation_for_cancellation(cur, legacy_cancel, ids["branch"])
            self.assertTrue(cancel_inventory(cur, cancellable, release_reserved_inventory))
            cur.execute("UPDATE reservations SET status='CANCELLED' WHERE reservation_id=%s", (legacy_cancel,))
            cur.execute("SELECT stock_total,reserved_qty FROM inventory_items WHERE item_id=%s", (ids["items"]["book1"],))
            self.assertEqual(tuple(cur.fetchone().values()), (4, 0))
            cur.execute("SELECT receipt_number FROM payments WHERE target_id=%s", (legacy_paid,))
            self.assertEqual(cur.fetchone()["receipt_number"], "OR-LEGACY-KEEP")

        history = self._client("student", "student1", "student1").get(
            "/student/reservations"
        )
        self.assertEqual(history.status_code, 200)
        self.assertIn(str(legacy_paid).encode(), history.data)

        other = self._client("cashier", "other_cashier", branch_key="other_branch")
        denied = other.post(
            f"/cashier/process-payment/{ids['bills']['student1']}",
            data={"amount": "100", "target_type": "general", "target_id": ""},
        )
        self.assertEqual(denied.status_code, 302)
        with _connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM payments WHERE receipt_number <> 'OR-LEGACY-KEEP' OR receipt_number IS NULL")
            self.assertEqual(cur.fetchone()[0], 0)

    def test_rendered_student_parent_cashier_and_librarian_pages(self):
        reservation = self._make_reservations("student1", [("book1", 1)])[0]
        pages = [
            self._client("student", "student1", "student1").get("/reservation"),
            self._client("student", "student1", "student1").get("/student/reservations"),
            self._client("parent", "parent").get("/parent/reservations"),
            self._client("cashier", "cashier").get(f"/cashier/bill/{self.ids['bills']['student1']}"),
            self._client("librarian", "librarian").get("/librarian/releases"),
        ]
        self.assertEqual([response.status_code for response in pages], [200, 200, 200, 200, 200])
        self.assertIn(b"Payment First Book One", pages[0].data)
        self.assertNotIn(b"Unpriced Book", pages[0].data)
        self.assertNotIn(b"Negative Price Book", pages[0].data)
        self.assertIn(b"Visible Out Of Stock Book", pages[0].data)
        self.assertIn(b"Out of Stock", pages[0].data)
        self.assertIn(str(reservation).encode(), pages[1].data)


if __name__ == "__main__":
    unittest.main()
