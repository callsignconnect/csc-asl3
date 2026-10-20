import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Ansible" / "files"))
import backend


class RealtimePayloadTests(unittest.TestCase):
    def test_encoding_round_trip(self):
        fields = {"id": "X1CSC@example.org", "password": "a&b=c+d %/", "empty": ""}
        encoded = backend.encode_realtime_payload(fields)
        self.assertEqual(
            parse_qs(encoded, keep_blank_values=True, strict_parsing=True),
            {key: [value] for key, value in fields.items()},
        )
        self.assertEqual(backend.encode_realtime_payload({}), "")

    def test_endpoint_settings(self):
        response = asyncio.run(backend.pjsip_realtime_endpoint(id="X1CSC", headers=None))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            parse_qs(response.body.decode(), strict_parsing=True),
            {key: [value] for key, value in {
                "id": "X1CSC", "type": "endpoint", "context": "from-webrtc",
                "allow": "ulaw", "auth": "auth_X1CSC", "webrtc": "yes",
                "use_avpf": "yes", "rtcp_mux": "yes", "media_encryption": "dtls",
                "dtls_verify": "no", "dtls_setup": "actpass",
                "dtls_auto_generate_cert": "yes", "media_use_received_transport": "yes",
                "rtp_symmetric": "yes", "force_rport": "yes", "direct_media": "no",
                "rtp_keepalive": "1", "timers": "required", "timers_min_se": "90",
                "send_connected_line": "yes",
            }.items()},
        )

    def test_unknown_and_missing_endpoint(self):
        for endpoint_id in ("UNKNOWN", None):
            response = asyncio.run(
                backend.pjsip_realtime_endpoint(id=endpoint_id, headers=None)
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.body, b"")

    def test_auth_password_is_escaped(self):
        with patch.object(backend, "csc_placeholder", {"password": "a&b=c+d %/"}):
            response = asyncio.run(backend.pjsip_realtime_auth(id="auth_X1CSC"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            parse_qs(response.body.decode(), strict_parsing=True),
            {"id": ["auth_X1CSC"], "auth_type": ["md5"],
             "username": ["X1CSC"], "password": ["a&b=c+d %/"]},
        )


if __name__ == "__main__":
    unittest.main()
