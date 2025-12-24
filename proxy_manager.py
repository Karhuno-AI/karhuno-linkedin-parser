"""Модуль для управления прокси-серверами"""
import requests
import time
import logging
from typing import Optional, List, Dict
from config import Config

logger = logging.getLogger(__name__)

class ProxyManager:
    """Класс для управления прокси-серверами"""
    
    def __init__(self, config: Config):
        """
        Инициализация ProxyManager
        
        Args:
            config: Объект конфигурации
        """
        self.config = config
        self.proxies: List[str] = []
        self.current_index = 0
        self.failed_proxies: set = set()
        self.last_refresh = 0
        self.proxy_enabled = config.get('proxy.enabled', True)
        self.api_url = config.get('proxy.api_url')
        self.test_url = config.get('proxy.test_url', 'https://httpbin.org/ip')
        self.test_timeout = config.get('proxy.test_timeout', 5)
        self.max_proxies = config.get('proxy.max_proxies', 50)
        self.refresh_interval = config.get('proxy.refresh_interval', 300)
        
        if self.proxy_enabled:
            self._fetch_proxies()
    
    def _fetch_proxies(self) -> bool:
        """
        Получение списка прокси через API
        
        Returns:
            True если прокси успешно получены
        """
        try:
            logger.info("Получение списка прокси через ProxyScrape API...")
            response = requests.get(self.api_url, timeout=10)
            
            if response.status_code == 200:
                # Прокси возвращаются в виде текста, по одному на строку
                raw_proxies = response.text.strip().split('\n')
                # Фильтруем пустые строки и валидируем формат ip:port
                valid_proxies = []
                for p in raw_proxies:
                    p = p.strip()
                    if not p:
                        continue
                    # Проверяем формат ip:port
                    if ':' in p and not any(c in p for c in [' ', '\t', '\n', '\r']):
                        parts = p.split(':')
                        if len(parts) == 2 and parts[1].isdigit():
                            valid_proxies.append(p)
                
                self.proxies = valid_proxies[:self.max_proxies]
                
                # Удаляем уже неработающие прокси
                self.proxies = [p for p in self.proxies if p not in self.failed_proxies]
                
                if self.proxies:
                    logger.info(f"Получено {len(self.proxies)} прокси")
                    self.last_refresh = time.time()
                    return True
                else:
                    logger.warning("Не удалось получить рабочие прокси")
                    return False
            else:
                logger.error(f"Ошибка получения прокси: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при получении прокси: {e}")
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
            
            # Проверяем прокси (можно отключить для ускорения)
            # if not self._test_proxy(proxy):
            #     self.failed_proxies.add(proxy)
            #     continue
            
            return {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
        
        # Если все прокси не работают, возвращаем None
        logger.warning("Все прокси не работают, работаем без прокси")
        return None
    
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
                logger.debug(f"Прокси {proxy} помечен как неработающий")
    
    def reset(self):
        """Сброс состояния менеджера прокси"""
        self.current_index = 0
        self.failed_proxies.clear()

