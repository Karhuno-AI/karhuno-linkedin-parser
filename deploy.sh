#!/bin/bash
# Скрипт для удобного запуска парсера на сервере

cd /opt/linkedin-parser
source venv/bin/activate

# Если передан URL или файл, используем его
if [ "$1" != "" ]; then
    if [ -f "$1" ]; then
        python3 main.py -f "$1"
    else
        python3 main.py "$1"
    fi
else
    python3 main.py "$@"
fi

