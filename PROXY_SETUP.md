# Система ротирующих прокси для LinkedIn Parser

## Обзор

Проект теперь имеет полнофункциональную систему управления ротирующимися прокси и сессиями для парсинга LinkedIn без блокировок. Система использует несколько открытых источников прокси и управляет сессиями с ротацией User-Agents.

## Компоненты

### 1. ProxyManager (`proxy_manager.py`)

Управляет ротацией прокси из нескольких источников.

**Возможности:**
- ✅ Поддержка нескольких источников прокси (ProxyScrape, FreeProxyList, ProxyListPlus)
- ✅ Автоматическое обновление списка прокси каждые 5 минут
- ✅ Валидация IP и портов
- ✅ Отслеживание неработающих прокси
- ✅ Статистика использования каждого прокси
- ✅ Методы mark_success() и mark_failed() для отслеживания
- ✅ Вывод детальной статистики с методом print_stats()

**Источники прокси:**
1. **ProxyScrape** - бесплатный API с хорошей скоростью обновления
2. **FreeProxyList** - JSON API с чистыми прокси
3. **ProxyListPlus** - HTML парсинг (отключен по умолчанию)

**Использование:**

```python
from config import Config
from proxy_manager import ProxyManager

config = Config()
proxy_manager = ProxyManager(config)

# Получить прокси из ротации
proxy = proxy_manager.get_proxy()
# Результат: {'http': 'http://123.45.67.89:8080', 'https': 'http://123.45.67.89:8080'}

# Отметить успешное использование прокси
proxy_manager.mark_success(proxy, response_time=0.5)

# Отметить неработающий прокси
proxy_manager.mark_failed(proxy)

# Получить статистику
stats = proxy_manager.get_stats()
proxy_manager.print_stats()  # Выведет красивую таблицу статистики
```

### 2. SessionManager (`session_manager.py`)

Управляет сессиями requests с ротацией User-Agents и cookies.

**Возможности:**
- ✅ Создание и управление несколькими сессиями (по умолчанию до 10)
- ✅ Автоматическая ротация User-Agents (13+ вариантов)
- ✅ Управление cookies
- ✅ Маскировка IP через заголовки X-Forwarded-For
- ✅ Отслеживание статистики сессий

**User-Agents включают:**
- Chrome (Windows, Mac)
- Firefox (Windows, Mac)
- Safari (Mac)
- Edge (Windows)

**Использование:**

```python
from config import Config
from session_manager import SessionManager

config = Config()
session_manager = SessionManager(config)

# Получить сессию с автоматической ротацией User-Agent
session = session_manager.rotate_session()
response = session.get('https://example.com', timeout=30)

# Получить конкретную сессию
session_id = 'session_0'
session = session_manager.get_session_with_id(session_id)

# Обновить User-Agent во всех сессиях
session_manager.rotate_user_agent()

# Очистить cookies
session_manager.clear_cookies()

# Создать новую сессию для конкретного IP
session = session_manager.create_new_session_for_ip('123.45.67.89')

# Получить статистику
stats = session_manager.get_stats()
```

### 3. LinkedInParser обновлен

Теперь использует SessionManager для всех запросов.

**Улучшения:**
- ✅ Автоматическая ротация User-Agents
- ✅ Управление cookies между запросами
- ✅ Отслеживание успешности каждого прокси
- ✅ Создание новых сессий при ошибках 999 и 429
- ✅ Очистка cookies при ошибках 403
- ✅ Отслеживание времени ответа

**Использование:**

```python
from config import Config
from proxy_manager import ProxyManager
from rate_limiter import RateLimiter
from session_manager import SessionManager
from linkedin_parser import LinkedInParser

config = Config()
proxy_manager = ProxyManager(config)
rate_limiter = RateLimiter()
session_manager = SessionManager(config)

parser = LinkedInParser(config, proxy_manager, rate_limiter, session_manager)
profile_data = parser.parse_profile('https://www.linkedin.com/in/username')
```

## Конфигурация

### config.json

```json
{
  "proxy": {
    "enabled": true,
    "test_url": "https://httpbin.org/ip",
    "test_timeout": 5,
    "max_proxies": 50,
    "refresh_interval": 300
  },
  "session": {
    "max_sessions": 10
  },
  "rate_limiting": {
    "min_delay": 2,
    "max_delay": 5,
    "enabled": true
  },
  "linkedin": {
    "base_url": "https://www.linkedin.com",
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 5
  }
}
```

**Параметры:**
- `proxy.enabled` - включить/отключить прокси
- `proxy.max_proxies` - максимальное количество прокси в памяти (50 рекомендуется)
- `proxy.refresh_interval` - интервал обновления списка прокси в секундах (300 = 5 минут)
- `session.max_sessions` - максимальное количество одновременных сессий (10 рекомендуется)
- `rate_limiting.min_delay` - минимальная задержка между запросами
- `rate_limiting.max_delay` - максимальная задержка между запросами

## Обработка ошибок

### Статус 403 (Доступ запрещен)
- Прокси помечается как неработающий
- Cookies очищаются
- User-Agent обновляется
- Повторная попытка с новым прокси

### Статус 429 (Слишком много запросов)
- Все прокси помечаются как неработающие
- Все сессии очищаются и создается новая
- Увеличенная задержка перед повтором (15 сек)

### Статус 999 (LinkedIn блокирует)
- Создается новая сессия для конкретного IP
- Прокси помечается как неработающий
- Увеличенная задержка перед повтором (10 сек)

## Установка зависимостей

```bash
pip install -r requirements.txt
```

**Зависимости:**
- requests>=2.31.0 - HTTP клиент
- beautifulsoup4>=4.12.0 - парсинг HTML
- lxml>=4.9.0 - быстрый парсер XML/HTML

## Примеры использования

### 1. Парсинг одного профиля

```bash
python main.py "https://www.linkedin.com/in/username"
```

### 2. Парсинг из файла со списком URL

```bash
python main.py -f urls.txt
```

### 3. Использование кастомной конфигурации

```bash
python main.py -f urls.txt -c config.json -o results
```

### 4. Программное использование

```python
from config import Config
from proxy_manager import ProxyManager
from rate_limiter import RateLimiter
from session_manager import SessionManager
from linkedin_parser import LinkedInParser
from data_exporter import DataExporter

config = Config('config.json')
proxy_manager = ProxyManager(config)
rate_limiter = RateLimiter()
session_manager = SessionManager(config)
parser = LinkedInParser(config, proxy_manager, rate_limiter, session_manager)
exporter = DataExporter('output')

url = 'https://www.linkedin.com/in/example'
profile = parser.parse_profile(url)
if profile.get('status') == 200:
    exporter.export_profile(profile)
    print("✓ Профиль успешно сохранен")

# Вывести статистику
proxy_manager.print_stats()
```

## Мониторинг и статистика

### Статистика прокси

```python
stats = proxy_manager.get_stats()
print(f"Всего запросов: {stats['total_requests']}")
print(f"Успешных: {stats['successful_requests']}")
print(f"Ошибок: {stats['failed_requests']}")
print(f"Успешность: {stats['success_rate']:.1f}%")
```

### Лучшие прокси

Метод `print_stats()` выводит топ-10 прокси по количеству использований с их статистикой:

```
  123.45.67.89:8080: 45 запросов, успех 44/1, 97.8%, avg response: 0.82s
  98.76.54.32:3128: 42 запросов, успех 40/2, 95.2%, avg response: 0.95s
```

## Оптимизация

### Для быстрого парсинга:
```json
{
  "rate_limiting": {
    "min_delay": 1,
    "max_delay": 2,
    "enabled": true
  },
  "proxy": {
    "max_proxies": 100,
    "refresh_interval": 600
  },
  "session": {
    "max_sessions": 20
  }
}
```

### Для скрытности (медленнее, но надежнее):
```json
{
  "rate_limiting": {
    "min_delay": 5,
    "max_delay": 15,
    "enabled": true
  },
  "proxy": {
    "max_proxies": 30,
    "refresh_interval": 300
  },
  "session": {
    "max_sessions": 5
  }
}
```

## Решение проблем

### Проблема: LinkedIn все равно блокирует запросы

**Решения:**
1. Увеличить `rate_limiting.max_delay` до 10-20 секунд
2. Уменьшить `proxy.max_proxies` чтобы лучше ротировать
3. Включить более частую ротацию User-Agents (уже включена по умолчанию 20%)
4. Уменьшить количество `session.max_sessions`

### Проблема: Ошибка "Connection refused" для некоторых прокси

**Решение:**
Это нормально - неработающие прокси автоматически помечаются как неработающие и больше не используются.

### Проблема: Медленное парсинг

**Решения:**
1. Увеличить параллельность в rate_limiter
2. Использовать больше прокси (увеличить `max_proxies`)
3. Уменьшить `test_timeout` если прокси проверяются
4. Использовать больше сессий (`max_sessions`)

## Структура логов

Все события логируются в `linkedin_parser.log`:

```
2025-12-24 10:15:22,123 - linkedin_parser - INFO - Получение прокси из источника proxyscrape...
2025-12-24 10:15:23,456 - linkedin_parser - INFO - Получено 47 прокси из proxyscrape
2025-12-24 10:15:24,789 - linkedin_parser - INFO - Всего получено 50 уникальных прокси
2025-12-24 10:15:25,012 - linkedin_parser - INFO - Создана новая сессия session_0 с User-Agent: Mozilla/5.0...
```

## Интеграция с системой мониторинга

Все метрики доступны через методы get_stats():

```python
# Экспорт в JSON для мониторинга
import json

proxy_stats = proxy_manager.get_stats()
session_stats = session_manager.get_stats()

with open('monitoring.json', 'w') as f:
    json.dump({
        'proxy': proxy_stats,
        'session': session_stats,
        'timestamp': datetime.now().isoformat()
    }, f, indent=2)
```

## Технические детали

### Как работает ротация прокси

1. ProxyManager получает список прокси из всех доступных источников
2. При каждом запросе выбирается следующий прокси из ротации
3. Если прокси помечен как неработающий, он пропускается
4. Каждые 5 минут список обновляется (освежаются ошибки)
5. Прокси со 100% ошибками остаются в памяти но не используются

### Как работает ротация User-Agents

1. Каждая сессия создается с случайным User-Agent
2. При использовании сессии 20% вероятность обновить User-Agent
3. При ошибке 403 User-Agent обновляется принудительно
4. При ошибке 999 создается полностью новая сессия

### Как работает управление cookies

1. Cookies сохраняются в каждой сессии автоматически
2. При ошибке 403 cookies очищаются в текущей сессии
3. При ошибке 429 все cookies очищаются во всех сессиях
4. Cookies отправляются с каждым запросом из сессии

## Поддерживаемые HTTP коды ошибок

| Код | Описание | Действие |
|-----|---------|---------|
| 200 | OK | Успех, сохранить данные |
| 403 | Forbidden | Очистить cookies, обновить User-Agent, помечить прокси |
| 404 | Not Found | Профиль не существует, пропустить |
| 429 | Too Many Requests | Очистить все сессии, помечить все прокси |
| 999 | LinkedIn Block | Создать новую сессию, помечить прокси |

## Лицензия

Проект использует открытые источники прокси. Убедитесь, что вы соблюдаете их условия использования.

## Кредиты

- ProxyScrape API
- FreeProxyList API
- requests библиотека
- BeautifulSoup4
