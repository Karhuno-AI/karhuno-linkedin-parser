"""Модуль для управления прокси-серверами"""
import requests
import time
import logging
import random
from typing import Optional, List, Dict, Set
from config import Config
from datetime import datetime

logger = logging.getLogger(__name__)

class ProxyManager:
    """Класс для управления прокси-серверами с поддержкой множественных источников"""
    
    # Источники прокси
    PROXY_SOURCES = {
        'proxyscrape': {
            'url': 'https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all',
            'parser': 'lines'
        },
        'freeproxylists': {
            'url': 'https://www.proxy-list.download/api/v1/get?type=http',
            'parser': 'json_data'
        },
        'proxylistplus': {
            'url': 'https://list.proxylistplus.com/Fresh-HTTP-Proxy-List-1',
            'parser': 'html_table',
            'enabled': False  # Может требовать парсинга HTML
        }
    }
    
    def __init__(self, config: Config):
        """
        Инициализация ProxyManager
        
        Args:
            config: Объект конфигурации
        """
        self.config = config
        self.proxies: List[str] = []
        self.current_index = 0
        self.failed_proxies: Set[str] = set()
        self.last_refresh = 0
        self.proxy_enabled = config.get('proxy.enabled', True)
        self.test_url = config.get('proxy.test_url', 'https://httpbin.org/ip')
        self.test_timeout = config.get('proxy.test_timeout', 5)
        self.max_proxies = config.get('proxy.max_proxies', 50)
        self.refresh_interval = config.get('proxy.refresh_interval', 300)
        
        # Статистика использования прокси
        self.proxy_stats: Dict[str, Dict] = {}
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        if self.proxy_enabled:
            self._fetch_proxies()
    
    def _fetch_proxies(self) -> bool:
        """
        Получение списка прокси из различных источников
        
        Returns:
            True если прокси успешно получены
        """
        all_proxies = []
        
        # Пробуем каждый источник
        for source_name, source_config in self.PROXY_SOURCES.items():
            if not source_config.get('enabled', True):
                logger.debug(f"Источник {source_name} отключен")
                continue
                
            try:
                logger.info(f"Получение прокси из источника {source_name}...")
                proxies = self._fetch_from_source(source_name, source_config)
                
                if proxies:
                    logger.info(f"Получено {len(proxies)} прокси из {source_name}")
                    all_proxies.extend(proxies)
                else:
                    logger.warning(f"Не удалось получить прокси из {source_name}")
                    
            except Exception as e:
                logger.warning(f"Ошибка при получении прокси из {source_name}: {e}")
                continue
        
        # Удаляем дубликаты и неработающие прокси
        unique_proxies = list(set(all_proxies))
        unique_proxies = [p for p in unique_proxies if p not in self.failed_proxies]
        
        # Ограничиваем количество прокси
        self.proxies = unique_proxies[:self.max_proxies]
        
        if self.proxies:
            logger.info(f"Всего получено {len(self.proxies)} уникальных прокси")
            self.last_refresh = time.time()
            return True
        else:
            logger.warning("Не удалось получить рабочие прокси из всех источников")
            return False
    
    def _fetch_from_source(self, source_name: str, source_config: Dict) -> List[str]:
        """
        Получение прокси из конкретного источника
        
        Args:
            source_name: Название источника
            source_config: Конфигурация источника
            
        Returns:
            Список прокси
        """
        url = source_config.get('url')
        parser = source_config.get('parser', 'lines')
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            if parser == 'lines':
                return self._parse_proxies_lines(response.text)
            elif parser == 'json_data':
                return self._parse_proxies_json(response.text)
            elif parser == 'html_table':
                return self._parse_proxies_html(response.text)
            else:
                logger.warning(f"Неизвестный парсер: {parser}")
                return []
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке прокси из {source_name}: {e}")
            return []
    
    def _parse_proxies_lines(self, text: str) -> List[str]:
        """
        Парсинг прокси из текста (по одному на строку)
        
        Args:
            text: Текст с прокси
            
        Returns:
            Список валидных прокси
        """
        proxies = []
        invalid_count = 0
        
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Проверяем формат ip:port
            if ':' in line and not any(c in line for c in [' ', '\t', '\r']):
                parts = line.split(':')
                if len(parts) == 2 and parts[0] and parts[1]:
                    if self._validate_proxy(parts[0], parts[1]):
                        proxies.append(line)
                    else:
                        invalid_count += 1
                else:
                    invalid_count += 1
            else:
                invalid_count += 1
        
        logger.debug(f"Спарсено {len(proxies)} валидных прокси, невалидных: {invalid_count}")
        return proxies
    
    def _parse_proxies_json(self, text: str) -> List[str]:
        """
        Парсинг прокси из JSON
        
        Args:
            text: JSON текст с прокси
            
        Returns:
            Список валидных прокси
        """
        try:
            data = requests.json(text)
            proxies = []
            
            # Для proxy-list.download API
            if isinstance(data, dict) and 'LISTA' in data:
                for proxy_str in data['LISTA']:
                    if isinstance(proxy_str, str) and ':' in proxy_str:
                        parts = proxy_str.split(':')
                        if len(parts) == 2 and self._validate_proxy(parts[0], parts[1]):
                            proxies.append(proxy_str)
            
            return proxies
        except Exception as e:
            logger.warning(f"Ошибка парсинга JSON: {e}")
            return []
    
    def _parse_proxies_html(self, html: str) -> List[str]:
        """
        Парсинг прокси из HTML таблицы
        
        Args:
            html: HTML текст со страницей прокси
            
        Returns:
            Список валидных прокси
        """
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            proxies = []
            
            # Ищем таблицы с прокси
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Пропускаем заголовок
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        ip = cols[0].text.strip()
                        port = cols[1].text.strip()
                        if self._validate_proxy(ip, port):
                            proxies.append(f"{ip}:{port}")
            
            return proxies
        except Exception as e:
            logger.warning(f"Ошибка парсинга HTML: {e}")
            return []
    
    def _validate_proxy(self, ip: str, port: str) -> bool:
        """
        Валидация IP и порта прокси
        
        Args:
            ip: IP адрес
            port: Порт
            
        Returns:
            True если прокси валидна
        """
        try:
            # Проверяем IP
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            
            # Проверяем порт
            port_num = int(port)
            if port_num < 1 or port_num > 65535:
                return False
            
            return True
        except:
            return False
    
    def _test_proxy(self, proxy: str) -> bool:
        """
        Проверка работоспособности прокси
        
        Args:
            proxy: Адрес прокси в формате ip:port
            
        Returns:
            True если прокси работает
        """
        try:
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            response = requests.get(
                self.test_url,
                proxies=proxies,
                timeout=self.test_timeout
            )
            
            if response.status_code == 200:
                logger.debug(f"Прокси {proxy} работает")
                return True
            else:
                logger.debug(f"Прокси {proxy} не отвечает (HTTP {response.status_code})")
                return False
                
        except Exception as e:
            logger.debug(f"Прокси {proxy} не работает: {e}")
            return False
    
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        Получение следующего прокси из ротации
        
        Returns:
            Словарь с настройками прокси или None
        """
        if not self.proxy_enabled:
            return None
        
        # Проверяем, нужно ли обновить список прокси
        if time.time() - self.last_refresh > self.refresh_interval:
            logger.info("Обновление списка прокси...")
            self._fetch_proxies()
        
        # Если нет доступных прокси, пытаемся получить новые
        if not self.proxies:
            logger.warning("Нет доступных прокси, попытка получить новые...")
            if not self._fetch_proxies():
                logger.warning("Не удалось получить прокси, работаем без прокси")
                return None
        
        # Ротация прокси
        attempts = 0
        max_attempts = len(self.proxies) * 2
        
        while attempts < max_attempts:
            if self.current_index >= len(self.proxies):
                self.current_index = 0
            
            proxy = self.proxies[self.current_index]
            self.current_index += 1
            attempts += 1
            
            # Пропускаем неработающие прокси
            if proxy in self.failed_proxies:
                continue
            
            # Инициализируем статистику прокси, если ее еще нет
            if proxy not in self.proxy_stats:
                self.proxy_stats[proxy] = {
                    'requests': 0,
                    'successful': 0,
                    'failed': 0,
                    'first_used': datetime.now().isoformat(),
                    'last_used': None,
                    'avg_response_time': 0
                }
            
            # Обновляем статистику
            self.proxy_stats[proxy]['requests'] += 1
            self.proxy_stats[proxy]['last_used'] = datetime.now().isoformat()
            self.total_requests += 1
            
            return {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
        
        # Если все прокси не работают, возвращаем None
        logger.warning("Все прокси не работают, работаем без прокси")
        return None
    
    def mark_success(self, proxy_dict: Optional[Dict[str, str]], response_time: float = 0):
        """
        Пометить прокси как успешно использованный
        
        Args:
            proxy_dict: Словарь с настройками прокси
            response_time: Время ответа в секундах
        """
        if proxy_dict and 'http' in proxy_dict:
            proxy_url = proxy_dict['http']
            if proxy_url.startswith('http://'):
                proxy = proxy_url.replace('http://', '')
                if proxy in self.proxy_stats:
                    self.proxy_stats[proxy]['successful'] += 1
                    if response_time > 0:
                        # Обновляем среднее время ответа
                        stats = self.proxy_stats[proxy]
                        total = stats['successful'] + stats['failed']
                        stats['avg_response_time'] = (
                            (stats['avg_response_time'] * (total - 1) + response_time) / total
                        )
                self.successful_requests += 1
                logger.debug(f"Прокси {proxy} отмечен как успешный")
    
    def mark_failed(self, proxy_dict: Optional[Dict[str, str]]):
        """
        Пометить прокси как неработающий
        
        Args:
            proxy_dict: Словарь с настройками прокси
        """
        if proxy_dict and 'http' in proxy_dict:
            # Извлекаем адрес прокси из URL
            proxy_url = proxy_dict['http']
            if proxy_url.startswith('http://'):
                proxy = proxy_url.replace('http://', '')
                self.failed_proxies.add(proxy)
                if proxy in self.proxy_stats:
                    self.proxy_stats[proxy]['failed'] += 1
                self.failed_requests += 1
                logger.info(f"Прокси {proxy} помечен как неработающий")
    
    def test_proxy(self, proxy: str) -> bool:
        """
        Проверка работоспособности прокси
        
        Args:
            proxy: Адрес прокси в формате ip:port
            
        Returns:
            True если прокси работает
        """
        try:
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            response = requests.get(
                self.test_url,
                proxies=proxies,
                timeout=self.test_timeout
            )
            
            if response.status_code == 200:
                logger.debug(f"Прокси {proxy} работает")
                return True
            else:
                logger.debug(f"Прокси {proxy} не отвечает (HTTP {response.status_code})")
                return False
                
        except Exception as e:
            logger.debug(f"Прокси {proxy} не работает: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """
        Получить статистику использования прокси
        
        Returns:
            Словарь со статистикой
        """
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': (
                (self.successful_requests / self.total_requests * 100)
                if self.total_requests > 0 else 0
            ),
            'proxies_count': len(self.proxies),
            'failed_proxies_count': len(self.failed_proxies),
            'proxy_stats': self.proxy_stats,
            'last_refresh': datetime.fromtimestamp(self.last_refresh).isoformat() if self.last_refresh else None
        }
    
    def print_stats(self):
        """Вывести статистику использования прокси"""
        stats = self.get_stats()
        logger.info("=" * 60)
        logger.info("СТАТИСТИКА ИСПОЛЬЗОВАНИЯ ПРОКСИ")
        logger.info("=" * 60)
        logger.info(f"Всего запросов: {stats['total_requests']}")
        logger.info(f"Успешных: {stats['successful_requests']}")
        logger.info(f"Ошибок: {stats['failed_requests']}")
        logger.info(f"Успешность: {stats['success_rate']:.1f}%")
        logger.info(f"Доступных прокси: {stats['proxies_count']}")
        logger.info(f"Отказавших прокси: {stats['failed_proxies_count']}")
        logger.info(f"Последнее обновление: {stats['last_refresh']}")
        
        if stats['proxy_stats']:
            logger.info("-" * 60)
            logger.info("Статистика по каждому прокси:")
            for proxy, data in sorted(stats['proxy_stats'].items(), 
                                      key=lambda x: x[1]['requests'], reverse=True)[:10]:
                success_rate = (
                    (data['successful'] / (data['successful'] + data['failed']) * 100)
                    if (data['successful'] + data['failed']) > 0 else 0
                )
                logger.info(f"  {proxy}: {data['requests']} запросов, "
                           f"успех {data['successful']}/{data['failed']}, "
                           f"{success_rate:.1f}%, "
                           f"avg response: {data['avg_response_time']:.2f}s")
        logger.info("=" * 60)
    
    def reset(self):
        """Сброс состояния менеджера прокси"""
        self.current_index = 0
        self.failed_proxies.clear()
        self.proxy_stats.clear()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
