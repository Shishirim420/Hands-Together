"""Tests for administrator registration and access."""

import os
import tempfile
import unittest

from hands_together import create_app


class AdminAuthenticationTests(unittest.TestCase):
    """Verify administrator registration and dashboard authorization."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test.db")
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": self.database_path,
                "SECRET_KEY": "test-secret-key",
            }
        )
        self.client = self.app.test_client()
        self.admin = {
            "name": "Test Admin",
            "phone": "01700000001",
            "email": "test.admin@example.com",
            "accountType": "Admin",
            "password": "correct-password",
            "adminPass": self.app.config["ADMIN_REGISTRATION_PASS"],
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_admin_can_register_and_open_dashboard(self):
        response = self.client.post("/api/signup", json=self.admin)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["accountType"], "Admin")
        self.assertEqual(self.client.get("/admin").status_code, 200)

    def test_admin_login_opens_dashboard(self):
        self.client.post("/api/signup", json=self.admin)
        self.client.post("/api/logout")

        response = self.client.post(
            "/api/login",
            json={"identity": self.admin["email"], "password": self.admin["password"]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["accountType"], "Admin")
        self.assertEqual(self.client.get("/admin").status_code, 200)

    def test_admin_registration_rejects_incorrect_access_phrase(self):
        self.admin["adminPass"] = "incorrect-test-phrase"

        response = self.client.post("/api/signup", json=self.admin)

        self.assertEqual(response.status_code, 403)
        self.assertIn("access phrase is incorrect", response.json["error"])

    def test_non_admin_cannot_open_dashboard(self):
        response = self.client.post(
            "/api/signup",
            json={
                "name": "Test Member",
                "phone": "01700000002",
                "email": "test.member@example.com",
                "accountType": "Community member",
                "password": "correct-password",
            },
        )
        self.assertEqual(response.status_code, 201)

        self.assertEqual(self.client.get("/admin").status_code, 403)


if __name__ == "__main__":
    unittest.main()