"""Модуль для парсинга профилей LinkedIn"""
import requests
import re
import json
import logging
import time
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from config import Config
from proxy_manager import ProxyManager
from rate_limiter import RateLimiter
from session_manager import SessionManager

logger = logging.getLogger(__name__)

# Попытаемся импортировать браузерный парсер
try:
    from browser_parser import BrowserParser
    BROWSER_PARSER_AVAILABLE = True
except ImportError:
    BROWSER_PARSER_AVAILABLE = False
    logger.warning("BrowserParser не доступен - браузерный парсинг отключен")

class LinkedInParser:
    """Класс для парсинга профилей LinkedIn"""
    
    def __init__(self, config: Config, proxy_manager: ProxyManager, rate_limiter: RateLimiter, session_manager: SessionManager = None):
        """
        Инициализация LinkedInParser
        
        Args:
            config: Объект конфигурации
            proxy_manager: Менеджер прокси
            rate_limiter: Лимитер запросов
            session_manager: Менеджер сессий (опционально)
        """
        self.config = config
        self.proxy_manager = proxy_manager
        self.rate_limiter = rate_limiter
        self.session_manager = session_manager or SessionManager(config)
        self.base_url = config.get('linkedin.base_url', 'https://www.linkedin.com')
        self.timeout = config.get('linkedin.timeout', 30)
        self.max_retries = config.get('linkedin.max_retries', 3)
        self.retry_delay = config.get('linkedin.retry_delay', 5)
        self.user_agents = config.get('user_agents', [])
        
        # Инициализируем браузерный парсер для обхода 999 ошибок
        self.browser_parser = None
        if BROWSER_PARSER_AVAILABLE:
            try:
                self.browser_parser = BrowserParser(config)
                logger.info("BrowserParser успешно инициализирован для обхода блокировок")
            except Exception as e:
                logger.warning(f"Ошибка инициализации BrowserParser: {e}")
    
    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Загрузка страницы профиля с использованием session manager
        
        Args:
            url: URL профиля
            
        Returns:
            BeautifulSoup объект или None при ошибке
        """
        self.rate_limiter.wait()
        
        for attempt in range(self.max_retries):
            try:
                # Получаем прокси
                proxy = self.proxy_manager.get_proxy()
                
                # Получаем сессию с ротацией
                session = self.session_manager.rotate_session()
                
                start_time = time.time()
                
                logger.info(f"Загрузка страницы: {url} (попытка {attempt + 1}/{self.max_retries})")
                logger.info(f"Используемый прокси: {proxy if proxy else 'Нет (прямое соединение)'}")
                logger.info(f"User-Agent: {session.headers.get('User-Agent', 'Не указан')}")
                
                # Используем сессию вместо requests.get
                response = session.get(
                    url,
                    proxies=proxy,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                response_time = time.time() - start_time
                
                logger.info(f"Получен ответ: статус {response.status_code}, размер {len(response.content)} байт, время {response_time:.2f}s")
                logger.info(f"Финальный URL после редиректов: {response.url}")
                logger.info(f"Заголовки ответа: {dict(response.headers)}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    logger.info("Страница успешно загружена")
                    logger.info(f"Размер HTML: {len(response.text)} символов")
                    
                    # Отмечаем успешное использование прокси
                    self.proxy_manager.mark_success(proxy, response_time)
                    
                    # Проверяем, что это действительно страница профиля
                    if 'linkedin.com' not in response.url.lower():
                        logger.warning(f"Возможный редирект на другую страницу: {response.url}")
                    return soup
                elif response.status_code == 403:
                    logger.warning(f"Доступ запрещен (403). LinkedIn блокирует запросы.")
                    logger.warning(f"Содержимое ответа (первые 500 символов): {response.text[:500]}")
                    logger.warning(f"Cookies в ответе: {dict(response.cookies)}")
                    
                    # Помечаем прокси как неработающий
                    if proxy:
                        logger.info(f"Прокси помечен как неработающий: {proxy}")
                        self.proxy_manager.mark_failed(proxy)
                    
                    # Очищаем cookies в сессии и обновляем User-Agent
                    self.session_manager.clear_cookies()
                    self.session_manager.rotate_user_agent()
                    
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay
                        logger.info(f"Ожидание {wait_time} секунд перед следующей попыткой...")
                        time.sleep(wait_time)
                        continue
                    return None
                elif response.status_code == 404:
                    logger.error("Профиль не найден (404)")
                    logger.error(f"Содержимое ответа: {response.text[:500]}")
                    return None
                elif response.status_code == 999:
                    logger.warning(f"LinkedIn блокирует запросы (999). Это защита от автоматизированного доступа.")
                    logger.warning(f"Содержимое ответа (первые 1000 символов): {response.text[:1000]}")
                    logger.warning(f"URL после редиректа: {response.url}")
                    
                    # Помечаем прокси как неработающий
                    if proxy:
                        logger.info(f"Прокси помечен как неработающий: {proxy}")
                        self.proxy_manager.mark_failed(proxy)
                    
                    # Если это последняя попытка и браузер доступен, пробуем браузерный парсинг
                    if attempt == self.max_retries - 1 and self.browser_parser:
                        logger.info("Переходим на браузерный парсинг для обхода блокировки...")
                        browser_html = self.browser_parser.fetch_profile(url, timeout=self.timeout)
                        if browser_html and not self.browser_parser.check_blockage():
                            logger.info("✓ Браузерный парсинг успешен!")
                            soup = BeautifulSoup(browser_html, 'html.parser')
                            return soup
                        else:
                            logger.warning("✗ Браузерный парсинг также заблокирован")
                            return None
                    
                    # Создаем новую сессию полностью
                    self.session_manager.create_new_session_for_ip(proxy.replace('http://', '') if proxy else 'unknown')
                    
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * 2
                        logger.info(f"Ожидание {wait_time} секунд перед следующей попыткой (увеличенная задержка для 999)...")
                        time.sleep(wait_time)
                        continue
                    return None
                elif response.status_code == 429:
                    logger.warning(f"Слишком много запросов (429). Rate limit превышен.")
                    retry_after = response.headers.get('Retry-After', 'не указан')
                    logger.warning(f"Retry-After заголовок: {retry_after}")
                    
                    # Помечаем прокси как неработающий
                    if proxy:
                        self.proxy_manager.mark_failed(proxy)
                    
                    # Очищаем все сессии и создаем новую
                    self.session_manager.clear_all_sessions()
                    
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * 3
                        logger.info(f"Ожидание {wait_time} секунд перед следующей попыткой (увеличенная задержка для 429)...")
                        time.sleep(wait_time)
                        continue
                    return None
                else:
                    logger.warning(f"Неожиданный статус код: {response.status_code}")
                    logger.warning(f"Содержимое ответа (первые 500 символов): {response.text[:500]}")
                    logger.warning(f"URL после редиректа: {response.url}")
                    
                    if proxy:
                        logger.info(f"Прокси помечен как неработающий: {proxy}")
                        self.proxy_manager.mark_failed(proxy)
                    
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay
                        logger.info(f"Ожидание {wait_time} секунд перед следующей попыткой...")
                        time.sleep(wait_time)
                        continue
                    return None
                    
            except requests.exceptions.InvalidURL as e:
                logger.error(f"Неверный URL прокси: {e}")
                logger.error(f"Прокси, вызвавший ошибку: {proxy}")
                if proxy:
                    self.proxy_manager.mark_failed(proxy)
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay
                    logger.info(f"Повторная попытка через {wait_time} секунд...")
                    time.sleep(wait_time)
                    continue
            except requests.exceptions.Timeout as e:
                logger.error(f"Таймаут запроса: {e}")
                logger.error(f"URL: {url}, таймаут: {self.timeout} секунд, прокси: {proxy if proxy else 'Нет'}")
                if proxy:
                    self.proxy_manager.mark_failed(proxy)
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay
                    logger.info(f"Повторная попытка через {wait_time} секунд...")
                    time.sleep(wait_time)
                    continue
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Ошибка соединения: {e}")
                logger.error(f"Прокси: {proxy if proxy else 'Нет'}, URL: {url}")
                if proxy:
                    self.proxy_manager.mark_failed(proxy)
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay
                    logger.info(f"Повторная попытка через {wait_time} секунд...")
                    time.sleep(wait_time)
                    continue
            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка запроса: {type(e).__name__}: {e}")
                logger.error(f"Детали ошибки: {str(e)}")
                logger.error(f"Прокси: {proxy if proxy else 'Нет'}")
                if proxy:
                    self.proxy_manager.mark_failed(proxy)
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay
                    logger.info(f"Повторная попытка через {wait_time} секунд...")
                    time.sleep(wait_time)
                    continue
            except Exception as e:
                logger.error(f"Неожиданная ошибка: {type(e).__name__}: {e}")
                import traceback
                logger.error(f"Трассировка: {traceback.format_exc()}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay
                    logger.info(f"Повторная попытка через {wait_time} секунд...")
                    time.sleep(wait_time)
                    continue
        
        return None
    
    def _extract_public_identifier(self, url: str) -> Optional[str]:
        """Извлечение publicIdentifier из URL"""
        # Формат: https://www.linkedin.com/in/username
        match = re.search(r'/in/([^/?]+)', url)
        if match:
            return match.group(1)
        return None
    
    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Извлечение JSON-LD данных из страницы"""
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and '@type' in data:
                    return data
            except:
                continue
        return None
    
    def _extract_meta_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Извлечение метаданных из страницы"""
        meta_data = {}
        
        # Извлечение из meta тегов
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            property_attr = meta.get('property') or meta.get('name')
            content = meta.get('content')
            
            if property_attr and content:
                meta_data[property_attr] = content
        
        return meta_data
    
    def _extract_basic_info(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Извлечение базовой информации профиля"""
        info = {
            'id': None,
            'publicIdentifier': self._extract_public_identifier(url),
            'linkedinUrl': url,
            'firstName': None,
            'lastName': None,
            'headline': None,
            'about': None,
            'photo': None,
            'location': None
        }
        
        # Извлечение из мета-тегов (Open Graph, Twitter Cards)
        meta_data = self._extract_meta_data(soup)
        
        # Извлечение имени из мета-тегов
        if 'og:title' in meta_data:
            title_text = meta_data['og:title']
            if '|' in title_text:
                name_part = title_text.split('|')[0].strip()
                name_parts = name_part.split()
                if len(name_parts) >= 2:
                    info['firstName'] = name_parts[0]
                    info['lastName'] = ' '.join(name_parts[1:])
        
        # Извлечение из заголовка страницы
        title = soup.find('title')
        if title and not info['firstName']:
            title_text = title.get_text(strip=True)
            # Формат: "Имя Фамилия | LinkedIn"
            if '|' in title_text:
                name_part = title_text.split('|')[0].strip()
                name_parts = name_part.split()
                if len(name_parts) >= 2:
                    info['firstName'] = name_parts[0]
                    info['lastName'] = ' '.join(name_parts[1:])
        
        # Извлечение заголовка (headline) из мета-тегов
        if 'og:description' in meta_data:
            info['headline'] = meta_data['og:description']
        else:
            # Поиск в HTML
            headline_elem = soup.find('div', class_=re.compile(r'text-headline|pv-text-details__left-panel|top-card-layout__headline', re.I))
            if not headline_elem:
                headline_elem = soup.find('h2', class_=re.compile(r'headline|top-card-layout__headline', re.I))
            if not headline_elem:
                headline_elem = soup.find('div', {'data-generated-suggestion-target': True})
            if headline_elem:
                info['headline'] = headline_elem.get_text(strip=True)
        
        # Извлечение фото из мета-тегов
        if 'og:image' in meta_data:
            info['photo'] = meta_data['og:image']
        else:
            # Поиск в HTML
            photo_elem = soup.find('img', class_=re.compile(r'profile-photo|pv-profile-photo|top-card-profile-picture', re.I))
            if not photo_elem:
                photo_elem = soup.find('img', {'alt': re.compile(r'profile|photo', re.I)})
            if photo_elem:
                photo_url = photo_elem.get('src') or photo_elem.get('data-delayed-url')
                if photo_url:
                    info['photo'] = photo_url
        
        # Поиск локации
        location_elem = soup.find('span', class_=re.compile(r'location|text-body-small|top-card__subline-item', re.I))
        if not location_elem:
            location_elem = soup.find('div', class_=re.compile(r'location', re.I))
        if location_elem:
            location_text = location_elem.get_text(strip=True)
            if location_text:
                info['location'] = {'linkedinText': location_text}
        
        # Поиск секции "О себе"
        about_section = soup.find('section', {'id': re.compile(r'about', re.I)})
        if not about_section:
            about_section = soup.find('div', class_=re.compile(r'about|summary', re.I))
        if about_section:
            about_text = about_section.get_text(strip=True, separator='\n')
            # Удаляем лишние пробелы и переносы
            about_text = re.sub(r'\n\s*\n', '\n\n', about_text).strip()
            if about_text:
                info['about'] = about_text
        
        # Попытка извлечь ID из JSON данных в script тегах
        scripts = soup.find_all('script', type='application/json')
        for script in scripts:
            try:
                if script.string:
                    data = json.loads(script.string)
                    # Поиск ID профиля в различных структурах
                    if isinstance(data, dict):
                        # Различные возможные пути к ID
                        possible_paths = [
                            ['data', 'entityUrn'],
                            ['profile', 'id'],
                            ['profileData', 'id']
                        ]
                        for path in possible_paths:
                            current = data
                            try:
                                for key in path:
                                    current = current[key]
                                if current:
                                    # Извлекаем ID из URN если нужно
                                    if isinstance(current, str) and ':' in current:
                                        parts = current.split(':')
                                        if len(parts) > 0:
                                            info['id'] = parts[-1]
                                    else:
                                        info['id'] = str(current)
                                    break
                            except (KeyError, TypeError):
                                continue
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return info
    
    def _extract_experience(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Извлечение опыта работы"""
        experience = []
        
        # Поиск секции опыта
        experience_section = soup.find('section', {'id': re.compile(r'experience', re.I)})
        if not experience_section:
            experience_section = soup.find('div', class_=re.compile(r'experience|work-experience', re.I))
        
        if experience_section:
            # Поиск всех позиций - различные возможные селекторы
            positions = experience_section.find_all('li', class_=re.compile(r'experience|position', re.I))
            if not positions:
                positions = experience_section.find_all('div', class_=re.compile(r'position|experience-item|pv-entity', re.I))
            
            for pos in positions:
                exp_item = {
                    'position': None,
                    'companyName': None,
                    'duration': None,
                    'description': None,
                    'location': None,
                    'startDate': None,
                    'endDate': None,
                    'employmentType': None,
                    'workplaceType': None
                }
                
                # Извлечение должности
                title_elem = pos.find('h3') or pos.find('h2') or pos.find('span', class_=re.compile(r'title|position', re.I))
                if not title_elem:
                    title_elem = pos.find('div', class_=re.compile(r'title', re.I))
                if title_elem:
                    exp_item['position'] = title_elem.get_text(strip=True)
                
                # Извлечение названия компании
                company_elem = pos.find('span', class_=re.compile(r'company|organization', re.I))
                if not company_elem:
                    company_elem = pos.find('h4', class_=re.compile(r'company', re.I))
                if not company_elem:
                    company_elem = pos.find('a', class_=re.compile(r'company', re.I))
                if company_elem:
                    exp_item['companyName'] = company_elem.get_text(strip=True)
                
                # Извлечение периода работы
                duration_elem = pos.find('span', class_=re.compile(r'duration|date-range|time', re.I))
                if not duration_elem:
                    duration_elem = pos.find('h4', class_=re.compile(r'date', re.I))
                if duration_elem:
                    duration_text = duration_elem.get_text(strip=True)
                    exp_item['duration'] = duration_text
                    # Попытка парсинга дат
                    date_match = re.search(r'(\w+)\s+(\d{4})\s*[-–]\s*(\w+)?\s*(\d{4})?', duration_text)
                    if date_match:
                        start_month, start_year = date_match.group(1), date_match.group(2)
                        end_month = date_match.group(3)
                        end_year = date_match.group(4)
                        exp_item['startDate'] = {'month': start_month, 'year': int(start_year), 'text': f"{start_month} {start_year}"}
                        if end_year:
                            if end_month:
                                exp_item['endDate'] = {'month': end_month, 'year': int(end_year), 'text': f"{end_month} {end_year}"}
                            else:
                                exp_item['endDate'] = {'year': int(end_year), 'text': end_year}
                        else:
                            exp_item['endDate'] = {'text': 'Present'}
                
                # Извлечение описания
                desc_elem = pos.find('div', class_=re.compile(r'description|summary', re.I))
                if desc_elem:
                    desc_text = desc_elem.get_text(strip=True, separator='\n')
                    desc_text = re.sub(r'\n\s*\n', '\n\n', desc_text).strip()
                    exp_item['description'] = desc_text
                
                # Извлечение локации
                location_elem = pos.find('span', class_=re.compile(r'location', re.I))
                if location_elem:
                    exp_item['location'] = location_elem.get_text(strip=True)
                
                if exp_item['position'] or exp_item['companyName']:
                    experience.append(exp_item)
        
        return experience
    
    def _extract_education(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Извлечение образования"""
        education = []
        
        education_section = soup.find('section', {'id': re.compile(r'education', re.I)})
        if not education_section:
            education_section = soup.find('div', class_=re.compile(r'education', re.I))
        
        if education_section:
            schools = education_section.find_all('li', class_=re.compile(r'education|school', re.I))
            if not schools:
                schools = education_section.find_all('div', class_=re.compile(r'school|education-item|pv-entity', re.I))
            
            for school in schools:
                edu_item = {
                    'schoolName': None,
                    'degree': None,
                    'fieldOfStudy': None,
                    'startDate': None,
                    'endDate': None,
                    'period': None
                }
                
                # Название учебного заведения
                school_name_elem = school.find('h3') or school.find('h2') or school.find('span', class_=re.compile(r'school|university', re.I))
                if not school_name_elem:
                    school_name_elem = school.find('a', class_=re.compile(r'school', re.I))
                if school_name_elem:
                    edu_item['schoolName'] = school_name_elem.get_text(strip=True)
                
                # Степень
                degree_elem = school.find('span', class_=re.compile(r'degree', re.I))
                if not degree_elem:
                    degree_elem = school.find('h4', class_=re.compile(r'degree', re.I))
                if degree_elem:
                    degree_text = degree_elem.get_text(strip=True)
                    # Разделяем степень и специальность
                    if ',' in degree_text:
                        parts = degree_text.split(',', 1)
                        edu_item['degree'] = parts[0].strip()
                        edu_item['fieldOfStudy'] = parts[1].strip()
                    else:
                        edu_item['degree'] = degree_text
                
                # Период обучения
                period_elem = school.find('span', class_=re.compile(r'date|period|time', re.I))
                if period_elem:
                    period_text = period_elem.get_text(strip=True)
                    edu_item['period'] = period_text
                    # Парсинг дат
                    date_match = re.search(r'(\w+)?\s*(\d{4})\s*[-–]\s*(\w+)?\s*(\d{4})?', period_text)
                    if date_match:
                        start_month = date_match.group(1)
                        start_year = date_match.group(2)
                        end_month = date_match.group(3)
                        end_year = date_match.group(4)
                        
                        if start_month:
                            edu_item['startDate'] = {'month': start_month, 'year': int(start_year), 'text': f"{start_month} {start_year}"}
                        else:
                            edu_item['startDate'] = {'year': int(start_year), 'text': start_year}
                        
                        if end_year:
                            if end_month:
                                edu_item['endDate'] = {'month': end_month, 'year': int(end_year), 'text': f"{end_month} {end_year}"}
                            else:
                                edu_item['endDate'] = {'year': int(end_year), 'text': end_year}
                
                if edu_item['schoolName']:
                    education.append(edu_item)
        
        return education
    
    def _extract_skills(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Извлечение навыков"""
        skills = []
        
        skills_section = soup.find('section', {'id': re.compile(r'skills', re.I)})
        if not skills_section:
            skills_section = soup.find('div', class_=re.compile(r'skills', re.I))
        
        if skills_section:
            skill_items = skills_section.find_all('li', class_=re.compile(r'skill', re.I))
            if not skill_items:
                skill_items = skills_section.find_all('span', class_=re.compile(r'skill', re.I))
            
            for skill_item in skill_items:
                skill_name_elem = skill_item.find('span') or skill_item.find('a')
                if skill_name_elem:
                    skill_name = skill_name_elem.get_text(strip=True)
                    if skill_name:
                        skills.append({'name': skill_name})
        
        return skills
    
    def _extract_certifications(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Извлечение сертификатов"""
        certifications = []
        
        cert_section = soup.find('section', {'id': re.compile(r'licenses|certifications', re.I)})
        if not cert_section:
            cert_section = soup.find('div', class_=re.compile(r'certification', re.I))
        
        if cert_section:
            cert_items = cert_section.find_all('li', class_=re.compile(r'certification', re.I))
            if not cert_items:
                cert_items = cert_section.find_all('div', class_=re.compile(r'certification', re.I))
            
            for cert_item in cert_items:
                cert = {
                    'title': None,
                    'issuedAt': None,
                    'issuedBy': None,
                    'issuedByLink': None
                }
                
                title_elem = cert_item.find('h3') or cert_item.find('span', class_=re.compile(r'title', re.I))
                if title_elem:
                    cert['title'] = title_elem.get_text(strip=True)
                
                issuer_elem = cert_item.find('span', class_=re.compile(r'issuer|organization', re.I))
                if issuer_elem:
                    cert['issuedBy'] = issuer_elem.get_text(strip=True)
                
                date_elem = cert_item.find('span', class_=re.compile(r'date', re.I))
                if date_elem:
                    cert['issuedAt'] = date_elem.get_text(strip=True)
                
                if cert['title']:
                    certifications.append(cert)
        
        return certifications
    
    def _extract_projects(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Извлечение проектов"""
        projects = []
        
        projects_section = soup.find('section', {'id': re.compile(r'projects', re.I)})
        if not projects_section:
            projects_section = soup.find('div', class_=re.compile(r'project', re.I))
        
        if projects_section:
            project_items = projects_section.find_all('li', class_=re.compile(r'project', re.I))
            if not project_items:
                project_items = projects_section.find_all('div', class_=re.compile(r'project', re.I))
            
            for project_item in project_items:
                project = {
                    'title': None,
                    'description': None,
                    'duration': None,
                    'startDate': None,
                    'endDate': None
                }
                
                title_elem = project_item.find('h3') or project_item.find('span', class_=re.compile(r'title', re.I))
                if title_elem:
                    project['title'] = title_elem.get_text(strip=True)
                
                desc_elem = project_item.find('div', class_=re.compile(r'description', re.I))
                if desc_elem:
                    project['description'] = desc_elem.get_text(strip=True)
                
                date_elem = project_item.find('span', class_=re.compile(r'date', re.I))
                if date_elem:
                    duration_text = date_elem.get_text(strip=True)
                    project['duration'] = duration_text
                    # Парсинг дат
                    date_match = re.search(r'(\w+)\s+(\d{4})\s*[-–]\s*(\w+)?\s*(\d{4})?', duration_text)
                    if date_match:
                        start_month, start_year = date_match.group(1), date_match.group(2)
                        end_month = date_match.group(3)
                        end_year = date_match.group(4)
                        project['startDate'] = {'month': start_month, 'year': int(start_year), 'text': f"{start_month} {start_year}"}
                        if end_year:
                            if end_month:
                                project['endDate'] = {'month': end_month, 'year': int(end_year), 'text': f"{end_month} {end_year}"}
                            else:
                                project['endDate'] = {'year': int(end_year), 'text': end_year}
                
                if project['title']:
                    projects.append(project)
        
        return projects
    
    def _extract_volunteering(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Извлечение волонтерства"""
        volunteering = []
        
        vol_section = soup.find('section', {'id': re.compile(r'volunteering', re.I)})
        if not vol_section:
            vol_section = soup.find('div', class_=re.compile(r'volunteer', re.I))
        
        if vol_section:
            vol_items = vol_section.find_all('li', class_=re.compile(r'volunteer', re.I))
            if not vol_items:
                vol_items = vol_section.find_all('div', class_=re.compile(r'volunteer', re.I))
            
            for vol_item in vol_items:
                vol = {
                    'role': None,
                    'duration': None,
                    'organizationName': None,
                    'organizationLinkedinUrl': None,
                    'cause': None,
                    'startDate': None,
                    'endDate': None
                }
                
                role_elem = vol_item.find('h3') or vol_item.find('span', class_=re.compile(r'role', re.I))
                if role_elem:
                    vol['role'] = role_elem.get_text(strip=True)
                
                org_elem = vol_item.find('span', class_=re.compile(r'organization', re.I))
                if org_elem:
                    vol['organizationName'] = org_elem.get_text(strip=True)
                
                date_elem = vol_item.find('span', class_=re.compile(r'date', re.I))
                if date_elem:
                    vol['duration'] = date_elem.get_text(strip=True)
                
                if vol['role'] or vol['organizationName']:
                    volunteering.append(vol)
        
        return volunteering
    
    def _extract_languages(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Извлечение языков"""
        languages = []
        
        lang_section = soup.find('section', {'id': re.compile(r'languages', re.I)})
        if not lang_section:
            lang_section = soup.find('div', class_=re.compile(r'language', re.I))
        
        if lang_section:
            lang_items = lang_section.find_all('li', class_=re.compile(r'language', re.I))
            if not lang_items:
                lang_items = lang_section.find_all('div', class_=re.compile(r'language', re.I))
            
            for lang_item in lang_items:
                lang = {
                    'name': None,
                    'proficiency': None
                }
                
                name_elem = lang_item.find('h3') or lang_item.find('span', class_=re.compile(r'name', re.I))
                if name_elem:
                    lang['name'] = name_elem.get_text(strip=True)
                
                prof_elem = lang_item.find('span', class_=re.compile(r'proficiency', re.I))
                if prof_elem:
                    lang['proficiency'] = prof_elem.get_text(strip=True)
                
                if lang['name']:
                    languages.append(lang)
        
        return languages
    
    def parse_profile(self, url: str) -> Dict[str, Any]:
        """
        Парсинг профиля LinkedIn
        
        Args:
            url: URL профиля
            
        Returns:
            Словарь с данными профиля в требуемом формате
        """
        logger.info(f"Начало парсинга профиля: {url}")
        
        # Нормализация URL
        if not url.startswith('http'):
            url = f"{self.base_url}/in/{url}" if not url.startswith('/') else f"{self.base_url}{url}"
        
        # Загрузка страницы
        soup = self._fetch_page(url)
        
        if not soup:
            logger.error("Не удалось загрузить страницу профиля после всех попыток")
            logger.error(f"URL: {url}, попыток: {self.max_retries}")
            return {
                'element': {},
                'status': 'error',
                'error': 'Failed to load profile page',
                'errorDetails': {
                    'message': 'LinkedIn блокирует запросы или профиль недоступен. Возможные причины: профиль приватный, LinkedIn блокирует автоматизированные запросы (статус 999), или проблемы с прокси.',
                    'url': url,
                    'attempts': self.max_retries,
                    'suggestions': [
                        'Проверьте, что профиль публичный',
                        'Попробуйте позже (LinkedIn может временно блокировать IP)',
                        'Используйте авторизованный доступ для полных данных',
                        'Проверьте логи для детальной информации об ошибках'
                    ]
                }
            }
        
        # Извлечение базовой информации
        basic_info = self._extract_basic_info(soup, url)
        
        # Извлечение опыта работы
        experience = self._extract_experience(soup)
        
        # Извлечение образования
        education = self._extract_education(soup)
        
        # Извлечение дополнительных данных
        skills = self._extract_skills(soup)
        certifications = self._extract_certifications(soup)
        projects = self._extract_projects(soup)
        volunteering = self._extract_volunteering(soup)
        languages = self._extract_languages(soup)
        
        # Формирование структуры данных
        profile_data = {
            'element': {
                'id': basic_info.get('id'),
                'publicIdentifier': basic_info.get('publicIdentifier'),
                'linkedinUrl': basic_info.get('linkedinUrl'),
                'firstName': basic_info.get('firstName'),
                'lastName': basic_info.get('lastName'),
                'headline': basic_info.get('headline'),
                'about': basic_info.get('about'),
                'openToWork': False,
                'hiring': False,
                'photo': basic_info.get('photo'),
                'premium': False,
                'influencer': False,
                'location': basic_info.get('location'),
                'verified': False,
                'experience': experience,
                'education': education,
                'skills': skills,
                'certifications': certifications,
                'projects': projects,
                'volunteering': volunteering,
                'languages': languages,
                'connectionsCount': None,
                'followerCount': None,
                'currentPosition': []
            },
            'query': {
                'publicIdentifier': basic_info.get('publicIdentifier'),
                'profileId': basic_info.get('id')
            },
            'status': 200,
            'retries': 0
        }
        
        # Извлечение текущей позиции из опыта работы
        if experience:
            first_exp = experience[0]
            if first_exp.get('endDate', {}).get('text') == 'Present' or not first_exp.get('endDate'):
                profile_data['element']['currentPosition'] = [{
                    'companyName': first_exp.get('companyName')
                }]
        
        logger.info("Парсинг профиля завершен")
        return profile_data

