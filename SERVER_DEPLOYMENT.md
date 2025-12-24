# Развертывание на сервере 77.42.23.150

## Расположение
- **Путь:** `/opt/linkedin-parser`
- **Python:** 3.12.3
- **Виртуальное окружение:** `/opt/linkedin-parser/venv`

## Использование

### Базовый запуск
```bash
ssh root@77.42.23.150
cd /opt/linkedin-parser
source venv/bin/activate
python3 main.py https://www.linkedin.com/in/username
```

### Использование скрипта deploy.sh
```bash
ssh root@77.42.23.150
/opt/linkedin-parser/deploy.sh https://www.linkedin.com/in/username
```

### Парсинг из файла
```bash
# Создать файл с URL на сервере
ssh root@77.42.23.150 "echo 'https://www.linkedin.com/in/user1' > /tmp/urls.txt"

# Запустить парсинг
ssh root@77.42.23.150 "cd /opt/linkedin-parser && source venv/bin/activate && python3 main.py -f /tmp/urls.txt"
```

### Результаты
Результаты сохраняются в `/opt/linkedin-parser/output/` в формате JSON.

## Обновление кода
```bash
ssh root@77.42.23.150 "cd /opt/linkedin-parser && git pull"
```

## Логи
Логи сохраняются в `/opt/linkedin-parser/linkedin_parser.log`

## Проверка статуса
```bash
ssh root@77.42.23.150 "cd /opt/linkedin-parser && ls -la output/"
```

