# -*- coding: utf-8 -*-
import os
import sqlite3
import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === ИМПОРТЫ AIOGRAM ===
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

# Импорт config.py
try:
    from config import *
    logger.info("✅ Конфиг загружен")
except Exception as e:
    logger.error(f"❌ Ошибка загрузки конфига: {e}")
    raise

# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ====================

try:
    # Используем BOT_TOKEN из конфига
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    logger.info(f"✅ Бот {NICNAME} инициализирован")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации бота: {e}")
    raise

# ==================== ИНИЦИАЛИЗАЦИЯ ДИСПЕТЧЕРА ====================

dp = Dispatcher()

# ==================== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ====================

class Database:
    def __init__(self, db_path: str = 'database.db'):
        self.db_path = db_path
        self.connection = None
        self.connect()
        self.init_all_tables()
    
    def connect(self):
        """Устанавливает соединение с базой данных"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            logger.info("✅ База данных подключена")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к БД: {e}")
    
    def init_all_tables(self):
        """Инициализирует все таблицы в базе данных"""
        try:
            cursor = self.connection.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    balance REAL DEFAULT 0.0,
                    total_deposit REAL DEFAULT 0.0,
                    total_withdraw REAL DEFAULT 0.0,
                    total_wins REAL DEFAULT 0.0,
                    total_losses REAL DEFAULT 0.0,
                    referral_id INTEGER DEFAULT 0,
                    referrals_count INTEGER DEFAULT 0,
                    referral_earnings REAL DEFAULT 0.0,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_blocked INTEGER DEFAULT 0,
                    block_reason TEXT DEFAULT '',
                    kyc_verified INTEGER DEFAULT 0,
                    vip_level TEXT DEFAULT 'STANDARD'
                )
            ''')
            
            # Таблица депозитов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS deposits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    currency TEXT DEFAULT 'USDT',
                    status TEXT DEFAULT 'pending',
                    payment_method TEXT,
                    invoice_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            ''')
            
            # Таблица выводов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    currency TEXT DEFAULT 'USDT',
                    wallet_address TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP
                )
            ''')
            
            # Таблица ставок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    game_type TEXT,
                    amount REAL,
                    outcome TEXT,
                    multiplier REAL,
                    result TEXT,
                    win_amount REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица промокодов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS promo_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE,
                    amount REAL,
                    max_uses INTEGER,
                    used_count INTEGER DEFAULT 0,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            
            # Таблица активаций промокодов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS promo_activations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    promo_code TEXT,
                    activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица коэффициентов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS coefficients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    value REAL,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица статистики
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE,
                    total_deposits REAL DEFAULT 0.0,
                    total_withdrawals REAL DEFAULT 0.0,
                    total_bets REAL DEFAULT 0.0,
                    total_wins REAL DEFAULT 0.0,
                    total_losses REAL DEFAULT 0.0,
                    new_users INTEGER DEFAULT 0,
                    active_users INTEGER DEFAULT 0
                )
            ''')
            
            # Таблица фейк игр
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fake_games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    enabled INTEGER DEFAULT 1,
                    min_interval INTEGER DEFAULT 30,
                    max_interval INTEGER DEFAULT 120,
                    min_bet REAL DEFAULT 1.0,
                    max_bet REAL DEFAULT 100.0,
                    win_chance INTEGER DEFAULT 40,
                    last_run TIMESTAMP
                )
            ''')
            
            self.connection.commit()
            logger.info("✅ Все таблицы инициализированы")
            
            # Инициализация коэффициентов
            self.init_default_coefficients()
            
            # Инициализация фейк игр
            self.init_fake_games()
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации таблиц: {e}")
    
    def init_default_coefficients(self):
        """Инициализирует коэффициенты по умолчанию"""
        try:
            cursor = self.connection.cursor()
            
            # Используем коэффициенты из конфига
            default_coefficients = [
                ('KEF1', DEFAULT_KEF['KEF1'], 'Коэффициент для больше/меньше'),
                ('KEF2', DEFAULT_KEF['KEF2'], 'Коэффициент для точного числа'),
                ('KEF5', DEFAULT_KEF['KEF5'], 'Коэффициент для чет/нечет'),
                ('KEF6', DEFAULT_KEF['KEF6'], 'Коэффициент для джекпота'),
                ('KEF7', DEFAULT_KEF['KEF7'], 'Коэффициент для большого выигрыша'),
                ('KEF8', DEFAULT_KEF['KEF8'], 'Коэффициент для среднего выигрыша'),
                ('KEF9', DEFAULT_KEF['KEF9'], 'Коэффициент для малого выигрыша'),
                ('KEF10', DEFAULT_KEF['KEF10'], 'Коэффициент для баскетбола гол'),
                ('KEF11', DEFAULT_KEF['KEF11'], 'Коэффициент для баскетбола мимо'),
                ('KEF12', DEFAULT_KEF['KEF12'], 'Коэффициент для футбола гол'),
                ('KEF13', DEFAULT_KEF['KEF13'], 'Коэффициент для футбола мимо'),
                ('KEF15', DEFAULT_KEF['KEF15'], 'Коэффициент для КНБ'),
                ('KEF16', DEFAULT_KEF['KEF16'], 'Коэффициент для красное/черное'),
                ('KEF17', DEFAULT_KEF['KEF17'], 'Коэффициент для зеленое'),
                ('KNB', DEFAULT_KEF['KNB'], 'Шанс победы в КНБ (%)')
            ]
            
            for name, value, description in default_coefficients:
                cursor.execute('''
                    INSERT OR IGNORE INTO coefficients (name, value, description)
                    VALUES (?, ?, ?)
                ''', (name, value, description))
            
            self.connection.commit()
            logger.info("✅ Коэффициенты инициализированы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации коэффициентов: {e}")
    
    def init_fake_games(self):
        """Инициализирует настройки фейк игр"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO fake_games (id, enabled, min_interval, max_interval, min_bet, max_bet, win_chance)
                VALUES (1, 1, ?, ?, ?, ?, ?)
            ''', (TIMER, TIMER, min(DIAPAZONE_AMOUNT), max(DIAPAZONE_AMOUNT), 40))
            self.connection.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации фейк игр: {e}")
    
    # ==================== МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ====================
    
    def user_exists(self, user_id: int) -> bool:
        """Проверяет существование пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"❌ Ошибка проверки пользователя: {e}")
            return False
    
    def add_users(self, user_id: int, referer_id: Optional[int] = None):
        """Добавляет нового пользователя"""
        try:
            cursor = self.connection.cursor()
            
            # Если пользователь уже существует, обновляем информацию
            if self.user_exists(user_id):
                cursor.execute('''
                    UPDATE users 
                    SET last_activity = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (user_id,))
            else:
                # Добавляем нового пользователя
                cursor.execute('''
                    INSERT INTO users (user_id, referral_id, registration_date, last_activity)
                    VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (user_id, referer_id if referer_id else 0))
                
                # Увеличиваем счетчик рефералов у реферера
                if referer_id and referer_id != user_id:
                    cursor.execute('''
                        UPDATE users 
                        SET referrals_count = referrals_count + 1 
                        WHERE user_id = ?
                    ''', (referer_id,))
            
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка добавления пользователя: {e}")
            return False
    
    def get_user_balance(self, user_id: int) -> float:
        """Получает баланс пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return result['balance'] if result else 0.0
        except Exception as e:
            logger.error(f"❌ Ошибка получения баланса: {e}")
            return 0.0
    
    def update_user_balance(self, user_id: int, new_balance: float) -> bool:
        """Обновляет баланс пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                UPDATE users 
                SET balance = ?, last_activity = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (new_balance, user_id))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка обновления баланса: {e}")
            return False
    
    def deduct_from_user_balance(self, user_id: int, amount: float) -> bool:
        """Списывает средства с баланса пользователя"""
        try:
            balance = self.get_user_balance(user_id)
            if balance < amount:
                return False
            
            new_balance = balance - amount
            return self.update_user_balance(user_id, new_balance)
        except Exception as e:
            logger.error(f"❌ Ошибка списания средств: {e}")
            return False
    
    def add_to_user_balance(self, user_id: int, amount: float) -> bool:
        """Пополняет баланс пользователя"""
        try:
            balance = self.get_user_balance(user_id)
            new_balance = balance + amount
            return self.update_user_balance(user_id, new_balance)
        except Exception as e:
            logger.error(f"❌ Ошибка пополнения баланса: {e}")
            return False
    
    # ==================== МЕТОДЫ ДЛЯ ПРОМОКОДОВ ====================
    
    def activate_promo_code(self, user_id: int, code: str) -> dict:
        """Активирует промокод"""
        try:
            cursor = self.connection.cursor()
            
            # Проверяем существование промокода
            cursor.execute('''
                SELECT amount, max_uses, used_count, expires_at, is_active 
                FROM promo_codes 
                WHERE code = ?
            ''', (code,))
            
            promo = cursor.fetchone()
            if not promo:
                return {'success': False, 'message': 'Промокод не найден'}
            
            # Проверяем активность промокода
            if not promo['is_active']:
                return {'success': False, 'message': 'Промокод не активен'}
            
            # Проверяем срок действия
            if promo['expires_at']:
                expires_at = datetime.strptime(promo['expires_at'], '%Y-%m-%d %H:%M:%S')
                if expires_at < datetime.now():
                    return {'success': False, 'message': 'Срок действия промокода истек'}
            
            # Проверяем лимит использования
            if promo['max_uses'] > 0 and promo['used_count'] >= promo['max_uses']:
                return {'success': False, 'message': 'Лимит использования промокода исчерпан'}
            
            # Проверяем, активировал ли пользователь уже этот промокод
            cursor.execute('''
                SELECT 1 FROM promo_activations 
                WHERE user_id = ? AND promo_code = ?
            ''', (user_id, code))
            
            if cursor.fetchone():
                return {'success': False, 'message': 'Вы уже активировали этот промокод'}
            
            # Активируем промокод
            cursor.execute('''
                UPDATE promo_codes 
                SET used_count = used_count + 1 
                WHERE code = ?
            ''', (code,))
            
            cursor.execute('''
                INSERT INTO promo_activations (user_id, promo_code)
                VALUES (?, ?)
            ''', (user_id, code))
            
            self.connection.commit()
            
            return {
                'success': True,
                'message': 'Промокод успешно активирован',
                'amount': promo['amount']
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка активации промокода: {e}")
            return {'success': False, 'message': f'Ошибка активации: {str(e)}'}
    
    def has_user_activated_promo(self, user_id: int, code: str) -> bool:
        """Проверяет, активировал ли пользователь промокод"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT 1 FROM promo_activations 
                WHERE user_id = ? AND promo_code = ?
            ''', (user_id, code))
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"❌ Ошибка проверки активации промокода: {e}")
            return False
    
    # ==================== МЕТОДЫ ДЛЯ КОЭФФИЦИЕНТОВ ====================
    
    def get_cur_KEF(self, name: str) -> float:
        """Получает текущий коэффициент"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT value FROM coefficients WHERE name = ?', (name,))
            result = cursor.fetchone()
            return result['value'] if result else DEFAULT_KEF.get(name, 1.0)
        except Exception as e:
            logger.error(f"❌ Ошибка получения коэффициента {name}: {e}")
            return DEFAULT_KEF.get(name, 1.0)
    
    def update_KEF(self, name: str, value: float) -> bool:
        """Обновляет коэффициент"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                UPDATE coefficients 
                SET value = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE name = ?
            ''', (value, name))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка обновления коэффициента {name}: {e}")
            return False
    
    # ==================== МЕТОДЫ ДЛЯ ФЕЙК ИГР ====================
    
    def get_fake_games_status(self) -> bool:
        """Получает статус фейк игр"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT enabled FROM fake_games WHERE id = 1')
            result = cursor.fetchone()
            return bool(result['enabled']) if result else True
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса фейк игр: {e}")
            return True
    
    def toggle_fake_games(self, enabled: bool) -> bool:
        """Включает/выключает фейк игры"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                UPDATE fake_games 
                SET enabled = ? 
                WHERE id = 1
            ''', (1 if enabled else 0,))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка переключения фейк игр: {e}")
            return False
    
    # ==================== МЕТОДЫ ДЛЯ СТАТИСТИКИ ====================
    
    def add_count_pay(self, user_id: int, text: str, amount: float):
        """Добавляет статистику платежа"""
        try:
            cursor = self.connection.cursor()
            
            if text == 'win':
                cursor.execute('''
                    UPDATE users 
                    SET total_wins = total_wins + ?, last_activity = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (amount, user_id))
            elif text == 'lose':
                cursor.execute('''
                    UPDATE users 
                    SET total_losses = total_losses + ?, last_activity = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (amount, user_id))
            
            self.connection.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка добавления статистики платежа: {e}")
    
    def add_count_pay_stats_day(self, text: str, amount: float):
        """Добавляет дневную статистику"""
        try:
            cursor = self.connection.cursor()
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Создаем запись на сегодня, если ее нет
            cursor.execute('''
                INSERT OR IGNORE INTO statistics (date)
                VALUES (?)
            ''', (today,))
            
            if text == 'win':
                cursor.execute('''
                    UPDATE statistics 
                    SET total_wins = total_wins + ? 
                    WHERE date = ?
                ''', (amount, today))
            elif text == 'lose':
                cursor.execute('''
                    UPDATE statistics 
                    SET total_losses = total_losses + ? 
                    WHERE date = ?
                ''', (amount, today))
            
            cursor.execute('''
                UPDATE statistics 
                SET total_bets = total_bets + ? 
                WHERE date = ?
            ''', (amount, today))
            
            self.connection.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка добавления дневной статистики: {e}")
    
    # ==================== ДРУГИЕ МЕТОДЫ ====================
    
    def get_all_users(self) -> list:
        """Получает всех пользователей"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT * FROM users ORDER BY registration_date DESC')
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Ошибка получения пользователей: {e}")
            return []
    
    def get_total_users(self) -> int:
        """Получает общее количество пользователей"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM users')
            result = cursor.fetchone()
            return result['count'] if result else 0
        except Exception as e:
            logger.error(f"❌ Ошибка получения общего количества пользователей: {e}")
            return 0
    
    def get_total_balance(self) -> float:
        """Получает общий баланс всех пользователей"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT SUM(balance) as total FROM users')
            result = cursor.fetchone()
            return result['total'] if result['total'] else 0.0
        except Exception as e:
            logger.error(f"❌ Ошибка получения общего баланса: {e}")
            return 0.0
    
    def get_total_deposits(self) -> float:
        """Получает общую сумму депозитов"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT SUM(amount) as total FROM deposits WHERE status = "completed"')
            result = cursor.fetchone()
            return result['total'] if result['total'] else 0.0
        except Exception as e:
            logger.error(f"❌ Ошибка получения общей суммы депозитов: {e}")
            return 0.0
    
    def get_total_withdrawals(self) -> float:
        """Получает общую сумму выводов"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT SUM(amount) as total FROM withdrawals WHERE status = "completed"')
            result = cursor.fetchone()
            return result['total'] if result['total'] else 0.0
        except Exception as e:
            logger.error(f"❌ Ошибка получения общей суммы выводов: {e}")
            return 0.0

# ==================== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ====================

try:
    db = Database()
    logger.info("✅ База данных инициализирована")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации БД: {e}")
    raise

# ==================== ИНИЦИАЛИЗАЦИЯ CRYPTOBOT ====================

crypto = None
if api_cryptobot:
    try:
        # Попробуем импортировать cryptobot_fast вместо cryptobot
        from cryptobot_fast import CryptoBotTurbo
        crypto = CryptoBotTurbo(api_cryptobot, False)  # Основная сеть
        logger.info("✅ CryptoBot API инициализирован (Turbo версия)")
    except ImportError:
        try:
            # Если cryptobot_fast нет, пробуем обычный cryptobot
            from cryptobot import CryptoBot
            crypto = CryptoBot(api_cryptobot, False)
            logger.info("✅ CryptoBot API инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации CryptoBot: {e}")
            crypto = None
else:
    logger.warning("⚠️ CryptoBot API ключ не указан, платежи через CryptoBot отключены")
    crypto = None

# ==================== ДРУГИЕ ИНИЦИАЛИЗАЦИИ ====================

lock = asyncio.Lock()

# Инициализация планировщика
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    logger.info("✅ Планировщик инициализирован")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации планировщика: {e}")
    scheduler = None

# Список админов
admin = ADMIN

# ==================== ПЛАТЕЖНАЯ ОЧЕРЕДЬ ====================

# Создаем пустую заглушку для payment_queue если он не определен в cryptobot_fast
try:
    from cryptobot_fast import PaymentQueue
    payment_queue = PaymentQueue()
    logger.info("✅ Платежная очередь инициализирована")
except ImportError:
    payment_queue = None
    logger.info("⚠️ Платежная очередь не доступна")

# ==================== ЭКСПОРТ ====================

__all__ = ['dp', 'db', 'bot', 'admin', 'lock', 'crypto', 'scheduler', 'payment_queue']