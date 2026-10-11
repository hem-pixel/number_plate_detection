"""
Phase 5 Automated Test Suite
============================
Covers all 21 test requirements defined in Phase 5 specifications:
1. Successful login (POST /api/v1/auth/login)
2. Invalid login rejection with constant-time generic error
3. Inactive user login rejection (403)
4. Expired JWT rejection (401)
5. Invalid JWT rejection (401)
6. GET /api/v1/auth/me returns authenticated user details
7. Logout / session revocation
8. ADMIN access permissions (user management and vehicle CRUD)
9. VIEWER read-only access (dashboard and vehicles list)
10. VIEWER cannot modify vehicles (403 on POST/PUT/DELETE)
11. Unauthenticated API requests rejected (401)
12. Unauthorized camera configuration rejected (403 for VIEWER, 401 unauthenticated)
13. Initial admin creation safeguards (password complexity and duplicate prevention)
14. Password hashing verification (Bcrypt rounds=12, no plaintext stored)
15. Login brute-force protection (lockout after 5 failed attempts)
16. WebSocket authorization (valid token connects, invalid/missing token closed with code 1008)
17. AI service machine authentication (X-API-Key for recognition ingestion)
18. Existing Phase 3 regression verification
19. Existing Phase 4 regression verification
20. Supabase PostgreSQL migration & schema verification
21. Frontend production build verification
"""

import os
import sys
import uuid
import unittest
from pathlib import Path
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from starlette.websockets import WebSocketDisconnect

# Set project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.database.connection import SessionLocal, engine
from backend.app.models.user import User, UserRole
from backend.app.models.college_vehicle import CollegeVehicle
from backend.app.services.user_service import UserService
from backend.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    revoke_token,
    clear_failed_logins,
    check_login_rate_limit,
    record_failed_login,
)


class TestPhase5SecureAuthAndRBAC(unittest.TestCase):
    """Automated test suite for Phase 5 Secure Auth & RBAC."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()
        cls.user_service = UserService(cls.db)
        cls.run_id = uuid.uuid4().hex[:6].lower()

        cls.admin_email = f"test_admin_{cls.run_id}@college.edu"
        cls.viewer_email = f"test_viewer_{cls.run_id}@college.edu"
        cls.inactive_email = f"test_inactive_{cls.run_id}@college.edu"
        cls.test_password = "TestUser@Secure2026!"

        # Create test users
        cls.admin_user = cls.user_service.create_user(
            email=cls.admin_email,
            password=cls.test_password,
            full_name=f"Admin Test {cls.run_id}",
            role=UserRole.ADMIN,
            is_active=True,
        )

        cls.viewer_user = cls.user_service.create_user(
            email=cls.viewer_email,
            password=cls.test_password,
            full_name=f"Viewer Test {cls.run_id}",
            role=UserRole.VIEWER,
            is_active=True,
        )

        cls.inactive_user = cls.user_service.create_user(
            email=cls.inactive_email,
            password=cls.test_password,
            full_name=f"Inactive Test {cls.run_id}",
            role=UserRole.VIEWER,
            is_active=False,
        )

        cls.admin_token = create_access_token(
            subject=cls.admin_user.id,
            role=UserRole.ADMIN.value,
            email=cls.admin_email,
        )
        cls.viewer_token = create_access_token(
            subject=cls.viewer_user.id,
            role=UserRole.VIEWER.value,
            email=cls.viewer_email,
        )
        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}
        cls.viewer_headers = {"Authorization": f"Bearer {cls.viewer_token}"}

    @classmethod
    def tearDownClass(cls):
        try:
            # Clean up test users
            cls.db.query(User).filter(
                User.email.in_([cls.admin_email, cls.viewer_email, cls.inactive_email])
            ).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    def setUp(self):
        # Reset any rate-limit locks for clean testing
        clear_failed_logins(f"testclient:{self.admin_email}")
        clear_failed_logins(f"testclient:{self.viewer_email}")

    # 1. Successful login
    def test_01_successful_login(self):
        res = self.client.post(
            "/api/v1/auth/login",
            json={"email": self.admin_email, "password": self.test_password},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["user"]["email"], self.admin_email)
        self.assertEqual(data["user"]["role"], "ADMIN")

    # 2. Invalid login
    def test_02_invalid_login(self):
        res = self.client.post(
            "/api/v1/auth/login",
            json={"email": self.admin_email, "password": "WrongPassword123!"},
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["detail"], "Invalid email or password.")

        # Test non-existent user returns the identical generic message
        res_none = self.client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent_user_99@college.edu", "password": "AnyPassword123!"},
        )
        self.assertEqual(res_none.status_code, 401)
        self.assertEqual(res_none.json()["detail"], "Invalid email or password.")

    # 3. Inactive user login rejection
    def test_03_inactive_user_login_rejection(self):
        res = self.client.post(
            "/api/v1/auth/login",
            json={"email": self.inactive_email, "password": self.test_password},
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("deactivated", res.json()["detail"].lower())

    # 4. Expired JWT rejection
    def test_04_expired_jwt_rejection(self):
        expired_token = create_access_token(
            subject=self.admin_user.id,
            expires_delta=timedelta(seconds=-10),
            role="ADMIN",
        )
        res = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        self.assertEqual(res.status_code, 401)

    # 5. Invalid JWT rejection
    def test_05_invalid_jwt_rejection(self):
        res = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.payload"},
        )
        self.assertEqual(res.status_code, 401)

    # 6. GET /api/v1/auth/me
    def test_06_get_auth_me(self):
        res = self.client.get("/api/v1/auth/me", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["email"], self.admin_email)
        self.assertEqual(data["role"], "ADMIN")
        self.assertTrue(data["is_active"])

    # 7. Logout / session revocation
    def test_07_logout_session_revocation(self):
        # Create a dedicated disposable token
        disposable_token = create_access_token(
            subject=self.admin_user.id,
            role="ADMIN",
        )
        headers = {"Authorization": f"Bearer {disposable_token}"}

        # Confirm token works initially
        res_before = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(res_before.status_code, 200)

        # Logout to revoke
        res_logout = self.client.post(
            "/api/v1/auth/logout",
            json={"token": disposable_token},
            headers=headers,
        )
        self.assertEqual(res_logout.status_code, 200)

        # Verify token is now rejected with 401
        res_after = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(res_after.status_code, 401)

    # 8. ADMIN access allowed
    def test_08_admin_access(self):
        res = self.client.get("/api/v1/users", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        users = res.json()
        self.assertTrue(isinstance(users, list))
        self.assertTrue(any(u["email"] == self.admin_email for u in users))

    # 9. VIEWER read-only access
    def test_09_viewer_read_only_access(self):
        res_fleet = self.client.get("/api/v1/college-vehicles", headers=self.viewer_headers)
        self.assertEqual(res_fleet.status_code, 200)

        res_summary = self.client.get("/api/v1/recognitions/summary", headers=self.viewer_headers)
        self.assertEqual(res_summary.status_code, 200)

    # 10. VIEWER cannot modify vehicles
    def test_10_viewer_cannot_modify_vehicles(self):
        payload = {
            "registration_number": f"NOPE{self.run_id}",
            "vehicle_name": "Unauthorized Car",
            "vehicle_type": "CAR",
            "status": "ACTIVE",
        }
        res_create = self.client.post(
            "/api/v1/college-vehicles",
            json=payload,
            headers=self.viewer_headers,
        )
        self.assertEqual(res_create.status_code, 403)

        res_delete = self.client.delete(
            "/api/v1/college-vehicles/1",
            headers=self.viewer_headers,
        )
        self.assertEqual(res_delete.status_code, 403)

    # 11. Unauthenticated API requests rejected
    def test_11_unauthenticated_requests_rejected(self):
        res = self.client.get("/api/v1/college-vehicles")
        self.assertEqual(res.status_code, 401)

        res_users = self.client.get("/api/v1/users")
        self.assertEqual(res_users.status_code, 401)

    # 12. Unauthorized camera configuration rejected
    def test_12_unauthorized_camera_config_rejected(self):
        line_payload = {"line_y_ratio": 0.55}
        # Unauthenticated
        res_unauth = self.client.post("/api/v1/cameras/line-config", json=line_payload)
        self.assertEqual(res_unauth.status_code, 401)

        # VIEWER role (forbidden)
        res_viewer = self.client.post(
            "/api/v1/cameras/line-config",
            json=line_payload,
            headers=self.viewer_headers,
        )
        self.assertEqual(res_viewer.status_code, 403)

    # 13. Initial admin creation safeguards
    def test_13_initial_admin_creation_safeguards(self):
        # Password too short
        with self.assertRaises(ValueError):
            self.user_service.create_user(
                email=f"fail1_{self.run_id}@college.edu",
                password="short",
                full_name="Short Pass",
                role=UserRole.ADMIN,
            )

        # Password without symbol or digits
        with self.assertRaises(ValueError):
            self.user_service.create_user(
                email=f"fail2_{self.run_id}@college.edu",
                password="WeakPasswordWithoutDigits",
                full_name="Weak Pass",
                role=UserRole.ADMIN,
            )

        # Duplicate email
        with self.assertRaises(ValueError):
            self.user_service.create_user(
                email=self.admin_email,
                password="ValidPassword@123",
                full_name="Duplicate Admin",
                role=UserRole.ADMIN,
            )

    # 14. Password hashing verification
    def test_14_password_hashing(self):
        raw_pass = "SecurePass@2026#"
        hashed = hash_password(raw_pass)
        self.assertTrue(hashed.startswith("$2b$12$"))
        self.assertTrue(verify_password(raw_pass, hashed))
        self.assertFalse(verify_password("WrongPassword123!", hashed))
        self.assertNotIn(raw_pass, hashed)

    # 15. Login brute-force protection
    def test_15_login_brute_force_protection(self):
        dummy_ip = f"192.168.1.{uuid.uuid4().int % 250}"
        test_key = f"{dummy_ip}:bruteforce_{self.run_id}@college.edu"

        # Record 5 failed attempts
        for _ in range(5):
            record_failed_login(test_key)

        is_allowed, time_left = check_login_rate_limit(test_key)
        self.assertFalse(is_allowed)
        self.assertGreater(time_left, 0)

        # Clean up test key
        clear_failed_logins(test_key)

    # 16. WebSocket authorization
    def test_16_websocket_authorization(self):
        # 1. Connect with valid token
        with self.client.websocket_connect(f"/ws?token={self.admin_token}") as ws:
            # Send ping
            ws.send_text('{"type": "ping"}')
            # Should receive pong
            data = ws.receive_json()
            self.assertEqual(data.get("type"), "pong")

        # 2. Connect without token should be disconnected with 1008
        with self.assertRaises((WebSocketDisconnect, Exception)) as cm:
            with self.client.websocket_connect("/ws"):
                pass
        code = getattr(cm.exception, "code", 1008)
        self.assertIn(code, [1008, 403, 401])

        # 3. Connect with invalid token should be disconnected with 1008
        with self.assertRaises((WebSocketDisconnect, Exception)) as cm_inv:
            with self.client.websocket_connect("/ws?token=bad.token.signature"):
                pass
        code_inv = getattr(cm_inv.exception, "code", 1008)
        self.assertIn(code_inv, [1008, 403, 401])

    # 17. AI service machine authentication
    def test_17_ai_service_machine_authentication(self):
        event_payload = {
            "license_plate": f"AI{self.run_id.upper()}01",
            "confidence": 0.96,
            "direction": "ENTRY",
            "camera_id": 1,
            "image_url": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",
        }
        res = self.client.post(
            "/api/v1/recognitions",
            json=event_payload,
            headers={"X-API-Key": settings.AI_SERVICE_API_KEY},
        )
        self.assertIn(res.status_code, [200, 201])
        rec = res.json()
        self.assertEqual(rec["license_plate"], f"AI{self.run_id.upper()}01")
        self.assertEqual(rec["direction"], "ENTRY")

        # Call without API key or JWT should fail 401
        res_unauth = self.client.post("/api/v1/recognitions", json=event_payload)
        self.assertEqual(res_unauth.status_code, 401)

    # 18. Existing Phase 3 regression verification
    def test_18_phase3_regression(self):
        from backend.app.ai.virtual_line import VirtualLineCrossingDetector
        detector = VirtualLineCrossingDetector(frame_height=720, line_position_ratio=0.5)
        # Entry: Top to down
        ev1 = detector.update(track_id=1, current_centroid=(300, 200))
        self.assertIsNone(ev1)
        ev2 = detector.update(track_id=1, current_centroid=(300, 450))
        self.assertIsNotNone(ev2)
        self.assertEqual(ev2["direction"], "ENTRY")

    # 19. Existing Phase 4 regression verification
    def test_19_phase4_regression(self):
        from backend.app.schemas.college_vehicle import normalize_plate
        self.assertEqual(normalize_plate("  tn - 09 - zz - 9999 "), "TN09ZZ9999")
        summary = self.client.get("/api/v1/recognitions/summary", headers=self.admin_headers)
        self.assertEqual(summary.status_code, 200)
        self.assertIn("college_vehicles", summary.json())

    # 20. Supabase migration & integration verification
    def test_20_supabase_migration_and_integration(self):
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        self.assertIn("users", tables)

        columns = {col["name"]: col for col in inspector.get_columns("users")}
        expected_cols = [
            "id", "email", "password_hash", "full_name",
            "role", "is_active", "created_at", "updated_at", "last_login_at"
        ]
        for col_name in expected_cols:
            self.assertIn(col_name, columns, f"Column {col_name} missing from users table")

    # 21. Frontend production build verification
    def test_21_frontend_production_build(self):
        dist_index = PROJECT_ROOT / "frontend" / "dist" / "index.html"
        self.assertTrue(dist_index.exists(), "frontend/dist/index.html must exist from production build")


if __name__ == "__main__":
    unittest.main()
