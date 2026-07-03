import unittest
from types import SimpleNamespace

from app.api_client import JijiaApiClient
from app.auth import AccessToken


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"code": 200, "data": {"rows": []}}


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, json, headers, timeout):
        self.calls.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return FakeResponse()


class JijiaApiClientTimeoutTest(unittest.TestCase):
    def test_api_config_can_override_request_timeout(self):
        settings = SimpleNamespace(
            jijia_base_url="https://example.test",
            jijia_open_gateway_prefix="/api/open",
        )
        client = JijiaApiClient(settings, timeout_seconds=30)
        client.session = FakeSession()

        client.request(
            {
                "api_code": "slow_api",
                "method": "POST",
                "path": "/slow/page",
                "timeout_seconds": 90,
                "params": {"page": 1},
            },
            AccessToken("token"),
        )

        self.assertEqual(client.session.calls[0]["timeout"], 90)


if __name__ == "__main__":
    unittest.main()
