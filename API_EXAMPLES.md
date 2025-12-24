# Примеры CURL запросов для API

## Запуск API сервера

```bash
ssh root@77.42.23.150
cd /opt/linkedin-parser
source venv/bin/activate
pip install flask
python3 api_server.py
```

Или в фоне:
```bash
nohup python3 api_server.py > api.log 2>&1 &
```

## Примеры запросов

### 1. Проверка здоровья сервиса

```bash
curl -X GET http://77.42.23.150:5000/health
```

**Ответ:**
```json
{
  "status": "ok",
  "service": "linkedin-parser-api"
}
```

### 2. Парсинг одного профиля

```bash
curl -X POST http://77.42.23.150:5000/parse \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.linkedin.com/in/username"
  }'
```

**Ответ (успех):**
```json
{
  "status": "success",
  "data": {
    "element": {
      "publicIdentifier": "username",
      "firstName": "John",
      "lastName": "Doe",
      ...
    },
    "status": 200
  },
  "saved_to": "output/username.json"
}
```

**Ответ (ошибка):**
```json
{
  "status": "error",
  "error": "Failed to load profile page"
}
```

### 3. Парсинг нескольких профилей (batch)

```bash
curl -X POST http://77.42.23.150:5000/parse/batch \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://www.linkedin.com/in/user1",
      "https://www.linkedin.com/in/user2",
      "https://www.linkedin.com/in/user3"
    ]
  }'
```

**Ответ:**
```json
{
  "status": "completed",
  "total": 3,
  "results": [
    {
      "url": "https://www.linkedin.com/in/user1",
      "status": "success",
      "publicIdentifier": "user1",
      "saved_to": "output/user1.json"
    },
    {
      "url": "https://www.linkedin.com/in/user2",
      "status": "error",
      "error": "Failed to parse"
    }
  ]
}
```

### 4. С сохранением ответа в файл

```bash
curl -X POST http://77.42.23.150:5000/parse \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.linkedin.com/in/username"}' \
  -o response.json
```

### 5. С подробным выводом (verbose)

```bash
curl -v -X POST http://77.42.23.150:5000/parse \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.linkedin.com/in/username"}'
```

### 6. С таймаутом

```bash
curl --max-time 300 -X POST http://77.42.23.150:5000/parse \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.linkedin.com/in/username"}'
```

## Systemd сервис для API

Создайте файл `/etc/systemd/system/linkedin-parser-api.service`:

```ini
[Unit]
Description=LinkedIn Parser API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/linkedin-parser
Environment="PATH=/opt/linkedin-parser/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PORT=5000"
ExecStart=/opt/linkedin-parser/venv/bin/python3 /opt/linkedin-parser/api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запуск:
```bash
systemctl daemon-reload
systemctl enable linkedin-parser-api
systemctl start linkedin-parser-api
systemctl status linkedin-parser-api
```

