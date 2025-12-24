"""Модуль для парсинга LinkedIn с использованием браузера (Selenium/Playwright)"""
import logging
import time
from typing import Optional, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from config import Config
from typing import Optional
try:
    from auth_manager import AuthManager
except Exception:
    AuthManager = None  # type: ignore

logger = logging.getLogger(__name__)


class BrowserParser:
    """Класс для парсинга LinkedIn страниц с использованием браузера"""
    
    def __init__(self, config: Config, auth_manager: Optional["AuthManager"] = None):
        """
        Инициализация BrowserParser
        
        Args:
            config: Объект конфигурации
        """
        self.config = config
        self.auth_manager = auth_manager
        self.driver = None
        self._init_driver()
    
    def _init_driver(self) -> None:
        """Инициализация Selenium WebDriver с максимальной антибот защитой"""
        try:
            chrome_options = Options()
            
            # Маскируем браузер как обычный
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Заголовки браузера
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # Производительность
            chrome_options.add_argument('--headless=new')  # Новый headless режим
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            
            # Отключаем логи
            chrome_options.add_argument('--log-level=3')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Эмулируем человеческое поведение
            self.driver.execute_cdp_cmd('Network.emulateNetworkConditions', {
                "offline": False,
                "downloadThroughput": 500 * 1024 / 8,
                "uploadThroughput": 20 * 1024 / 8,
                "latency": 100
            })
            
            logger.info("Selenium WebDriver успешно инициализирован")
            
        except Exception as e:
            logger.warning(f"Ошибка инициализации Selenium: {e}")
            self.driver = None
    
    def set_auth_manager(self, auth_manager: "AuthManager") -> None:
        self.auth_manager = auth_manager

    def fetch_profile(self, url: str, timeout: int = 30) -> Optional[str]:
        """
        Получить HTML страницы профиля с помощью браузера
        
        Args:
            url: URL профиля LinkedIn
            timeout: Максимальное время ожидания загрузки (сек)
            
        Returns:
            HTML страницы или None при ошибке
        """
        if not self.driver:
            logger.error("WebDriver не инициализирован")
            return None
        
        try:
            logger.info(f"Загрузка профиля браузером: {url}")

            # Если есть cookies – применим их перед переходом
            if self.auth_manager and self.auth_manager.has_cookies():
                try:
                    self.auth_manager.apply_to_selenium(self.driver)
                    logger.info("Аутентификационные cookies применены к браузеру")
                except Exception as e:
                    logger.warning(f"Не удалось применить cookies к браузеру: {e}")
            
            # Имитируем человеческое поведение - добавляем случайные задержки
            self.driver.get(url)
            
            # Ждем загрузки основного контента
            wait = WebDriverWait(self.driver, timeout)
            
            # LinkedIn может требовать логин - проверяем
            try:
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "profile-content")))
            except:
                # Если профиль защищен, попробуем получить доступное содержимое
                logger.warning("Профиль может быть защищен или требует логина")
                
                # Добавляем задержку для имитации человека
                time.sleep(2)
            
            # Скроллим страницу для загрузки больше контента
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Получаем исходный код после загрузки JavaScript
            page_source = self.driver.page_source
            
            logger.info(f"Профиль успешно загружен, размер: {len(page_source)} байт")
            return page_source
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке профиля браузером: {e}")
            return None
    
    def check_blockage(self) -> bool:
        """
        Проверить, заблокирован ли доступ
        
        Returns:
            True если доступ заблокирован
        """
        if not self.driver:
            return False
        
        try:
            # Проверяем наличие текста блокировки
            html = self.driver.page_source
            
            blockage_indicators = [
                'window.onload = function()',  # Редирект JavaScript
                'trkCode=bf',  # LinkedIn блокировка
                'If you are the owner'  # Сообщение об ограничении
            ]
            
            for indicator in blockage_indicators:
                if indicator in html:
                    logger.warning(f"Обнаружена блокировка: {indicator}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при проверке блокировки: {e}")
            return False
    
    def close(self) -> None:
        """Закрыть браузер"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Браузер успешно закрыт")
            except Exception as e:
                logger.error(f"Ошибка при закрытии браузера: {e}")
    
    def __del__(self):
        """Очистка при удалении объекта"""
        self.close()
