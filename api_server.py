"""HTTP API сервер для LinkedIn парсера"""
from flask import Flask, request, jsonify
import logging
import json
import os
from config import Config
from proxy_manager import ProxyManager
from rate_limiter import RateLimiter
from linkedin_parser import LinkedInParser
from data_exporter import DataExporter

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Устанавливаем уровень логирования для внешних библиотек
logging.getLogger('werkzeug').setLevel(logging.INFO)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Инициализация компонентов
config = Config()
proxy_manager = ProxyManager(config)
rate_limiter = RateLimiter(
    min_delay=config.get('rate_limiting.min_delay', 2),
    max_delay=config.get('rate_limiting.max_delay', 5),
    enabled=config.get('rate_limiting.enabled', True)
)
exporter = DataExporter(config.get('output.directory', 'output'))

@app.route('/health', methods=['GET'])
def health():
    """Проверка здоровья сервиса"""
    return jsonify({
        'status': 'ok',
        'service': 'linkedin-parser-api'
    }), 200

@app.route('/parse', methods=['POST'])
def parse_profile():
    """
    Парсинг профиля LinkedIn
    
    Body (JSON):
    {
        "url": "https://www.linkedin.com/in/username"
    }
    """
    try:
        # Более гибкий парсинг JSON
        data = None
        
        if request.is_json:
            data = request.get_json()
        elif request.data:
            try:
                data = json.loads(request.data)
            except:
                data = None
        
        if not data or 'url' not in data:
            logger.warning(f"Неполные данные запроса: {data}")
            return jsonify({
                'error': 'Missing required field: url',
                'received': str(data)
            }), 400
        
        url = data['url']
        logger.info(f"Получен запрос на парсинг: {url}")
        logger.info(f"Полные данные запроса: {data}")
        
        # Создаем парсер
        parser = LinkedInParser(config, proxy_manager, rate_limiter)
        
        # Парсим профиль
        logger.info("Начало парсинга профиля...")
        profile_data = parser.parse_profile(url)
        logger.info(f"Парсинг завершен. Статус: {profile_data.get('status')}")
        
        if profile_data.get('status') == 200 and 'element' in profile_data:
            # Сохраняем в файл
            public_identifier = profile_data['element'].get('publicIdentifier')
            logger.info(f"Сохранение профиля: {public_identifier}")
            filepath = exporter.export_profile(profile_data, public_identifier)
            logger.info(f"Профиль сохранен в: {filepath}")
            
            return jsonify({
                'status': 'success',
                'data': profile_data,
                'saved_to': filepath
            }), 200
        else:
            # Формируем детальный ответ об ошибке
            error_message = profile_data.get('error', 'Failed to parse profile')
            error_details = profile_data.get('errorDetails', {})
            
            logger.warning(f"Ошибка парсинга: {error_message}")
            logger.warning(f"Детали ошибки: {error_details}")
            
            return jsonify({
                'status': 'error',
                'error': error_message,
                'errorDetails': error_details,
                'data': profile_data
            }), 500
            
    except Exception as e:
        logger.error(f"Ошибка при парсинге: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/parse/batch', methods=['POST'])
def parse_batch():
    """
    Парсинг нескольких профилей
    
    Body (JSON):
    {
        "urls": [
            "https://www.linkedin.com/in/user1",
            "https://www.linkedin.com/in/user2"
        ]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'urls' not in data:
            return jsonify({
                'error': 'Missing required field: urls'
            }), 400
        
        urls = data['urls']
        if not isinstance(urls, list):
            return jsonify({
                'error': 'urls must be an array'
            }), 400
        
        logger.info(f"Получен запрос на парсинг {len(urls)} профилей")
        
        parser = LinkedInParser(config, proxy_manager, rate_limiter)
        results = []
        
        for url in urls:
            try:
                profile_data = parser.parse_profile(url)
                
                if profile_data.get('status') == 200 and 'element' in profile_data:
                    public_identifier = profile_data['element'].get('publicIdentifier')
                    filepath = exporter.export_profile(profile_data, public_identifier)
                    
                    results.append({
                        'url': url,
                        'status': 'success',
                        'publicIdentifier': public_identifier,
                        'saved_to': filepath
                    })
                else:
                    results.append({
                        'url': url,
                        'status': 'error',
                        'error': profile_data.get('error', 'Failed to parse')
                    })
            except Exception as e:
                logger.error(f"Ошибка при парсинге {url}: {e}")
                results.append({
                    'url': url,
                    'status': 'error',
                    'error': str(e)
                })
        
        return jsonify({
            'status': 'completed',
            'total': len(urls),
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Ошибка при batch парсинге: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

