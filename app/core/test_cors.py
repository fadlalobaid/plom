"""Tests for the application's browser CORS policy."""

import unittest

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


class CorsMiddlewareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.allowed_origin = get_settings().cors_origins[0]
        self.disallowed_origin = "https://unconfigured-origin.invalid"
        while self.disallowed_origin in get_settings().cors_origins:
            self.disallowed_origin = f"https://not-{self.disallowed_origin}"

    def tearDown(self) -> None:
        self.client.close()

    def test_allowed_origin_receives_cors_headers(self) -> None:
        response = self.client.get(
            "/health",
            headers={"Origin": self.allowed_origin},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            self.allowed_origin,
        )
        self.assertEqual(
            response.headers["access-control-allow-credentials"],
            "true",
        )

    def test_disallowed_origin_is_not_granted_cors_access(self) -> None:
        response = self.client.get(
            "/health",
            headers={"Origin": self.disallowed_origin},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_preflight_allows_authorization_header(self) -> None:
        response = self.client.options(
            "/health",
            headers={
                "Origin": self.allowed_origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            self.allowed_origin,
        )
        self.assertIn(
            "authorization",
            response.headers["access-control-allow-headers"].lower(),
        )


if __name__ == "__main__":
    unittest.main()
