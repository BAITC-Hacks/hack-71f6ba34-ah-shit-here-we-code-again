import base64
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPResponse
import io
import json
import unittest
from unittest.mock import patch

from hosting_guard import HostingGuard, DemoLimit
import server


CODE = 'test-only-ExampleCode_8127394065'


def public_guard(**overrides):
    return HostingGuard({'HOST': '0.0.0.0', 'DEMO_ACCESS_CODE': CODE, **overrides})


class HostingConfigurationTests(unittest.TestCase):
    def test_public_binding_requires_strong_access_code(self):
        for code in ('', 'short', 'a' * 30, 'a long sentence with spaces!123'):
            with self.subTest(code_length=len(code)), self.assertRaises(ValueError):
                public_guard(DEMO_ACCESS_CODE=code).validate()
        public_guard().validate()
        local = HostingGuard({})
        local.validate()
        self.assertEqual(local.host, '127.0.0.1')
        self.assertTrue(local.authorized(''))

    def test_minute_budget_is_session_specific_and_expires(self):
        guard = public_guard(SESSION_REQUESTS_PER_MINUTE='2')
        first, other = {}, {}
        guard.reserve_request(first, now=0)
        guard.reserve_request(first, now=1)
        with self.assertRaises(DemoLimit):
            guard.reserve_request(first, now=59)
        guard.reserve_request(other, now=59)
        guard.reserve_request(first, now=60)
        self.assertEqual(len(first['_request_times']), 2)

    def test_daily_budget_counts_concurrent_calls_and_resets_on_next_utc_day(self):
        guard = public_guard(OPENAI_DAILY_CALL_LIMIT='3')
        def reserve(_):
            try:
                guard.reserve_openai_call(now=1)
                return True
            except DemoLimit:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(reserve, range(12))), 3)
        guard.reserve_openai_call(now=86400)
        self.assertEqual(guard.calls, 1)

    def test_exhausted_budget_prevents_network_call(self):
        guard = public_guard(OPENAI_DAILY_CALL_LIMIT='1')
        guard.reserve_openai_call()
        with patch.object(server, 'hosting_guard', guard), patch.object(server.urllib.request, 'urlopen') as network:
            with self.assertRaises(DemoLimit):
                server.fetch_json('https://api.openai.com/v1/responses', body={})
            network.assert_not_called()


class HostedHTTPTests(unittest.TestCase):
    def setUp(self):
        self.guard = public_guard(SESSION_REQUESTS_PER_MINUTE='1')
        self.patch = patch.object(server, 'hosting_guard', self.guard)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def request(self, path, method='GET', auth=None, body=None, headers=None):
        request_headers = dict(headers or {})
        if auth is not None:
            request_headers['Authorization'] = auth
        payload = (body or '').encode()
        if payload:
            request_headers['Content-Length'] = str(len(payload))
        wire = (method + ' ' + path + ' HTTP/1.0\r\n' + ''.join(
            key + ': ' + value + '\r\n' for key, value in request_headers.items()) + '\r\n').encode() + payload

        class MemorySocket:
            def __init__(self, incoming):
                self.incoming = incoming
                self.outgoing = io.BytesIO()
            def makefile(self, *args):
                return io.BytesIO(self.incoming)
            def sendall(self, data):
                self.outgoing.write(data)

        connection = MemorySocket(wire)
        server.Handler(connection, ('127.0.0.1', 1), None)
        response = HTTPResponse(MemorySocket(connection.outgoing.getvalue()))
        response.begin()
        return response.status, dict(response.getheaders()), response.read()

    def credentials(self, username='jury', password=CODE):
        return 'Basic ' + base64.b64encode((username + ':' + password).encode()).decode()

    def test_ui_and_post_are_protected_before_session_creation(self):
        before = len(server.sessions)
        for path, method in (('/', 'GET'), ('/app.js', 'GET'), ('/api/status', 'GET'), ('/api/chat', 'POST')):
            status, headers, _ = self.request(path, method)
            self.assertEqual(status, 401)
            self.assertIn('Basic realm=', headers['WWW-Authenticate'])
            self.assertNotIn('Set-Cookie', headers)
        self.assertEqual(len(server.sessions), before)

    def test_wrong_and_malformed_credentials_are_rejected(self):
        for auth in ('Basic !!!', 'Bearer xxx', self.credentials(password='wrong'), self.credentials(username='admin')):
            self.assertEqual(self.request('/api/status', auth=auth)[0], 401)

    def test_valid_auth_creates_secure_cookie(self):
        status, headers, body = self.request('/api/status', auth=self.credentials())
        self.assertEqual(status, 200)
        self.assertIn('csrf', json.loads(body))
        for attribute in ('; Secure', '; HttpOnly', '; SameSite=Strict'):
            self.assertIn(attribute, headers['Set-Cookie'])
        self.assertNotIn(CODE.encode(), body)

    def test_health_probe_reveals_only_liveness_without_session(self):
        status, headers, body = self.request('/healthz')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {'ok': True})
        self.assertNotIn('Set-Cookie', headers)

    def test_expensive_request_limit_returns_429_with_retry_hint(self):
        auth = self.credentials()
        _, headers, body = self.request('/api/status', auth=auth)
        request_headers = {'Cookie': headers['Set-Cookie'].split(';')[0],
                           'X-CSRF-Token': json.loads(body)['csrf'], 'Content-Type': 'application/json'}
        payload = json.dumps({'message': 'Минимальная сумма заказа?'})
        self.assertEqual(self.request('/api/chat', 'POST', auth, payload, request_headers)[0], 200)
        status, headers, body = self.request('/api/chat', 'POST', auth, payload, request_headers)
        self.assertEqual(status, 429)
        self.assertEqual(headers['Retry-After'], '60')
        self.assertIn('минуту', json.loads(body)['error'])
