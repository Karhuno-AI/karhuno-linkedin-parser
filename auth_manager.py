"""AuthManager: управление аутентификацией для LinkedIn через cookies.

Позволяет установить cookies (li_at, JSESSIONID или произвольную cookie-строку)
и применять их к requests.Session и Selenium WebDriver.
"""
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def _parse_cookie_string(cookie_string: str) -> Dict[str, str]:
    cookies: Dict[str, str] = {}
    if not cookie_string:
        return cookies
    parts = [p.strip() for p in cookie_string.split(';') if p.strip()]
    for part in parts:
        if '=' in part:
            name, value = part.split('=', 1)
            cookies[name.strip()] = value.strip()
    return cookies


class AuthManager:
    def __init__(self, _config=None):
        self._cookies: Dict[str, str] = {}

        # Инициализация из переменных окружения, если заданы
        env_cookie = os.environ.get('LINKEDIN_COOKIE', '').strip()
        li_at = os.environ.get('LINKEDIN_LI_AT', '').strip()
        jsid = os.environ.get('LINKEDIN_JSESSIONID', '').strip()

        if env_cookie:
            self.set_cookie_string(env_cookie)
        else:
            base: Dict[str, str] = {}
            if li_at:
                base['li_at'] = li_at
            if jsid:
                # Часто JSESSIONID обрамлен кавычками — удалим их, если есть
                base['JSESSIONID'] = jsid.strip('"')
            if base:
                self.set_cookies(base)

    def has_cookies(self) -> bool:
        return bool(self._cookies)

    def get_sanitized(self) -> Dict[str, bool]:
        # Не логируем значения cookies
        return {k: True for k in self._cookies.keys()}

    def set_cookie_string(self, cookie_string: str) -> None:
        cookies = _parse_cookie_string(cookie_string)
        self.set_cookies(cookies)

    def set_cookies(self, cookies: Dict[str, str]) -> None:
        # Фильтруем только полезные и общие cookie
        self._cookies = dict(cookies or {})
        # Нормализуем JSESSIONID без кавычек
        if 'JSESSIONID' in self._cookies:
            self._cookies['JSESSIONID'] = self._cookies['JSESSIONID'].strip('"')
        logger.info("Auth cookies updated: %s", list(self._cookies.keys()))

    def apply_to_requests_session(self, session) -> None:
        if not self._cookies:
            return
        try:
            for name, value in self._cookies.items():
                # Домен .linkedin.com, путь /
                session.cookies.set(name, value, domain='.linkedin.com', path='/')
        except Exception as e:
            logger.warning("Failed to apply cookies to requests session: %s", e)

    def apply_to_selenium(self, driver) -> None:
        if not self._cookies or driver is None:
            return
        try:
            # Должны сначала открыть домен, чтобы можно было добавлять cookies
            driver.get('https://www.linkedin.com')
            for name, value in self._cookies.items():
                cookie = {
                    'name': name,
                    'value': value,
                    'domain': '.linkedin.com',
                    'path': '/',
                    'secure': True,
                    'httpOnly': False,
                }
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    # Попробуем без domain
                    cookie.pop('domain', None)
                    driver.add_cookie(cookie)
        except Exception as e:
            logger.warning("Failed to apply cookies to selenium: %s", e)
