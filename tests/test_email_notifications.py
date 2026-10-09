import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from utils import send_email as email_helper


class DummySMTP:
    sent_messages = []
    fail_send = False

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self):
        return None

    def login(self, username, password):
        self.username = username
        self.password = password

    def send_message(self, msg):
        if self.fail_send:
            raise RuntimeError("simulated failure with secret")
        self.sent_messages.append(msg)


class EmailNotificationTest(unittest.TestCase):
    def setUp(self):
        DummySMTP.sent_messages = []
        DummySMTP.fail_send = False

    def test_synchronous_send_returns_true_on_smtp_handoff(self):
        env = {
            "MAIL_USERNAME": "mailer@example.com",
            "MAIL_PASSWORD": "secret-password",
            "MAIL_SERVER": "smtp.example.com",
            "MAIL_PORT": "465",
        }
        with patch.dict(os.environ, env, clear=False), patch("utils.send_email.smtplib.SMTP_SSL", DummySMTP):
            ok = email_helper.send_email("student@example.com", "Subject", "Body", use_background=False)
        self.assertTrue(ok)
        self.assertEqual(len(DummySMTP.sent_messages), 1)

    def test_synchronous_send_returns_false_and_masks_logs_on_failure(self):
        DummySMTP.fail_send = True
        env = {
            "MAIL_USERNAME": "mailer@example.com",
            "MAIL_PASSWORD": "secret-password",
            "MAIL_SERVER": "smtp.example.com",
            "MAIL_PORT": "465",
        }
        out = io.StringIO()
        with patch.dict(os.environ, env, clear=False), \
             patch("utils.send_email.smtplib.SMTP_SSL", DummySMTP), \
             patch("utils.send_email.smtplib.SMTP", DummySMTP), \
             redirect_stdout(out):
            ok = email_helper.send_email("student@example.com", "Subject", "Body", use_background=False)
        log = out.getvalue()
        self.assertFalse(ok)
        self.assertIn("s***t@example.com", log)
        self.assertNotIn("student@example.com", log)
        self.assertNotIn("secret-password", log)
        self.assertNotIn("simulated failure with secret", log)

    def test_missing_credentials_returns_false_and_masks_recipient(self):
        out = io.StringIO()
        with patch.dict(os.environ, {"MAIL_USERNAME": "", "MAIL_PASSWORD": "", "SMTP_USER": "", "SMTP_PASS": ""}, clear=False), redirect_stdout(out):
            ok = email_helper.send_email("parent@example.com", "Subject", "Body", use_background=False)
        log = out.getvalue()
        self.assertFalse(ok)
        self.assertIn("p***t@example.com", log)
        self.assertNotIn("parent@example.com", log)


if __name__ == "__main__":
    unittest.main()
