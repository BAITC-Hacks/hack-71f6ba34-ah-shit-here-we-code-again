"""Small, process-local limits for a password-protected hackathon demo."""
import base64
import binascii
import secrets
import threading
import time


class DemoLimit(Exception):
    pass


class HostingGuard:
    def __init__(self, env):
        self.host = env.get('HOST', '127.0.0.1')
        self.enabled = env.get('PUBLIC_MODE') == '1' or self.host not in ('127.0.0.1', 'localhost', '::1')
        self.code = env.get('DEMO_ACCESS_CODE', '')
        self.daily_limit = int(env.get('OPENAI_DAILY_CALL_LIMIT', '100'))
        self.minute_limit = int(env.get('SESSION_REQUESTS_PER_MINUTE', '6'))
        self.day = None
        self.calls = 0
        self.lock = threading.Lock()

    def validate(self):
        if not self.enabled:
            return
        if len(self.code) < 24 or len(set(self.code)) < 10 or ':' in self.code or any(c.isspace() for c in self.code):
            raise ValueError('Public hosting requires a random DEMO_ACCESS_CODE of at least 24 characters, without spaces or colons.')
        if not 1 <= self.daily_limit <= 1000 or not 1 <= self.minute_limit <= 60:
            raise ValueError('Public demo request limits are outside the allowed range.')

    def authorized(self, header):
        if not self.enabled:
            return True
        if not self.code:
            return False
        try:
            scheme, encoded = header.split(' ', 1)
            if scheme.lower() != 'basic':
                return False
            actual = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            return False
        return secrets.compare_digest(actual, ('jury:' + self.code).encode())

    def reserve_request(self, session, now=None):
        if not self.enabled:
            return
        now = time.monotonic() if now is None else now
        with self.lock:
            recent = [stamp for stamp in session.get('_request_times', []) if now - stamp < 60]
            if len(recent) >= self.minute_limit:
                raise DemoLimit('Слишком много запросов. Подождите минуту и попробуйте снова.')
            session['_request_times'] = recent + [now]

    def reserve_openai_call(self, now=None):
        if not self.enabled:
            return
        day = int((time.time() if now is None else now) // 86400)
        with self.lock:
            if day != self.day:
                self.day, self.calls = day, 0
            if self.calls >= self.daily_limit:
                raise DemoLimit('Достигнут дневной лимит ИИ для демонстрации. Поиск по каталогу и корзина доступны.')
            # Reserve before sending, including calls which subsequently fail.
            self.calls += 1
