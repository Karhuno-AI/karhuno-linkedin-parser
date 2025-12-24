#!/usr/bin/env python3
"""Скрипт для проверки работоспособности системы прокси и сессий"""

import sys
import logging
from config import Config
from proxy_manager import ProxyManager
from rate_limiter import RateLimiter
from session_manager import SessionManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_proxy_manager():
    """Тест ProxyManager"""
    logger.info("=" * 60)
    logger.info("ТЕСТИРОВАНИЕ PROXY MANAGER")
    logger.info("=" * 60)
    
    try:
        config = Config()
        proxy_manager = ProxyManager(config)
        
        # Проверка получения прокси
        logger.info("\n1. Получение прокси из ротации...")
        for i in range(5):
            proxy = proxy_manager.get_proxy()
            logger.info(f"   Попытка {i+1}: {proxy}")
        
        # Проверка отметки успеха
        logger.info("\n2. Отметка успешного использования прокси...")
        proxy = proxy_manager.get_proxy()
        if proxy:
            proxy_manager.mark_success(proxy, response_time=0.75)
            logger.info(f"   ✓ Отмечен прокси {proxy['http']}")
        
        # Проверка отметки ошибки
        logger.info("\n3. Отметка неработающего прокси...")
        if proxy:
            proxy_manager.mark_failed(proxy)
            logger.info(f"   ✓ Помечен прокси {proxy['http']} как неработающий")
        
        # Проверка статистики
        logger.info("\n4. Статистика ProxyManager:")
        proxy_manager.print_stats()
        
        logger.info("\n✓ ProxyManager работает корректно!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Ошибка в ProxyManager: {e}", exc_info=True)
        return False

def test_session_manager():
    """Тест SessionManager"""
    logger.info("\n" + "=" * 60)
    logger.info("ТЕСТИРОВАНИЕ SESSION MANAGER")
    logger.info("=" * 60)
    
    try:
        config = Config()
        session_manager = SessionManager(config)
        
        # Проверка получения сессии
        logger.info("\n1. Получение сессий...")
        for i in range(3):
            session = session_manager.rotate_session()
            user_agent = session.headers.get('User-Agent', 'Unknown')[:50]
            logger.info(f"   Сессия {i+1}: User-Agent={user_agent}...")
        
        # Проверка получения сессии по ID
        logger.info("\n2. Получение сессии по ID...")
        session_0 = session_manager.get_session_with_id('session_0')
        if session_0:
            logger.info(f"   ✓ Сессия session_0 найдена")
        else:
            logger.warning(f"   ✗ Сессия session_0 не найдена")
        
        # Проверка ротации User-Agent
        logger.info("\n3. Ротация User-Agent во всех сессиях...")
        session_manager.rotate_user_agent()
        logger.info(f"   ✓ User-Agents обновлены")
        
        # Проверка очистки cookies
        logger.info("\n4. Очистка cookies...")
        session_manager.clear_cookies()
        logger.info(f"   ✓ Cookies очищены")
        
        # Проверка создания новой сессии для IP
        logger.info("\n5. Создание сессии для конкретного IP...")
        session = session_manager.create_new_session_for_ip('192.168.1.1')
        if session:
            logger.info(f"   ✓ Сессия создана для IP 192.168.1.1")
        
        # Проверка статистики
        logger.info("\n6. Статистика SessionManager:")
        stats = session_manager.get_stats()
        logger.info(f"   Всего сессий: {stats['total_sessions']}")
        for session_id, data in list(stats['sessions'].items())[:3]:
            logger.info(f"   {session_id}: cookies={data['cookies_count']}")
        
        logger.info("\n✓ SessionManager работает корректно!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Ошибка в SessionManager: {e}", exc_info=True)
        return False

def test_rate_limiter():
    """Тест RateLimiter"""
    logger.info("\n" + "=" * 60)
    logger.info("ТЕСТИРОВАНИЕ RATE LIMITER")
    logger.info("=" * 60)
    
    try:
        config = Config()
        rate_limiter = RateLimiter(
            min_delay=config.get('rate_limiting.min_delay', 2),
            max_delay=config.get('rate_limiting.max_delay', 5),
            enabled=True
        )
        
        logger.info("\n1. Проверка rate limiting...")
        logger.info("   Отправка 3 запросов с задержками...")
        
        import time
        for i in range(3):
            start = time.time()
            rate_limiter.wait()
            elapsed = time.time() - start
            logger.info(f"   Запрос {i+1}: задержка {elapsed:.2f}s")
        
        logger.info("\n✓ RateLimiter работает корректно!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Ошибка в RateLimiter: {e}", exc_info=True)
        return False

def test_config():
    """Тест Config"""
    logger.info("\n" + "=" * 60)
    logger.info("ТЕСТИРОВАНИЕ CONFIG")
    logger.info("=" * 60)
    
    try:
        config = Config()
        
        logger.info("\n1. Проверка параметров конфигурации...")
        
        # Проверка основных параметров
        proxy_enabled = config.get('proxy.enabled', True)
        logger.info(f"   proxy.enabled: {proxy_enabled}")
        
        max_proxies = config.get('proxy.max_proxies', 50)
        logger.info(f"   proxy.max_proxies: {max_proxies}")
        
        min_delay = config.get('rate_limiting.min_delay', 2)
        logger.info(f"   rate_limiting.min_delay: {min_delay}")
        
        max_sessions = config.get('session.max_sessions', 10)
        logger.info(f"   session.max_sessions: {max_sessions}")
        
        user_agents_count = len(config.get('user_agents', []))
        logger.info(f"   user_agents count: {user_agents_count}")
        
        logger.info("\n✓ Config работает корректно!")
        return True
        
    except Exception as e:
        logger.error(f"✗ Ошибка в Config: {e}", exc_info=True)
        return False

def main():
    """Главная функция тестирования"""
    logger.info("\n")
    logger.info("╔" + "═" * 58 + "╗")
    logger.info("║" + " " * 10 + "ТЕСТИРОВАНИЕ СИСТЕМЫ ПРОКСИ И СЕССИЙ" + " " * 12 + "║")
    logger.info("╚" + "═" * 58 + "╝")
    
    results = {
        'Config': test_config(),
        'RateLimiter': test_rate_limiter(),
        'ProxyManager': test_proxy_manager(),
        'SessionManager': test_session_manager(),
    }
    
    logger.info("\n" + "=" * 60)
    logger.info("ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    logger.info("=" * 60)
    
    for name, result in results.items():
        status = "✓ ПРОЙДЕН" if result else "✗ ПРОВАЛЕН"
        logger.info(f"{name}: {status}")
    
    logger.info("=" * 60)
    
    if all(results.values()):
        logger.info("\n✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return 0
    else:
        logger.error("\n✗ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ!")
        return 1

if __name__ == '__main__':
    sys.exit(main())
