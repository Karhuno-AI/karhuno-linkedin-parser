# Скрипт для обновления LinkedIn Parser сервиса (Windows/PowerShell)

param(
    [switch]$SkipTest = $false,
    [switch]$DryRun = $false
)

$repoDir = "C:\opt\linkedin-parser"
$serviceLogFile = "$repoDir\service_update.log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage
    Add-Content -Path $serviceLogFile -Value $logMessage
}

# Заголовок
Write-Host "╔════════════════════════════════════════╗"
Write-Host "║  LinkedIn Parser - Обновление сервиса  ║"
Write-Host "╚════════════════════════════════════════╝"
Write-Host ""

# Проверяем директорию
if (-not (Test-Path $repoDir)) {
    Write-Log "Директория $repoDir не найдена" "ERROR"
    exit 1
}

Write-Log "Директория репозитория: $repoDir"

# Переходим в директорию
Push-Location $repoDir

try {
    # Проверяем git
    if (-not (Test-Path ".git")) {
        Write-Log "Git репозиторий не инициализирован" "ERROR"
        exit 1
    }

    Write-Log "Статус git репозитория:"
    & git status --short
    
    # Получаем текущую ветку
    $branch = & git branch --show-current
    Write-Log "Текущая ветка: $branch"

    if ($DryRun) {
        Write-Log "РЕЖИМ ТЕСТИРОВАНИЯ - Изменения не будут применены" "WARN"
    }

    # Обновляем из GitHub
    Write-Log "Получение изменений с GitHub..."
    & git fetch origin
    Write-Log "✓ Изменения получены"

    # Обновляем код
    if (-not $DryRun) {
        Write-Log "Обновление кода..."
        & git pull origin $branch
        Write-Log "✓ Код обновлен"
    } else {
        Write-Log "[ТЕСТ] Были бы выполнены: git pull origin $branch" "WARN"
    }

    # Обновляем зависимости
    if (Test-Path "requirements.txt") {
        Write-Log "Обновление зависимостей Python..."
        if (-not $DryRun) {
            python -m pip install -r requirements.txt --upgrade --quiet
            Write-Log "✓ Зависимости обновлены"
        } else {
            Write-Log "[ТЕСТ] Были бы установлены зависимости из requirements.txt" "WARN"
        }
    }

    # Проверяем синтаксис Python файлов
    if (-not $SkipTest) {
        Write-Log "Проверка синтаксиса Python файлов..."
        $pythonFiles = @("proxy_manager.py", "session_manager.py", "linkedin_parser.py", "main.py")
        
        foreach ($file in $pythonFiles) {
            if (Test-Path $file) {
                try {
                    & python -m py_compile $file
                    Write-Log "  ✓ $file"
                } catch {
                    Write-Log "  ✗ $file: $_" "ERROR"
                    exit 1
                }
            }
        }
        Write-Log "✓ Все файлы синтаксически верны"
    }

    # Запускаем тесты
    if ((Test-Path "test_proxy_system.py") -and (-not $SkipTest)) {
        Write-Log "Запуск тестов системы..."
        if (-not $DryRun) {
            & python test_proxy_system.py 2>&1 | Select-Object -Last 5
            Write-Log "✓ Тесты завершены"
        }
    }

    # Информация о последнем коммите
    Write-Log ""
    Write-Log "Информация о последнем коммите:"
    & git log -1 --oneline --decorate

    # Статус
    Write-Log ""
    Write-Log "✅ Обновление успешно завершено!" "SUCCESS"

} catch {
    Write-Log "Ошибка: $_" "ERROR"
    exit 1
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "📋 Дополнительные команды:"
Write-Host "  • Для проверки логов: Get-Content $serviceLogFile -Tail 20"
Write-Host "  • Для проверки статуса: Get-Service linkedin-parser"
Write-Host "  • Для запуска парсера: python main.py -f urls.txt"
