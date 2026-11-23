"""tests for sign-up and login."""

import os
import shutil
import tempfile
import unittest

from hands_together import create_app


class AuthenticationTests(unittest.TestCase):
    """Verify that users can sign up and log in safely."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.database_path = os.path.join(self.temp_dir, "test.db")
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": self.database_path,
                "SECRET_KEY": "test-secret-key",
            }
        )
        self.client = self.app.test_client()
        self.user = {
            "name": "Test User",
            "phone": "01700000000",
            "email": "test.user@example.com",
            "accountType": "Community member",
            "password": "correct-password",
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def signup_user(self):
        return self.client.post("/api/signup", json=self.user)

    def test_signup_creates_a_new_user(self):
        response = self.signup_user()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["name"], self.user["name"])
        self.assertEqual(response.json["accountType"], "Community member")

    def test_signup_rejects_duplicate_email_or_phone(self):
        self.signup_user()
        response = self.signup_user()

        self.assertEqual(response.status_code, 409)
        self.assertIn("already registered", response.json["error"])

    def test_login_accepts_correct_credentials(self):
        self.signup_user()
        self.client.post("/api/logout")

        response = self.client.post(
            "/api/login",
            json={"identity": self.user["email"], "password": self.user["password"]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["name"], self.user["name"])

    def test_login_rejects_an_incorrect_password(self):
        self.signup_user()
        self.client.post("/api/logout")

        response = self.client.post(
            "/api/login",
            json={"identity": self.user["email"], "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("incorrect", response.json["error"])


if __name__ == "__main__":
    unittest.main()
