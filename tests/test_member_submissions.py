"""Tests for member-owned missing-person reports and donations."""

import os
import shutil
import tempfile
import unittest

from hands_together import create_app


class MemberSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": os.path.join(self.temp_dir, "test.db"),
                "SECRET_KEY": "test-secret-key",
                "ADMIN_REGISTRATION_PASS": "test-admin-phrase",
            }
        )
        self.client = self.app.test_client()
        self.member = {
            "name": "Member One",
            "phone": "01700000003",
            "email": "member.one@example.com",
            "accountType": "Community member",
            "password": "correct-password",
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_anonymous_people_cannot_submit_a_donation_or_missing_report(self):
        donation = self.client.post("/api/donations", json={"amount": 500, "method": "bKash"})
        report = self.client.post(
            "/api/reports",
            json={
                "kind": "missing", "title": "Person", "category": "Adult",
                "date": "2026-11-25", "location": "Dhaka", "description": "Test report",
            },
        )

        self.assertEqual(donation.status_code, 401)
        self.assertEqual(report.status_code, 401)

    def test_admin_can_see_the_member_profile_for_a_donation(self):
        self.client.post("/api/signup", json=self.member)
        donation = self.client.post("/api/donations", json={"amount": 500, "method": "bKash"})
        self.assertEqual(donation.status_code, 201)
        self.client.post("/api/logout")
        self.client.post(
            "/api/signup",
            json={
                "name": "Admin One", "phone": "01700000004", "email": "admin.one@example.com",
                "accountType": "Admin", "password": "correct-password", "adminPass": "test-admin-phrase",
            },
        )

        dashboard = self.client.get("/admin")

        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("Member One", dashboard.get_data(as_text=True))
        self.assertIn("01700000003", dashboard.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
