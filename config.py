"""Конфигурация парсера LinkedIn"""
import json
import os

class Config:
    """Класс для управления конфигурацией"""
    
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """Загрузка конфигурации из файла"""
        default_config = {
            "proxy": {
                "enabled": True,
                "api_url": "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
                "test_url": "https://httpbin.org/ip",
                "test_timeout": 5,
                "max_proxies": 50,
                "refresh_interval": 300
            },
            "rate_limiting": {
                "min_delay": 2,
                "max_delay": 5,
                "enabled": True
            },
            "linkedin": {
                "base_url": "https://www.linkedin.com",
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 5
            },
            "output": {
                "directory": "output",
                "format": "json"
            },
            "user_agents": [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
            ]
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # Объединение с дефолтными настройками
                    default_config.update(user_config)
            except Exception as e:
                print(f"Ошибка загрузки конфигурации: {e}. Используются настройки по умолчанию.")
        
        return default_config
    
    def get(self, key, default=None):
        """Получение значения конфигурации"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def save(self):
        """Сохранение конфигурации в файл"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")

