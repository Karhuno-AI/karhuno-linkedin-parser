"""Модуль для экспорта данных в JSON"""
import json
import os
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DataExporter:
    """Класс для экспорта данных профилей"""
    
    def __init__(self, output_dir='output'):
        """
        Инициализация DataExporter
        
        Args:
            output_dir: Директория для сохранения файлов
        """
        self.output_dir = output_dir
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """Создание директории для выходных файлов, если её нет"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Создана директория {self.output_dir}")
    
    def export_profile(self, profile_data: Dict[str, Any], public_identifier: str = None) -> str:
        """
        Экспорт данных профиля в JSON файл
        
        Args:
            profile_data: Данные профиля в формате словаря
            public_identifier: Идентификатор профиля для имени файла
            
        Returns:
            Путь к сохраненному файлу
        """
        # Определяем имя файла
        if public_identifier:
            filename = f"{public_identifier}.json"
        elif 'element' in profile_data and 'publicIdentifier' in profile_data['element']:
            filename = f"{profile_data['element']['publicIdentifier']}.json"
        else:
            filename = f"profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # Сохранение в JSON с красивым форматированием
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Профиль сохранен в {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Ошибка сохранения профиля: {e}")
            raise
    
    def validate_structure(self, profile_data: Dict[str, Any]) -> bool:
        """
        Валидация структуры данных профиля
        
        Args:
            profile_data: Данные профиля для проверки
            
        Returns:
            True если структура валидна
        """
        required_keys = ['element']
        
        if not all(key in profile_data for key in required_keys):
            logger.warning("Отсутствуют обязательные ключи в структуре данных")
            return False
        
        return True

