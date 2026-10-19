import unittest

from flask import Flask, redirect, request, session, url_for

from utils.auth_sessions import (
    AUTH_SESSION_KEY,
    enforce_active_auth_session,
    issue_auth_session,
    revoke_current_auth_session,
)


class FakeSessionStore:
    def __init__(self):
        self.sessions = {}

    def connect(self):
        return FakeConnection(self)


class FakeConnection:
    def __init__(self, store):
        self.store = store

    def cursor(self):
        return FakeCursor(self.store)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class FakeCursor:
    def __init__(self, store):
        self.store = store
        self.result = None

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split()).upper()
        self.result = None
        if normalized.startswith("INSERT INTO AUTH_SESSIONS"):
            session_hash, user_id, _lifetime = params
            self.store.sessions[session_hash] = {
                "user_id": user_id,
                "revoked": False,
                "expired": False,
                "idle": False,
            }
        elif "SET LAST_SEEN_AT = NOW()" in normalized:
            session_hash, user_id, _idle_timeout = params
            record = self.store.sessions.get(session_hash)
            if (
                record
                and record["user_id"] == user_id
                and not record["revoked"]
                and not record["expired"]
                and not record["idle"]
            ):
                self.result = (session_hash,)
        elif "SET REVOKED_AT = COALESCE" in normalized:
            session_hash, user_id = params
            record = self.store.sessions.get(session_hash)
            if record and record["user_id"] == user_id:
                record["revoked"] = True
        else:
            raise AssertionError(f"Unexpected SQL in fake session store: {normalized}")

    def fetchone(self):
        return self.result

    def close(self):
        pass


def build_test_app(store):
    app = Flask(__name__)
    app.secret_key = "test-only-session-secret"
    app.config.update(
        TESTING=True,
        AUTH_SESSION_ABSOLUTE_LIFETIME_SECONDS=86400,
    )

    @app.before_request
    def validate_server_session():
        return enforce_active_auth_session(
            db_factory=store.connect,
            idle_timeout_seconds=3600,
            login_endpoint="login",
        )

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return "login"
        role = request.form.get("role", "teacher")
        roles = request.form.getlist("roles") or [role]
        session.clear()
        session.permanent = True
        session["user_id"] = 42
        session["role"] = role
        session["roles"] = roles
        db = store.connect()
        cursor = db.cursor()
        issue_auth_session(cursor, 42)
        db.commit()
        cursor.close()
        db.close()
        return "logged-in"

    @app.route("/logout", methods=["POST"])
    def logout():
        if not revoke_current_auth_session(db_factory=store.connect):
            return "unavailable", 503
        session.clear()
        return "logged-out"

    @app.route("/protected")
    def protected():
        return f"protected:{session['role']}"

    @app.route("/switch-role", methods=["POST"])
    def switch_role():
        target_role = request.form["role"]
        if target_role not in session.get("roles", []):
            return "forbidden", 403
        session["role"] = target_role
        return target_role

    return app


class AuthSessionRevocationTests(unittest.TestCase):
    def setUp(self):
        self.store = FakeSessionStore()
        self.app = build_test_app(self.store)
        self.client = self.app.test_client()

    def login(self, client=None, role="teacher", roles=None):
        client = client or self.client
        data = {"role": role}
        if roles:
            data["roles"] = roles
        response = client.post("/login", data=data)
        self.assertEqual(response.status_code, 200)
        return client.get_cookie("session").value

    def test_logout_revokes_restored_cookie_and_new_login_uses_new_id(self):
        old_cookie = self.login()
        self.assertEqual(self.client.get("/protected").status_code, 200)

        response = self.client.post("/logout")
        self.assertEqual(response.status_code, 200)

        self.client.set_cookie("session", old_cookie)
        replay = self.client.get("/protected", follow_redirects=False)
        self.assertEqual(replay.status_code, 302)
        self.assertTrue(replay.headers["Location"].endswith("/login"))

        new_cookie = self.login()
        self.assertNotEqual(old_cookie, new_cookie)
        self.assertEqual(self.client.get("/protected").status_code, 200)

    def test_only_current_concurrent_session_is_revoked(self):
        first = self.app.test_client()
        second = self.app.test_client()
        self.login(first)
        self.login(second)

        self.assertEqual(first.post("/logout").status_code, 200)
        self.assertEqual(second.get("/protected").status_code, 200)

    def test_role_switch_keeps_same_server_session(self):
        self.login(role="teacher", roles=["teacher", "parent"])
        with self.client.session_transaction() as current:
            original_session_id = current[AUTH_SESSION_KEY]

        switched = self.client.post("/switch-role", data={"role": "parent"})
        self.assertEqual(switched.status_code, 200)
        with self.client.session_transaction() as current:
            self.assertEqual(current[AUTH_SESSION_KEY], original_session_id)
        self.assertEqual(self.client.get("/protected").data, b"protected:parent")

    def test_missing_revoked_expired_and_idle_sessions_are_rejected(self):
        self.login()
        with self.client.session_transaction() as current:
            raw_session_id = current[AUTH_SESSION_KEY]

        from utils.auth_sessions import _hash_session_id

        record = self.store.sessions[_hash_session_id(raw_session_id)]
        for state in ("revoked", "expired", "idle"):
            with self.subTest(state=state):
                record[state] = True
                response = self.client.get("/protected", follow_redirects=False)
                self.assertEqual(response.status_code, 302)
                record[state] = False
                self.login()
                with self.client.session_transaction() as current:
                    raw_session_id = current[AUTH_SESSION_KEY]
                record = self.store.sessions[_hash_session_id(raw_session_id)]

        with self.client.session_transaction() as current:
            current.pop(AUTH_SESSION_KEY)
        response = self.client.get("/protected", follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        with self.client.session_transaction() as current:
            current.clear()
            current["role"] = "teacher"
        response = self.client.get("/protected", follow_redirects=False)
        self.assertEqual(response.status_code, 302)

    def test_all_existing_account_roles_can_hold_valid_sessions(self):
        roles = (
            "teacher",
            "student",
            "parent",
            "registrar",
            "cashier",
            "librarian",
            "branch_admin",
            "super_admin",
        )
        for role in roles:
            with self.subTest(role=role):
                client = self.app.test_client()
                self.login(client, role=role)
                response = client.get("/protected")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, f"protected:{role}".encode())


if __name__ == "__main__":
    unittest.main()
