"""Главный модуль парсера LinkedIn"""
import sys
import argparse
import logging
import os
from config import Config
from proxy_manager import ProxyManager
from rate_limiter import RateLimiter
from session_manager import SessionManager
from linkedin_parser import LinkedInParser
from data_exporter import DataExporter

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('linkedin_parser.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def parse_single_profile(url: str, config: Config, proxy_manager: ProxyManager, 
                         rate_limiter: RateLimiter, session_manager: SessionManager, exporter: DataExporter):
    """Парсинг одного профиля"""
    parser = LinkedInParser(config, proxy_manager, rate_limiter, session_manager)
    
    try:
        profile_data = parser.parse_profile(url)
        
        if profile_data.get('status') == 200 and 'element' in profile_data:
            public_identifier = profile_data['element'].get('publicIdentifier')
            exporter.export_profile(profile_data, public_identifier)
            logger.info(f"Профиль {url} успешно обработан")
            return True
        else:
            logger.error(f"Ошибка при парсинге профиля {url}: {profile_data.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"Критическая ошибка при парсинге {url}: {e}")
        return False

def parse_from_file(filepath: str, config: Config, proxy_manager: ProxyManager,
                    rate_limiter: RateLimiter, session_manager: SessionManager, exporter: DataExporter):
    """Парсинг профилей из файла"""
    if not os.path.exists(filepath):
        logger.error(f"Файл {filepath} не найден")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    logger.info(f"Найдено {len(urls)} URL для обработки")
    
    success_count = 0
    for i, url in enumerate(urls, 1):
        logger.info(f"Обработка {i}/{len(urls)}: {url}")
        if parse_single_profile(url, config, proxy_manager, rate_limiter, session_manager, exporter):
            success_count += 1
    
    logger.info(f"Обработано успешно: {success_count}/{len(urls)}")

def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description='Парсер профилей LinkedIn без авторизации с использованием прокси'
    )
    parser.add_argument(
        'url',
        nargs='?',
        help='URL профиля LinkedIn (например: https://www.linkedin.com/in/username)'
    )
    parser.add_argument(
        '-f', '--file',
        help='Файл со списком URL (по одному на строку)'
    )
    parser.add_argument(
        '-c', '--config',
        default='config.json',
        help='Путь к файлу конфигурации (по умолчанию: config.json)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Директория для сохранения результатов (по умолчанию: output)'
    )
    
    args = parser.parse_args()
    
    # Загрузка конфигурации
    config = Config(args.config)
    
    # Переопределение директории вывода, если указана
    output_dir = args.output or config.get('output.directory', 'output')
    exporter = DataExporter(output_dir)
    
    # Инициализация компонентов
    logger.info("Инициализация компонентов парсера...")
    proxy_manager = ProxyManager(config)
    rate_limiter = RateLimiter(
        min_delay=config.get('rate_limiting.min_delay', 2),
        max_delay=config.get('rate_limiting.max_delay', 5),
        enabled=config.get('rate_limiting.enabled', True)
    )
    session_manager = SessionManager(config)
    
    # Обработка входных данных
    if args.file:
        parse_from_file(args.file, config, proxy_manager, rate_limiter, session_manager, exporter)
    elif args.url:
        parse_single_profile(args.url, config, proxy_manager, rate_limiter, session_manager, exporter)
    else:
        parser.print_help()
        logger.error("Не указан URL профиля или файл со списком URL")
        sys.exit(1)
    
    # Вывод статистики
    logger.info("Статистика использования прокси:")
    proxy_manager.print_stats()
    
    logger.info("Статистика сессий:")
    session_stats = session_manager.get_stats()
    logger.info(f"Всего сессий: {session_stats['total_sessions']}")
    for session_id, data in session_stats['sessions'].items():
        logger.info(f"  {session_id}: User-Agent={data['user_agent'][:50]}..., "
                   f"cookies={data['cookies_count']}, jar_size={data['cookie_jar_size']} bytes")
    
    logger.info("Работа парсера завершена")

if __name__ == '__main__':
    main()

