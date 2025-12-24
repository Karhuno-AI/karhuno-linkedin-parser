"""Модуль для контроля лимитов запросов"""
import time
import random
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Класс для контроля частоты запросов"""
    
    def __init__(self, min_delay=2, max_delay=5, enabled=True):
        """
        Инициализация RateLimiter
        
        Args:
            min_delay: Минимальная задержка в секундах
            max_delay: Максимальная задержка в секундах
            enabled: Включен ли лимитер
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.enabled = enabled
        self.last_request_time = 0
    
    def wait(self):
        """Ожидание перед следующим запросом"""
        if not self.enabled:
            return
        
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Вычисляем случайную задержку
        delay = random.uniform(self.min_delay, self.max_delay)
        
        # Если прошло меньше времени, чем нужно, ждем
        if time_since_last < delay:
            wait_time = delay - time_since_last
            logger.debug(f"Ожидание {wait_time:.2f} секунд перед следующим запросом")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def reset(self):
        """Сброс времени последнего запроса"""
        self.last_request_time = 0

