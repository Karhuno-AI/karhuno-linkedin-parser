#!/bin/bash
# Скрипт для обновления LinkedIn Parser на сервере

set -e

REPO_DIR="/opt/linkedin-parser"

echo "📋 LinkedIn Parser - Скрипт обновления"
echo "========================================"
echo ""

# Проверяем что репозиторий существует
if [ ! -d "$REPO_DIR" ]; then
    echo "❌ Директория $REPO_DIR не найдена"
    exit 1
fi

echo "📥 Обновление из GitHub..."
cd "$REPO_DIR"

# Проверяем git статус
if [ ! -d ".git" ]; then
    echo "❌ Git репозиторий не инициализирован"
    exit 1
fi

# Сохраняем текущее состояние
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 Текущая ветка: $CURRENT_BRANCH"

# Получаем последние изменения
git fetch origin
echo "✓ Получены изменения с GitHub"

# Обновляем код
git pull origin $CURRENT_BRANCH
echo "✓ Код обновлен"

# Обновляем зависимости
if [ -f "requirements.txt" ]; then
    echo "📦 Обновление зависимостей..."
    source venv/bin/activate
    pip install -r requirements.txt --upgrade
    echo "✓ Зависимости обновлены"
fi

# Проверяем синтаксис основных файлов
echo "🔍 Проверка синтаксиса Python файлов..."
python3 -m py_compile proxy_manager.py
python3 -m py_compile session_manager.py
python3 -m py_compile linkedin_parser.py
python3 -m py_compile main.py
echo "✓ Синтаксис валиден"

# Перезагружаем сервис
echo ""
echo "🔄 Перезагрузка сервиса..."
systemctl daemon-reload
systemctl restart linkedin-parser.service

# Проверяем статус сервиса
echo "📊 Статус сервиса:"
systemctl status linkedin-parser.service --no-pager

echo ""
echo "✅ Обновление завершено успешно!"
echo ""
echo "📊 Информация о последнем коммите:"
git log -1 --oneline --decorate

echo ""
echo "Для просмотра логов:"
echo "  journalctl -u linkedin-parser.service -f"
