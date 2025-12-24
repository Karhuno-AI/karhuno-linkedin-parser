"""Модуль для управления сессиями с ротацией User-Agents и cookies"""
import requests
import logging
import random
from typing import Optional, Dict, List
from requests.cookies import RequestsCookieJar
from config import Config

logger = logging.getLogger(__name__)


class SessionManager:
    """Класс для управления сессиями с ротацией User-Agents и cookies"""
    
    # Расширенный список User-Agents
    USER_AGENTS = [
        # Chrome на Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        
        # Chrome на Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        
        # Firefox на Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
        
        # Firefox на Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1; rv:121.0) Gecko/20100101 Firefox/121.0",
        
        # Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        
        # Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    ]
    
    def __init__(self, config: Config):
        """
        Инициализация SessionManager
        
        Args:
            config: Объект конфигурации
        """
        self.config = config
        self.sessions: Dict[str, requests.Session] = {}
        self.session_count = 0
        self.user_agents = config.get('user_agents', self.USER_AGENTS)
        self.max_sessions = config.get('session.max_sessions', 10)
        
        # Инициализируем первую сессию
        self._create_session()
    
    def _create_session(self) -> str:
        """
        Создание новой сессии
        
        Returns:
            ID сессии
        """
        session_id = f"session_{self.session_count}"
        self.session_count += 1
        
        session = requests.Session()
        
        # Устанавливаем случайный User-Agent
        session.headers.update({
            'User-Agent': random.choice(self.user_agents)
        })
        
        # Базовые заголовки для браузера
        session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        self.sessions[session_id] = session
        logger.info(f"Создана новая сессия {session_id} с User-Agent: {session.headers['User-Agent']}")
        
        return session_id
    
    def get_session(self) -> requests.Session:
        """
        Получить сессию с ротацией
        
        Returns:
            Объект сессии requests
        """
        # Если сессий меньше максимального количества, создаем новую
        if len(self.sessions) < self.max_sessions:
            # 30% вероятность создать новую сессию
            if random.random() < 0.3:
                self._create_session()
        
        # Выбираем случайную сессию
        session_id = random.choice(list(self.sessions.keys()))
        session = self.sessions[session_id]
        
        # Время от времени обновляем User-Agent в сессии
        if random.random() < 0.2:  # 20% вероятность
            session.headers['User-Agent'] = random.choice(self.user_agents)
            logger.debug(f"Обновлен User-Agent в {session_id}: {session.headers['User-Agent']}")
        
        return session
    
    def get_session_with_id(self, session_id: str) -> Optional[requests.Session]:
        """
        Получить конкретную сессию по ID
        
        Args:
            session_id: ID сессии
            
        Returns:
            Объект сессии или None
        """
        return self.sessions.get(session_id)
    
    def rotate_user_agent(self, session_id: Optional[str] = None):
        """
        Ротировать User-Agent в сессии
        
        Args:
            session_id: ID сессии (если None, ротируем все сессии)
        """
        if session_id:
            if session_id in self.sessions:
                self.sessions[session_id].headers['User-Agent'] = random.choice(self.user_agents)
                logger.debug(f"Обновлен User-Agent в {session_id}")
        else:
            # Обновляем User-Agent во всех сессиях
            for sid, session in self.sessions.items():
                session.headers['User-Agent'] = random.choice(self.user_agents)
            logger.debug("Обновлены User-Agents во всех сессиях")
    
    def clear_cookies(self, session_id: Optional[str] = None):
        """
        Очистить cookies в сессии
        
        Args:
            session_id: ID сессии (если None, очищаем все)
        """
        if session_id:
            if session_id in self.sessions:
                self.sessions[session_id].cookies.clear()
                logger.info(f"Очищены cookies в {session_id}")
        else:
            # Очищаем cookies во всех сессиях
            for session in self.sessions.values():
                session.cookies.clear()
            logger.info("Очищены cookies во всех сессиях")
    
    def rotate_session(self) -> requests.Session:
        """
        Получить сессию и ротировать User-Agent
        
        Returns:
            Объект сессии с ротированным User-Agent
        """
        session = self.get_session()
        
        # Периодически обновляем User-Agent
        if random.random() < 0.15:  # 15% вероятность
            self.rotate_user_agent()
        
        return session
    
    def create_new_session_for_ip(self, ip: str) -> requests.Session:
        """
        Создать новую сессию для конкретного IP
        
        Args:
            ip: IP адрес
            
        Returns:
            Новая сессия
        """
        session_id = f"session_{self.session_count}_{ip.replace('.', '_')}"
        self.session_count += 1
        
        session = requests.Session()
        
        # Устанавливаем случайный User-Agent
        session.headers.update({
            'User-Agent': random.choice(self.user_agents)
        })
        
        # Базовые заголовки
        session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'X-Forwarded-For': ip,  # Добавляем заголовок для маскировки IP
        })
        
        self.sessions[session_id] = session
        logger.info(f"Создана сессия {session_id} для IP {ip}")
        
        return session
    
    def get_stats(self) -> Dict:
        """
        Получить статистику сессий
        
        Returns:
            Словарь со статистикой
        """
        stats = {
            'total_sessions': len(self.sessions),
            'sessions': {}
        }
        
        for session_id, session in self.sessions.items():
            stats['sessions'][session_id] = {
                'user_agent': session.headers.get('User-Agent', 'Unknown'),
                'cookies_count': len(session.cookies),
                'cookie_jar_size': len(str(session.cookies))
            }
        
        return stats
    
    def clear_all_sessions(self):
        """Очистить все сессии и создать новую"""
        logger.info(f"Очищено {len(self.sessions)} сессий")
        self.sessions.clear()
        self._create_session()
    
    def remove_session(self, session_id: str):
        """
        Удалить конкретную сессию
        
        Args:
            session_id: ID сессии
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Удалена сессия {session_id}")
