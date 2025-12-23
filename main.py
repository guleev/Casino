# -*- coding: utf-8 -*-
import datetime
import asyncio
import random
import logging
import os
import sys
import time
from typing import Optional, Dict, List, Any, Union, Tuple
import sqlite3
import pytz
import json
from string import digits
from contextlib import asynccontextmanager
import hashlib
import base64
import inspect
import traceback
import html

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==================== ИМПОРТЫ AIOGRAM 2.25.1 ====================
try:
    from aiogram import Bot, Dispatcher, types
    from aiogram.dispatcher import FSMContext
    from aiogram.contrib.fsm_storage.memory import MemoryStorage
    from aiogram.types import (
        Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup,
        InlineKeyboardButton, InlineKeyboardMarkup, InputFile,
        BotCommand, BotCommandScopeDefault, ReplyKeyboardRemove, ContentType,
        PreCheckoutQuery, SuccessfulPayment, LabeledPrice, ShippingOption,
        ShippingQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
        ChatJoinRequest, Dice, ParseMode, InputMediaPhoto, InputMediaVideo,
        InputMediaAudio, InputMediaDocument
    )
    from aiogram.dispatcher.filters import Command, Text, CommandStart
    from aiogram.dispatcher.filters.state import State, StatesGroup
    from aiogram.utils.markdown import hbold, hlink, hcode, hitalic, text
    from aiogram.utils.exceptions import TelegramAPIError, MessageNotModified, CantParseEntities
    from aiogram.utils import executor
    from aiogram.contrib.middlewares.logging import LoggingMiddleware
    logger.info("✅ Aiogram 2.25.1 импортирован")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта aiogram: {e}")
    sys.exit(1)

# ==================== ИМПОРТ ДРУГИХ БИБЛИОТЕК ====================
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    logger.info("✅ APScheduler импортирован")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта APScheduler: {e}")
    scheduler = None

# ==================== ИМПОРТ КОНФИГА ====================
try:
    from config import *
    logger.info("✅ Конфиг загружен")
    
    # Проверка обязательных переменных
    required_vars = ['BOT_TOKEN', 'ADMIN', 'MIN_STAVKA']
    for var in required_vars:
        if var not in globals():
            logger.error(f"❌ Отсутствует обязательная переменная: {var}")
            sys.exit(1)
    
    # Специальная проверка для channel_id (исправление опечатки channal_id → channel_id)
    if 'channel_id' not in globals():
        if 'channal_id' in globals():
            # Если есть channal_id, используем его как channel_id
            channel_id = channal_id
            logger.info("⚠️  Исправлена опечатка: channal_id → channel_id")
        else:
            logger.error("❌ Отсутствует обязательная переменная: channel_id или channal_id")
            sys.exit(1)
            
except ImportError as e:
    logger.error(f"❌ Ошибка загрузки конфига: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"❌ Ошибка в конфиге: {e}")
    sys.exit(1)

# ==================== НАСТРОЙКА ПУТЕЙ К ФОТО ====================
PHOTO_DIR = 'photos/'

# Создаем директорию для фото если её нет
if not os.path.exists(PHOTO_DIR):
    os.makedirs(PHOTO_DIR)
    logger.info(f"✅ Создана директория {PHOTO_DIR}")

# Маппинг фото к функциям
PHOTO_MAPPING = {
    # Основные фото
    'start': 'welcome.jpg',
    'menu': 'menu.jpg',
    'balance': 'balance.jpg',
    'profile': 'profile.jpg',
    
    # Игры
    'game': 'game.jpg',
    'dice': 'dice.jpg',
    'slots': 'slots.jpg',
    'football': 'football.jpg',
    'basketball': 'basketball.jpg',
    'knb': 'knb.jpg',
    'roulette': 'roulette.jpg',
    'games': 'games.jpg',
    
    # Финансы
    'enter_amount': 'enter_the_amount.jpg',
    'wallet': 'wallet.jpg',
    'deposit': 'replenishment.jpg',
    'withdraw': 'conclusion.jpg',
    'withdraw_admin': 'conclusion_admin.jpg',
    
    # Результаты
    'success': 'success.jpg',
    'error': 'error.jpg',
    'result': 'result.jpg',
    'win': 'Wins.jpg',
    'lose': 'Lose.jpg',
    
    # Админка
    'admin': 'admin.jpg',
    'stats': 'stats.jpg',
    'stats_user': 'stats_user.jpg',
    'promo': 'promo.jpg',
    'add_balance': 'add_balance.jpg',
    'kef_edit': 'kef_edit.jpg',
    'urls': 'urls.jpg',
    'referral': 'referral.jpg',
    'info': 'info.jpg',
}

def get_photo_path(photo_type: str) -> Optional[str]:
    """Получение пути к фото"""
    if photo_type not in PHOTO_MAPPING:
        return None
    
    photo_file = PHOTO_MAPPING[photo_type]
    photo_path = os.path.join(PHOTO_DIR, photo_file)
    
    if not os.path.exists(photo_path):
        logger.warning(f"⚠️ Фото не найдено: {photo_path}")
        return None
    
    return photo_path

async def send_photo_message(chat_id: int, photo_type: str, caption: str = "", 
                           reply_markup=None, parse_mode=ParseMode.HTML):
    """Отправка сообщения с фото"""
    try:
        photo_path = get_photo_path(photo_type)
        
        if photo_path:
            with open(photo_path, 'rb') as photo:
                return await bot.send_photo(
                    chat_id=chat_id,
                    photo=types.InputFile(photo_path),
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
        else:
            # Если фото нет, отправляем просто текст
            logger.warning(f"⚠️ Фото {photo_type} не найдено, отправляю текст")
            return await bot.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
    except Exception as e:
        logger.error(f"❌ Ошибка отправки фото {photo_type}: {e}")
        # Фолбэк на текстовое сообщение
        return await bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

async def edit_message_with_photo(callback: CallbackQuery, photo_type: str, caption: str = "",
                                reply_markup=None, parse_mode=ParseMode.HTML):
    """Редактирование сообщения с заменой на фото"""
    try:
        photo_path = get_photo_path(photo_type)
        
        if photo_path:
            # Удаляем старое сообщение и отправляем новое с фото
            await callback.message.delete()
            return await send_photo_message(
                callback.message.chat.id,
                photo_type,
                caption,
                reply_markup,
                parse_mode
            )
        else:
            # Если фото нет, редактируем текст
            return await callback.message.edit_text(
                text=caption,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
    except Exception as e:
        logger.error(f"❌ Ошибка редактирования с фото {photo_type}: {e}")
        return await callback.message.edit_text(
            text=caption,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ====================
try:
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    logger.info(f"✅ Бот инициализирован")
    
    # Проверка токена
    async def check_bot_token():
        try:
            me = await bot.get_me()
            logger.info(f"🤖 Бот: @{me.username} (ID: {me.id})")
            return True
        except Exception as e:
            logger.error(f"❌ Неверный токен бота: {e}")
            return False
    
except Exception as e:
    logger.error(f"❌ Ошибка инициализации бота: {e}")
    sys.exit(1)

# ==================== ИНИЦИАЛИЗАЦИЯ ДИСПЕТЧЕРА ====================
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# ==================== БАЗА ДАННЫХ (ПОЛНАЯ ВЕРСИЯ) ====================
class Database:
    def __init__(self, db_path: str = 'casino.db'):
        self.db_path = db_path
        self.connection = None
        self.lock = asyncio.Lock()
        self.init_database()
    
    def init_database(self):
        """Инициализация всей базы данных с ВСЕМИ таблицами"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            cursor = self.connection.cursor()
            
            # ========== ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ ==========
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
                    total_bets INTEGER DEFAULT 0,
                    total_bet_amount REAL DEFAULT 0.0,
                    referral_id INTEGER DEFAULT 0,
                    referrals_count INTEGER DEFAULT 0,
                    referral_earnings REAL DEFAULT 0.0,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_deposit TIMESTAMP,
                    last_withdraw TIMESTAMP,
                    is_blocked INTEGER DEFAULT 0,
                    block_reason TEXT DEFAULT '',
                    language_code TEXT DEFAULT 'ru',
                    phone_number TEXT,
                    email TEXT,
                    kyc_verified INTEGER DEFAULT 0,
                    kyc_data TEXT,
                    vip_level TEXT DEFAULT 'STANDARD',
                    vip_points INTEGER DEFAULT 0,
                    daily_bonus_claimed INTEGER DEFAULT 0,
                    last_daily_bonus TIMESTAMP,
                    achievements TEXT DEFAULT '[]',
                    settings TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}'
                )
            ''')
            
            # Индексы для пользователей
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_balance ON users(balance)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_registration ON users(registration_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_id)')
            
            # ========== ТАБЛИЦА СТАВОК ==========
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    game_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USDT',
                    outcome TEXT NOT NULL,
                    result TEXT NOT NULL,
                    win_amount REAL DEFAULT 0.0,
                    multiplier REAL DEFAULT 1.0,
                    dice_value INTEGER,
                    is_fake INTEGER DEFAULT 0,
                    channel_message_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bets_user ON bets(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bets_date ON bets(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bets_game ON bets(game_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bets_result ON bets(result)')
            
            # ========== ТАБЛИЦА ДЕПОЗИТОВ ==========
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS deposits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USDT',
                    payment_method TEXT,
                    status TEXT DEFAULT 'pending',
                    invoice_id TEXT UNIQUE,
                    invoice_url TEXT,
                    tx_hash TEXT,
                    address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    confirmed_at TIMESTAMP,
                    cancelled_at TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            
            # ========== ТАБЛИЦА ВЫВОДОВ ==========
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USDT',
                    wallet_address TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    tx_hash TEXT,
                    admin_id INTEGER,
                    admin_comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    cancelled_at TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            
            # ========== ТАБЛИЦА ПРОМОКОДОВ ==========
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS promo_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    amount REAL NOT NULL,
                    bonus_type TEXT DEFAULT 'fixed',
                    max_uses INTEGER DEFAULT 0,
                    used_count INTEGER DEFAULT 0,
                    min_deposit REAL DEFAULT 0,
                    min_bet REAL DEFAULT 0,
                    expires_at TIMESTAMP,
                    starts_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    is_public INTEGER DEFAULT 0,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    restrictions TEXT DEFAULT '{}'
                )
            ''')
            
            # ========== ТАБЛИЦА АКТИВАЦИЙ ПРОМОКОДОВ ==========
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS promo_activations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    promo_code TEXT NOT NULL,
                    amount REAL NOT NULL,
                    activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (promo_code) REFERENCES promo_codes(code) ON DELETE CASCADE
                )
            ''')
            
            # ========== ТАБЛИЦА КОЭФФИЦИЕНТОВ ==========
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS coefficients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    value REAL NOT NULL,
                    min_value REAL DEFAULT 0,
                    max_value REAL DEFAULT 100,
                    description TEXT,
                    category TEXT DEFAULT 'general',
                    is_editable INTEGER DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_by INTEGER
                )
            ''')
            
            # ========== ТАБЛИЦА ФЕЙК ИГР ==========
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fake_games (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    enabled INTEGER DEFAULT 1,
                    min_interval INTEGER DEFAULT 30,
                    max_interval INTEGER DEFAULT 120,
                    min_bet REAL DEFAULT 1.0,
                    max_bet REAL DEFAULT 100.0,
                    win_chance INTEGER DEFAULT 40,
                    max_concurrent INTEGER DEFAULT 3,
                    last_run TIMESTAMP,
                    settings TEXT DEFAULT '{}',
                    statistics TEXT DEFAULT '{}'
                )
            ''')
            
            # ========== ТАБЛИЦА СТАТИСТИКИ ==========
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    total_users INTEGER DEFAULT 0,
                    new_users INTEGER DEFAULT 0,
                    active_users INTEGER DEFAULT 0,
                    total_deposits INTEGER DEFAULT 0,
                    total_deposit_amount REAL DEFAULT 0.0,
                    total_withdrawals INTEGER DEFAULT 0,
                    total_withdraw_amount REAL DEFAULT 0.0,
                    total_bets INTEGER DEFAULT 0,
                    total_bet_amount REAL DEFAULT 0.0,
                    winning_bets INTEGER DEFAULT 0,
                    losing_bets INTEGER DEFAULT 0,
                    total_win_amount REAL DEFAULT 0.0,
                    total_loss_amount REAL DEFAULT 0.0,
                    profit REAL DEFAULT 0.0,
                    referral_payments INTEGER DEFAULT 0,
                    referral_amount REAL DEFAULT 0.0,
                    promo_activations INTEGER DEFAULT 0,
                    promo_amount REAL DEFAULT 0.0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ========== ТАБЛИЦА ТРАНЗАКЦИЙ ==========
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USDT',
                    balance_before REAL NOT NULL,
                    balance_after REAL NOT NULL,
                    description TEXT,
                    reference_id INTEGER,
                    reference_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            
            # ========== ТАБЛИЦА СООБЩЕНИЙ ==========
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message_type TEXT NOT NULL,
                    text TEXT NOT NULL,
                    media_id TEXT,
                    media_type TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    delivered INTEGER DEFAULT 0,
                    read INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            
            # ========== ТАБЛИЦА ЛОГОВ ==========
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    module TEXT NOT NULL,
                    function TEXT NOT NULL,
                    message TEXT NOT NULL,
                    user_id INTEGER,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ========== ТАБЛИЦА НАСТРОЕК ==========
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    category TEXT DEFAULT 'general',
                    is_public INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ========== ТАБЛИЦА ССЫЛОК ==========
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS urls (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    title TEXT,
                    description TEXT,
                    category TEXT DEFAULT 'general',
                    is_active INTEGER DEFAULT 1,
                    order_index INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ========== ТАБЛИЦА УВЕДОМЛЕНИЙ ==========
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    is_read INTEGER DEFAULT 0,
                    is_important INTEGER DEFAULT 0,
                    action_url TEXT,
                    action_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            
            # ========== ТАБЛИЦА АЧИВКОВ ==========
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    icon TEXT,
                    condition_type TEXT NOT NULL,
                    condition_value REAL NOT NULL,
                    reward_type TEXT,
                    reward_value REAL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    achievement_id INTEGER NOT NULL,
                    progress REAL DEFAULT 0,
                    is_completed INTEGER DEFAULT 0,
                    completed_at TIMESTAMP,
                    reward_claimed INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE,
                    UNIQUE(user_id, achievement_id)
                )
            ''')
            
            self.connection.commit()
            
            # Инициализация данных по умолчанию
            self.init_default_data()
            
            logger.info("✅ База данных инициализирована с 15 таблицами")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД: {e}")
            raise
    
    def init_default_data(self):
        """Инициализация данных по умолчанию"""
        try:
            cursor = self.connection.cursor()
            
            # Коэффициенты по умолчанию
            default_coefficients = [
                ('KEF1', 2.0, 'Больше/Меньше'),
                ('KEF2', 6.0, 'Точное число'),
                ('KEF3', 2.0, 'Чет/Нечет'),
                ('KEF4', 4.0, 'Дуэль'),
                ('KEF5', 2.0, 'Красное/Черное'),
                ('KEF6', 14.0, 'Зеленое'),
                ('KEF7', 5.0, '3 одинаковых'),
                ('KEF8', 10.0, '2 одинаковых'),
                ('KEF9', 20.0, 'Джекпот'),
                ('KEF10', 2.5, 'Баскетбол гол'),
                ('KEF11', 2.5, 'Баскетбол мимо'),
                ('KEF12', 2.5, 'Футбол гол'),
                ('KEF13', 2.5, 'Футбол мимо'),
                ('KEF14', 6.0, 'Блэкджек'),
                ('KEF15', 3.0, 'КНБ'),
                ('KEF16', 2.0, 'Рулетка красное'),
                ('KEF17', 14.0, 'Рулетка зеленое'),
                ('KNB_CHANCE', 50.0, 'Шанс победы в КНБ (%)'),
                ('CASHBACK', 10.0, 'Кэшбэк (%)'),
                ('REFERRAL', 20.0, 'Реферальный процент (%)'),
                ('WELCOME_BONUS', 10.0, 'Приветственный бонус (%)'),
                ('MIN_BET', 0.1, 'Минимальная ставка'),
                ('MAX_BET', 30.0, 'Максимальная ставка'),
                ('MIN_WITHDRAW', 1.0, 'Минимальный вывод')
            ]
            
            for name, value, description in default_coefficients:
                cursor.execute('''
                    INSERT OR IGNORE INTO coefficients (name, value, description)
                    VALUES (?, ?, ?)
                ''', (name, value, description))
            
            # Настройки фейк игр
            cursor.execute('''
                INSERT OR IGNORE INTO fake_games (id, enabled, min_interval, max_interval, min_bet, max_bet, win_chance)
                VALUES (1, 1, ?, ?, ?, ?, ?)
            ''', (TIMER, TIMER, min(DIAPAZONE_AMOUNT), max(DIAPAZONE_AMOUNT), 40))
            
            # Ссылки по умолчанию
            default_urls = [
                ('news', 'https://t.me/noxwat', 'Новостной канал', 'Последние новости казино'),
                ('support', f'https://t.me/{ADMIN_USERNAME[1:]}', 'Поддержка', 'Связь с администрацией'),
                ('rules', 'https://telegra.ph/Pravila-Noxwat-Casino-01-20', 'Правила', 'Правила использования'),
                ('payments', 'https://t.me/NoxwatPayments', 'Выплаты', 'Канал с выплатами'),
                ('games', 'https://t.me/noxwatgames', 'Игры', 'Игровой канал'),
                ('faq', 'https://teletype.in/@oeaow-144350/tsIRVcpdqg', 'FAQ', 'Частые вопросы'),
                ('referral', URL_BOT, 'Реферальная программа', 'Приглашай друзей и получай бонусы')
            ]
            
            for url_id, url, title, description in default_urls:
                cursor.execute('''
                    INSERT OR IGNORE INTO urls (id, url, title, description)
                    VALUES (?, ?, ?, ?)
                ''', (url_id, url, title, description))
            
            # Настройки по умолчанию
            default_settings = [
                ('BOT_NAME', NAME_CASINO, 'Название бота'),
                ('SUPPORT_USERNAME', SUPPORT_USERNAME, 'Username поддержки'),
                ('WORK_HOURS', WORK_HOURS, 'Часы работы поддержки'),
                ('RESPONSE_TIME', RESPONSE_TIME, 'Время ответа поддержки'),
                ('CURRENCY', 'USDT', 'Основная валюта'),
                ('DEFAULT_LANGUAGE', 'ru', 'Язык по умолчанию'),
                ('MAINTENANCE_MODE', '0', 'Режим техобслуживания'),
                ('REGISTRATION_ENABLED', '1', 'Регистрация новых пользователей'),
                ('WITHDRAWAL_ENABLED', '1', 'Вывод средств'),
                ('DEPOSIT_ENABLED', '1', 'Пополнение баланса'),
                ('BETTING_ENABLED', '1', 'Делать ставки'),
                ('REFERRAL_ENABLED', '1', 'Реферальная программа'),
                ('PROMO_ENABLED', '1', 'Промокоды'),
                ('CAPTCHA_ENABLED', '0', 'Капча при регистрации'),
                ('KYC_ENABLED', '0', 'Верификация KYC')
            ]
            
            for key, value, description in default_settings:
                cursor.execute('''
                    INSERT OR IGNORE INTO settings (key, value, description)
                    VALUES (?, ?, ?)
                ''', (key, value, description))
            
            # Ачивки по умолчанию
            default_achievements = [
                ('first_deposit', 'Первый депозит', 'Пополните баланс в первый раз', '💰', 'deposit_count', 1, 'balance', 5),
                ('first_bet', 'Первая ставка', 'Сделайте первую ставку', '🎲', 'bet_count', 1, 'balance', 2),
                ('first_win', 'Первая победа', 'Выиграйте первую ставку', '🏆', 'win_count', 1, 'balance', 10),
                ('deposit_100', 'Крупный инвестор', 'Пополните баланс на 100$', '💎', 'deposit_total', 100, 'balance', 20),
                ('bet_50', 'Азартный игрок', 'Сделайте 50 ставок', '🎰', 'bet_count', 50, 'balance', 25),
                ('referral_5', 'Вербовщик', 'Пригласите 5 друзей', '👥', 'referral_count', 5, 'balance', 50),
                ('win_streak_5', 'Удачливый', '5 побед подряд', '🔥', 'win_streak', 5, 'balance', 30),
                ('vip_member', 'VIP игрок', 'Достигните VIP уровня', '👑', 'vip_level', 1, 'vip_points', 100)
            ]
            
            for name, title, desc, icon, cond_type, cond_value, reward_type, reward_value in default_achievements:
                cursor.execute('''
                    INSERT OR IGNORE INTO achievements (name, title, description, icon, condition_type, condition_value, reward_type, reward_value)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, title, desc, icon, cond_type, cond_value, reward_type, reward_value))
            
            # Статистика на сегодня
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                INSERT OR IGNORE INTO statistics (date)
                VALUES (?)
            ''', (today,))
            
            self.connection.commit()
            logger.info("✅ Данные по умолчанию инициализированы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации данных: {e}")
    
    # ==================== МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ====================
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, 
                 last_name: str = None, referer_id: int = None, language_code: str = 'ru') -> bool:
        """Добавление нового пользователя"""
        try:
            cursor = self.connection.cursor()
            
            if self.user_exists(user_id):
                # Обновляем данные существующего пользователя
                cursor.execute('''
                    UPDATE users 
                    SET username = ?, first_name = ?, last_name = ?, language_code = ?, last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (username, first_name, last_name, language_code, user_id))
            else:
                # Добавляем нового пользователя
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name, referral_id, language_code, registration_date, last_activity)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (user_id, username, first_name, last_name, referer_id if referer_id else 0, language_code))
                
                # Обновляем статистику
                today = datetime.datetime.now().strftime('%Y-%m-%d')
                cursor.execute('''
                    UPDATE statistics 
                    SET total_users = total_users + 1, new_users = new_users + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE date = ?
                ''', (today,))
                
                # Увеличиваем счетчик рефералов у реферера
                if referer_id and referer_id != user_id:
                    cursor.execute('''
                        UPDATE users 
                        SET referrals_count = referrals_count + 1 
                        WHERE user_id = ?
                    ''', (referer_id,))
            
            self.connection.commit()
            self.log_action('USER', f'User {user_id} added/updated')
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления пользователя {user_id}: {e}")
            return False
    
    def user_exists(self, user_id: int) -> bool:
        """Проверка существования пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"❌ Ошибка проверки пользователя {user_id}: {e}")
            return False
    
    def get_user(self, user_id: int) -> Dict:
        """Получение информации о пользователе"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {}
        except Exception as e:
            logger.error(f"❌ Ошибка получения пользователя {user_id}: {e}")
            return {}
    
    def get_user_balance(self, user_id: int) -> float:
        """Получение баланса пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            return row['balance'] if row else 0.0
        except Exception as e:
            logger.error(f"❌ Ошибка получения баланса {user_id}: {e}")
            return 0.0
    
    async def update_balance(self, user_id: int, amount: float, transaction_type: str = 'adjustment', 
                          description: str = None, reference_id: int = None, reference_type: str = None) -> bool:
        """Обновление баланса пользователя с записью транзакции"""
        try:
            async with self.lock:
                cursor = self.connection.cursor()
                
                # Получаем текущий баланс
                cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                if not row:
                    return False
                
                balance_before = row['balance']
                balance_after = amount
                
                # Обновляем баланс
                cursor.execute('''
                    UPDATE users 
                    SET balance = ?, last_activity = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                ''', (balance_after, user_id))
                
                # Записываем транзакцию
                cursor.execute('''
                    INSERT INTO transactions (user_id, type, amount, balance_before, balance_after, description, reference_id, reference_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, transaction_type, balance_after - balance_before, balance_before, balance_after, 
                      description, reference_id, reference_type))
                
                # Обновляем статистику пользователя
                if transaction_type == 'deposit':
                    cursor.execute('''
                        UPDATE users 
                        SET total_deposit = total_deposit + ?, last_deposit = CURRENT_TIMESTAMP 
                        WHERE user_id = ?
                    ''', (amount - balance_before, user_id))
                elif transaction_type == 'withdraw':
                    cursor.execute('''
                        UPDATE users 
                        SET total_withdraw = total_withdraw + ?, last_withdraw = CURRENT_TIMESTAMP 
                        WHERE user_id = ?
                    ''', (balance_before - amount, user_id))
                elif transaction_type == 'win':
                    cursor.execute('''
                        UPDATE users 
                        SET total_wins = total_wins + ? 
                        WHERE user_id = ?
                    ''', (amount - balance_before, user_id))
                elif transaction_type == 'lose':
                    cursor.execute('''
                        UPDATE users 
                        SET total_losses = total_losses + ? 
                        WHERE user_id = ?
                    ''', (balance_before - amount, user_id))
                
                self.connection.commit()
                self.log_action('BALANCE', f'User {user_id} balance updated: {balance_before} -> {balance_after}')
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления баланса {user_id}: {e}")
            return False
    
    async def add_to_balance(self, user_id: int, amount: float, transaction_type: str = 'bonus', 
                          description: str = None, reference_id: int = None, reference_type: str = None) -> bool:
        """Пополнение баланса"""
        try:
            current_balance = self.get_user_balance(user_id)
            new_balance = current_balance + amount
            return await self.update_balance(user_id, new_balance, transaction_type, description, reference_id, reference_type)
        except Exception as e:
            logger.error(f"❌ Ошибка пополнения баланса {user_id}: {e}")
            return False
    
    async def deduct_from_balance(self, user_id: int, amount: float, transaction_type: str = 'bet', 
                               description: str = None, reference_id: int = None, reference_type: str = None) -> bool:
        """Списание с баланса"""
        try:
            current_balance = self.get_user_balance(user_id)
            if current_balance < amount:
                return False
            new_balance = current_balance - amount
            return await self.update_balance(user_id, new_balance, transaction_type, description, reference_id, reference_type)
        except Exception as e:
            logger.error(f"❌ Ошибка списания с баланса {user_id}: {e}")
            return False
    
    def update_user_activity(self, user_id: int) -> bool:
        """Обновление времени последней активности"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                UPDATE users 
                SET last_activity = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (user_id,))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка обновления активности {user_id}: {e}")
            return False
    
    # ==================== МЕТОДЫ ДЛЯ СТАВОК ====================
    
    def add_bet(self, user_id: int, game_type: str, amount: float, outcome: str, 
                result: str, win_amount: float = 0.0, multiplier: float = 1.0, 
                dice_value: int = None, is_fake: bool = False, channel_message_id: int = None) -> int:
        """Добавление ставки"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute('''
                INSERT INTO bets (user_id, game_type, amount, outcome, result, win_amount, multiplier, dice_value, is_fake, channel_message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, game_type, amount, outcome, result, win_amount, multiplier, dice_value, 1 if is_fake else 0, channel_message_id))
            
            bet_id = cursor.lastrowid
            
            # Обновляем статистику пользователя
            cursor.execute('''
                UPDATE users 
                SET total_bets = total_bets + 1, total_bet_amount = total_bet_amount + ?, last_activity = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (amount, user_id))
            
            # Обновляем общую статистику
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                UPDATE statistics 
                SET total_bets = total_bets + 1, total_bet_amount = total_bet_amount + ?,
                    winning_bets = winning_bets + ?, losing_bets = losing_bets + ?,
                    total_win_amount = total_win_amount + ?, total_loss_amount = total_loss_amount + ?,
                    profit = profit + ?, updated_at = CURRENT_TIMESTAMP
                WHERE date = ?
            ''', (amount, 
                  1 if result == 'win' else 0, 
                  1 if result == 'lose' else 0,
                  win_amount,
                  amount if result == 'lose' else 0,
                  (win_amount - amount) if result == 'win' else -amount,
                  today))
            
            self.connection.commit()
            self.log_action('BET', f'User {user_id} placed bet #{bet_id}: {amount}$ on {game_type} - {result}')
            return bet_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления ставки {user_id}: {e}")
            return 0
    
    def get_user_bets(self, user_id: int, limit: int = 10, offset: int = 0) -> List[Dict]:
        """Получение ставок пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT * FROM bets 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Ошибка получения ставок {user_id}: {e}")
            return []
    
    def get_bet_stats(self, user_id: int = None, game_type: str = None, date_from: str = None, date_to: str = None) -> Dict:
        """Статистика ставок"""
        try:
            cursor = self.connection.cursor()
            
            query = '''
                SELECT 
                    COUNT(*) as total_bets,
                    SUM(amount) as total_amount,
                    SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as win_count,
                    SUM(CASE WHEN result = 'lose' THEN 1 ELSE 0 END) as lose_count,
                    SUM(CASE WHEN result = 'win' THEN win_amount ELSE 0 END) as win_amount,
                    SUM(CASE WHEN result = 'lose' THEN amount ELSE 0 END) as lose_amount,
                    AVG(multiplier) as avg_multiplier
                FROM bets 
                WHERE 1=1
            '''
            params = []
            
            if user_id:
                query += ' AND user_id = ?'
                params.append(user_id)
            
            if game_type:
                query += ' AND game_type = ?'
                params.append(game_type)
            
            if date_from:
                query += ' AND DATE(created_at) >= ?'
                params.append(date_from)
            
            if date_to:
                query += ' AND DATE(created_at) <= ?'
                params.append(date_to)
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            if row:
                stats = dict(row)
                stats['profit'] = (stats['win_amount'] or 0) - (stats['lose_amount'] or 0)
                stats['win_rate'] = (stats['win_count'] / stats['total_bets'] * 100) if stats['total_bets'] > 0 else 0
                return stats
            
            return {
                'total_bets': 0,
                'total_amount': 0,
                'win_count': 0,
                'lose_count': 0,
                'win_amount': 0,
                'lose_amount': 0,
                'profit': 0,
                'win_rate': 0,
                'avg_multiplier': 0
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики ставок: {e}")
            return {}
    
    # ==================== МЕТОДЫ ДЛЯ ПРОМОКОДОВ ====================
    
    def create_promo_code(self, code: str, amount: float, bonus_type: str = 'fixed', 
                         max_uses: int = 0, expires_at: str = None, created_by: int = None,
                         description: str = None, restrictions: Dict = None) -> bool:
        """Создание промокода"""
        try:
            cursor = self.connection.cursor()
            
            restrictions_json = json.dumps(restrictions or {})
            
            cursor.execute('''
                INSERT OR REPLACE INTO promo_codes 
                (code, amount, bonus_type, max_uses, expires_at, created_by, description, restrictions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (code.upper(), amount, bonus_type, max_uses, expires_at, created_by, description, restrictions_json))
            
            self.connection.commit()
            self.log_action('PROMO', f'Promo code {code} created by {created_by}')
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания промокода {code}: {e}")
            return False
    
    def get_promo_code(self, code: str) -> Optional[Dict]:
        """Получение информации о промокоде"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT * FROM promo_codes WHERE code = ?', (code.upper(),))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ Ошибка получения промокода {code}: {e}")
            return None
    
    async def activate_promo_code(self, user_id: int, code: str) -> Dict:
        """Активация промокода"""
        try:
            cursor = self.connection.cursor()
            
            # Получаем информацию о промокоде
            cursor.execute('''
                SELECT * FROM promo_codes 
                WHERE code = ? AND is_active = 1
            ''', (code.upper(),))
            
            promo = cursor.fetchone()
            if not promo:
                return {'success': False, 'message': 'Промокод не найден'}
            
            promo = dict(promo)
            
            # Проверяем срок действия
            if promo['expires_at']:
                expires_at = datetime.datetime.strptime(promo['expires_at'], '%Y-%m-%d %H:%M:%S')
                if expires_at < datetime.datetime.now():
                    return {'success': False, 'message': 'Срок действия промокода истек'}
            
            # Проверяем лимит использований
            if promo['max_uses'] > 0 and promo['used_count'] >= promo['max_uses']:
                return {'success': False, 'message': 'Лимит использований промокода исчерпан'}
            
            # Проверяем, активировал ли пользователь уже этот промокод
            cursor.execute('''
                SELECT 1 FROM promo_activations 
                WHERE user_id = ? AND promo_code = ?
            ''', (user_id, code.upper()))
            
            if cursor.fetchone():
                return {'success': False, 'message': 'Вы уже активировали этот промокод'}
            
            # Проверяем ограничения
            restrictions = json.loads(promo['restrictions'] or '{}')
            if restrictions:
                user = self.get_user(user_id)
                
                # Минимальный депозит
                if 'min_deposit' in restrictions and user['total_deposit'] < restrictions['min_deposit']:
                    return {'success': False, 'message': f'Требуется минимальный депозит {restrictions["min_deposit"]}$'}
                
                # Минимальное количество ставок
                if 'min_bets' in restrictions and user['total_bets'] < restrictions['min_bets']:
                    return {'success': False, 'message': f'Требуется минимум {restrictions["min_bets"]} ставок'}
            
            # Активируем промокод
            cursor.execute('''
                UPDATE promo_codes 
                SET used_count = used_count + 1 
                WHERE code = ?
            ''', (code.upper(),))
            
            # Записываем активацию
            cursor.execute('''
                INSERT INTO promo_activations (user_id, promo_code, amount)
                VALUES (?, ?, ?)
            ''', (user_id, code.upper(), promo['amount']))
            
            # Начисляем бонус
            if promo['bonus_type'] == 'percentage':
                # Процентный бонус от депозита
                user = self.get_user(user_id)
                bonus_amount = user['total_deposit'] * (promo['amount'] / 100)
            else:
                # Фиксированный бонус
                bonus_amount = promo['amount']
            
            await self.add_to_balance(user_id, bonus_amount, 'promo', f'Активация промокода {code}')
            
            # Обновляем статистику
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                UPDATE statistics 
                SET promo_activations = promo_activations + 1, promo_amount = promo_amount + ?, updated_at = CURRENT_TIMESTAMP
                WHERE date = ?
            ''', (bonus_amount, today))
            
            self.connection.commit()
            self.log_action('PROMO', f'User {user_id} activated promo {code} for {bonus_amount}$')
            
            return {
                'success': True,
                'message': 'Промокод успешно активирован',
                'amount': bonus_amount,
                'promo': promo
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка активации промокода {code} для {user_id}: {e}")
            return {'success': False, 'message': f'Ошибка активации: {str(e)}'}
    
    def get_promo_codes(self, is_active: bool = True, created_by: int = None) -> List[Dict]:
        """Получение списка промокодов"""
        try:
            cursor = self.connection.cursor()
            
            query = 'SELECT * FROM promo_codes WHERE 1=1'
            params = []
            
            if is_active is not None:
                query += ' AND is_active = ?'
                params.append(1 if is_active else 0)
            
            if created_by:
                query += ' AND created_by = ?'
                params.append(created_by)
            
            query += ' ORDER BY created_at DESC'
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения промокодов: {e}")
            return []
    
    # ==================== АДМИН МЕТОДЫ ДЛЯ БАЛАНСА ====================
    
    async def admin_add_balance(self, user_id: int, amount: float, admin_id: int, reason: str = "Админ пополнение") -> bool:
        """Пополнение баланса пользователя администратором"""
        try:
            # Получаем текущий баланс
            current_balance = self.get_user_balance(user_id)
            
            # Добавляем средства
            success = await self.add_to_balance(
                user_id, 
                amount, 
                'admin_add', 
                f'{reason} (Админ: {admin_id})',
                admin_id,
                'admin'
            )
            
            if success:
                # Логируем действие
                self.log_action('ADMIN_BALANCE', 
                    f'Admin {admin_id} added {amount}$ to user {user_id}. Reason: {reason}',
                    admin_id,
                    {'user_id': user_id, 'amount': amount, 'reason': reason}
                )
                
                # Отправляем уведомление пользователю
                try:
                    await send_photo_message(
                        user_id,
                        'success',
                        f"💰 <b>Баланс пополнен администратором!</b>\n\n"
                        f"💸 <b>Сумма:</b> {format_balance(amount)}\n"
                        f"📝 <b>Причина:</b> {reason}\n"
                        f"💳 <b>Новый баланс:</b> {format_balance(current_balance + amount)}\n\n"
                        f"🎮 <b>Удачи в играх!</b>"
                    )
                except:
                    pass
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Ошибка админ пополнения баланса {user_id}: {e}")
            return False
    
    async def admin_deduct_balance(self, user_id: int, amount: float, admin_id: int, reason: str = "Админ списание") -> bool:
        """Списание баланса пользователя администратором"""
        try:
            # Получаем текущий баланс
            current_balance = self.get_user_balance(user_id)
            
            if current_balance < amount:
                logger.warning(f"⚠️ Недостаточно средств у пользователя {user_id} для списания")
                return False
            
            # Списание средств
            success = await self.deduct_from_balance(
                user_id, 
                amount, 
                'admin_deduct', 
                f'{reason} (Админ: {admin_id})',
                admin_id,
                'admin'
            )
            
            if success:
                # Логируем действие
                self.log_action('ADMIN_BALANCE', 
                    f'Admin {admin_id} deducted {amount}$ from user {user_id}. Reason: {reason}',
                    admin_id,
                    {'user_id': user_id, 'amount': amount, 'reason': reason}
                )
                
                # Отправляем уведомление пользователю
                try:
                    await send_photo_message(
                        user_id,
                        'error',
                        f"⚠️ <b>Списание средств администратором!</b>\n\n"
                        f"💸 <b>Сумма:</b> {format_balance(amount)}\n"
                        f"📝 <b>Причина:</b> {reason}\n"
                        f"💳 <b>Новый баланс:</b> {format_balance(current_balance - amount)}\n\n"
                        f"📞 <b>По вопросам обращайтесь в поддержку</b>"
                    )
                except:
                    pass
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Ошибка админ списания баланса {user_id}: {e}")
            return False
    
    async def admin_set_balance(self, user_id: int, amount: float, admin_id: int, reason: str = "Админ установка баланса") -> bool:
        """Установка баланса пользователя администратором"""
        try:
            # Получаем текущий баланс
            current_balance = self.get_user_balance(user_id)
            
            # Устанавливаем баланс
            success = await self.update_balance(
                user_id, 
                amount, 
                'admin_set', 
                f'{reason} (Админ: {admin_id})',
                admin_id,
                'admin'
            )
            
            if success:
                # Логируем действие
                self.log_action('ADMIN_BALANCE', 
                    f'Admin {admin_id} set balance {amount}$ for user {user_id}. Reason: {reason}',
                    admin_id,
                    {'user_id': user_id, 'old_balance': current_balance, 'new_balance': amount, 'reason': reason}
                )
                
                # Отправляем уведомление пользователю
                try:
                    if amount > current_balance:
                        photo_type = 'success'
                        diff_text = f"📈 <b>Пополнено:</b> {format_balance(amount - current_balance)}"
                    elif amount < current_balance:
                        photo_type = 'error'
                        diff_text = f"📉 <b>Списано:</b> {format_balance(current_balance - amount)}"
                    else:
                        photo_type = 'info'
                        diff_text = "🔄 <b>Баланс не изменился</b>"
                    
                    await send_photo_message(
                        user_id,
                        photo_type,
                        f"⚡ <b>Баланс изменен администратором!</b>\n\n"
                        f"📝 <b>Причина:</b> {reason}\n"
                        f"{diff_text}\n"
                        f"💳 <b>Старый баланс:</b> {format_balance(current_balance)}\n"
                        f"💰 <b>Новый баланс:</b> {format_balance(amount)}\n\n"
                        f"📞 <b>По вопросам обращайтесь в поддержку</b>"
                    )
                except:
                    pass
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Ошибка админ установки баланса {user_id}: {e}")
            return False
    
    # ==================== МЕТОДЫ ДЛЯ КОЭФФИЦИЕНТОВ ====================
    
    def get_coefficient(self, name: str) -> float:
        """Получение коэффициента"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT value FROM coefficients WHERE name = ?', (name,))
            row = cursor.fetchone()
            return row['value'] if row else DEFAULT_KEF.get(name, 1.0)
        except Exception as e:
            logger.error(f"❌ Ошибка получения коэффициента {name}: {e}")
            return DEFAULT_KEF.get(name, 1.0)
    
    def update_coefficient(self, name: str, value: float, updated_by: int = None) -> bool:
        """Обновление коэффициента"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                UPDATE coefficients 
                SET value = ?, updated_at = CURRENT_TIMESTAMP, updated_by = ?
                WHERE name = ?
            ''', (value, updated_by, name))
            self.connection.commit()
            self.log_action('COEFFICIENT', f'Coefficient {name} updated to {value} by {updated_by}')
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка обновления коэффициента {name}: {e}")
            return False
    
    def get_all_coefficients(self) -> Dict:
        """Получение всех коэффициентов"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT name, value FROM coefficients')
            return {row['name']: row['value'] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"❌ Ошибка получения всех коэффициентов: {e}")
            return {}
    
    # ==================== МЕТОДЫ ДЛЯ ФЕЙК ИГР ====================
    
    def get_fake_games_settings(self) -> Dict:
        """Получение настроек фейк игр"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT * FROM fake_games WHERE id = 1')
            row = cursor.fetchone()
            if row:
                settings = dict(row)
                settings['statistics'] = json.loads(settings.get('statistics', '{}'))
                settings['settings'] = json.loads(settings.get('settings', '{}'))
                return settings
            return {}
        except Exception as e:
            logger.error(f"❌ Ошибка получения настроек фейк игр: {e}")
            return {}
    
    def update_fake_games_settings(self, enabled: bool = None, min_interval: int = None, max_interval: int = None,
                                  min_bet: float = None, max_bet: float = None, win_chance: int = None,
                                  settings: Dict = None) -> bool:
        """Обновление настроек фейк игр"""
        try:
            cursor = self.connection.cursor()
            
            current = self.get_fake_games_settings()
            if not current:
                cursor.execute('''
                    INSERT INTO fake_games (id, enabled, min_interval, max_interval, min_bet, max_bet, win_chance, settings)
                    VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                ''', (enabled or 1, min_interval or 30, max_interval or 120, min_bet or 1.0, max_bet or 100.0, win_chance or 40, json.dumps(settings or {})))
            else:
                update_fields = []
                params = []
                
                if enabled is not None:
                    update_fields.append('enabled = ?')
                    params.append(1 if enabled else 0)
                
                if min_interval is not None:
                    update_fields.append('min_interval = ?')
                    params.append(min_interval)
                
                if max_interval is not None:
                    update_fields.append('max_interval = ?')
                    params.append(max_interval)
                
                if min_bet is not None:
                    update_fields.append('min_bet = ?')
                    params.append(min_bet)
                
                if max_bet is not None:
                    update_fields.append('max_bet = ?')
                    params.append(max_bet)
                
                if win_chance is not None:
                    update_fields.append('win_chance = ?')
                    params.append(win_chance)
                
                if settings is not None:
                    update_fields.append('settings = ?')
                    params.append(json.dumps(settings))
                
                update_fields.append('last_run = CURRENT_TIMESTAMP')
                
                if update_fields:
                    query = f'UPDATE fake_games SET {", ".join(update_fields)} WHERE id = 1'
                    cursor.execute(query, params)
            
            self.connection.commit()
            self.log_action('FAKE_GAMES', 'Fake games settings updated')
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления настроек фейк игр: {e}")
            return False
    
    def add_fake_game_stat(self, bet_amount: float, win_amount: float, result: str) -> bool:
        """Добавление статистики фейк игры"""
        try:
            cursor = self.connection.cursor()
            
            settings = self.get_fake_games_settings()
            stats = settings.get('statistics', {})
            
            stats['total_games'] = stats.get('total_games', 0) + 1
            stats['total_bet_amount'] = stats.get('total_bet_amount', 0) + bet_amount
            stats['total_win_amount'] = stats.get('total_win_amount', 0) + win_amount
            
            if result == 'win':
                stats['wins'] = stats.get('wins', 0) + 1
            else:
                stats['losses'] = stats.get('losses', 0) + 1
            
            stats['last_game'] = datetime.datetime.now().isoformat()
            
            cursor.execute('''
                UPDATE fake_games 
                SET statistics = ? 
                WHERE id = 1
            ''', (json.dumps(stats),))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления статистики фейк игры: {e}")
            return False
    
    # ==================== МЕТОДЫ ДЛЯ СТАТИСТИКИ ====================
    
    def get_statistics(self, date: str = None) -> Dict:
        """Получение статистики"""
        try:
            if date is None:
                date = datetime.datetime.now().strftime('%Y-%m-%d')
            
            cursor = self.connection.cursor()
            cursor.execute('SELECT * FROM statistics WHERE date = ?', (date,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            
            # Создаем новую запись если нет
            cursor.execute('''
                INSERT INTO statistics (date)
                VALUES (?)
            ''', (date,))
            self.connection.commit()
            
            return {
                'date': date,
                'total_users': 0,
                'new_users': 0,
                'active_users': 0,
                'total_deposits': 0,
                'total_deposit_amount': 0.0,
                'total_withdrawals': 0,
                'total_withdraw_amount': 0.0,
                'total_bets': 0,
                'total_bet_amount': 0.0,
                'winning_bets': 0,
                'losing_bets': 0,
                'total_win_amount': 0.0,
                'total_loss_amount': 0.0,
                'profit': 0.0,
                'referral_payments': 0,
                'referral_amount': 0.0,
                'promo_activations': 0,
                'promo_amount': 0.0
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {}
    
    def get_overall_statistics(self) -> Dict:
        """Общая статистика за все время"""
        try:
            cursor = self.connection.cursor()
            
            # Статистика пользователей
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_users,
                    SUM(balance) as total_balance,
                    SUM(total_deposit) as total_deposit,
                    SUM(total_withdraw) as total_withdraw,
                    SUM(total_wins) as total_wins,
                    SUM(total_losses) as total_losses,
                    SUM(total_bets) as total_bets,
                    SUM(total_bet_amount) as total_bet_amount
                FROM users
            ''')
            user_stats = dict(cursor.fetchone())
            
            # Статистика ставок
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_bets_all,
                    SUM(amount) as total_bet_amount_all,
                    SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as total_wins_all,
                    SUM(CASE WHEN result = 'lose' THEN 1 ELSE 0 END) as total_losses_all,
                    SUM(CASE WHEN result = 'win' THEN win_amount ELSE 0 END) as total_win_amount_all,
                    SUM(CASE WHEN result = 'lose' THEN amount ELSE 0 END) as total_loss_amount_all
                FROM bets
            ''')
            bet_stats = dict(cursor.fetchone())
            
            # Статистика депозитов и выводов
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_deposits_all,
                    SUM(amount) as total_deposit_amount_all
                FROM deposits 
                WHERE status = 'completed'
            ''')
            deposit_stats = dict(cursor.fetchone())
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_withdrawals_all,
                    SUM(amount) as total_withdraw_amount_all
                FROM withdrawals 
                WHERE status = 'completed'
            ''')
            withdraw_stats = dict(cursor.fetchone())
            
            # Объединяем статистику
            stats = {
                'users': user_stats,
                'bets': bet_stats,
                'deposits': deposit_stats,
                'withdrawals': withdraw_stats,
                'overall': {
                    'total_profit': (deposit_stats.get('total_deposit_amount_all', 0) or 0) - 
                                   (withdraw_stats.get('total_withdraw_amount_all', 0) or 0) - 
                                   (user_stats.get('total_balance', 0) or 0),
                    'game_profit': (bet_stats.get('total_loss_amount_all', 0) or 0) - 
                                  (bet_stats.get('total_win_amount_all', 0) or 0),
                    'active_today': self.get_active_users_count(1),
                    'active_week': self.get_active_users_count(7),
                    'active_month': self.get_active_users_count(30)
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения общей статистики: {e}")
            return {}
    
    def get_active_users_count(self, days: int = 1) -> int:
        """Количество активных пользователей за N дней"""
        try:
            cursor = self.connection.cursor()
            date_limit = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) as count 
                FROM bets 
                WHERE created_at >= ?
            ''', (date_limit,))
            row = cursor.fetchone()
            return row['count'] if row else 0
        except Exception as e:
            logger.error(f"❌ Ошибка получения активных пользователей: {e}")
            return 0
    
    # ==================== МЕТОДЫ ДЛЯ АДМИНИСТРИРОВАНИЯ ====================
    
    def get_all_users(self, limit: int = 100, offset: int = 0, order_by: str = 'registration_date DESC') -> List[Dict]:
        """Получение всех пользователей"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(f'''
                SELECT * FROM users 
                ORDER BY {order_by} 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Ошибка получения всех пользователей: {e}")
            return []
    
    def search_users(self, query: str, limit: int = 50) -> List[Dict]:
        """Поиск пользователей"""
        try:
            cursor = self.connection.cursor()
            
            # Поиск по ID
            if query.isdigit():
                cursor.execute('''
                    SELECT * FROM users 
                    WHERE user_id = ? 
                    LIMIT ?
                ''', (int(query), limit))
            
            # Поиск по username
            elif query.startswith('@'):
                cursor.execute('''
                    SELECT * FROM users 
                    WHERE username LIKE ? 
                    LIMIT ?
                ''', (f'%{query[1:]}%', limit))
            
            # Поиск по имени
            else:
                cursor.execute('''
                    SELECT * FROM users 
                    WHERE first_name LIKE ? OR last_name LIKE ? 
                    LIMIT ?
                ''', (f'%{query}%', f'%{query}%', limit))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска пользователей: {e}")
            return []
    
    def block_user(self, user_id: int, admin_id: int, reason: str = '') -> bool:
        """Блокировка пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                UPDATE users 
                SET is_blocked = 1, block_reason = ?, last_activity = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (reason, user_id))
            self.connection.commit()
            self.log_action('ADMIN', f'User {user_id} blocked by {admin_id}. Reason: {reason}')
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка блокировки пользователя {user_id}: {e}")
            return False
    
    def unblock_user(self, user_id: int, admin_id: int) -> bool:
        """Разблокировка пользователя"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                UPDATE users 
                SET is_blocked = 0, block_reason = '', last_activity = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (user_id,))
            self.connection.commit()
            self.log_action('ADMIN', f'User {user_id} unblocked by {admin_id}')
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка разблокировки пользователя {user_id}: {e}")
            return False
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    def log_action(self, action_type: str, message: str, user_id: int = None, data: Dict = None):
        """Логирование действий"""
        try:
            cursor = self.connection.cursor()
            data_json = json.dumps(data or {})
            
            # Получаем информацию о вызове
            frame = inspect.currentframe().f_back
            module = frame.f_globals.get('__name__', 'unknown')
            function = frame.f_code.co_name
            
            cursor.execute('''
                INSERT INTO logs (level, module, function, message, user_id, data)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (action_type, module, function, message, user_id, data_json))
            
            self.connection.commit()
            
        except Exception as e:
            logger.error(f"❌ Ошибка логирования: {e}")
    
    def get_logs(self, limit: int = 100, level: str = None, user_id: int = None) -> List[Dict]:
        """Получение логов"""
        try:
            cursor = self.connection.cursor()
            
            query = 'SELECT * FROM logs WHERE 1=1'
            params = []
            
            if level:
                query += ' AND level = ?'
                params.append(level)
            
            if user_id:
                query += ' AND user_id = ?'
                params.append(user_id)
            
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения логов: {e}")
            return []
    
    def cleanup_old_data(self, days: int = 30) -> bool:
        """Очистка старых данных"""
        try:
            cursor = self.connection.cursor()
            date_limit = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Очищаем старые логи
            cursor.execute('DELETE FROM logs WHERE created_at < ?', (date_limit,))
            
            # Очищаем старые ставки (кроме последних 1000 на пользователя)
            cursor.execute('''
                DELETE FROM bets 
                WHERE id NOT IN (
                    SELECT id FROM bets 
                    ORDER BY created_at DESC 
                    LIMIT 10000
                ) AND created_at < ?
            ''', (date_limit,))
            
            # Очищаем старые уведомления
            cursor.execute('DELETE FROM notifications WHERE created_at < ? AND is_read = 1', (date_limit,))
            
            self.connection.commit()
            self.log_action('SYSTEM', f'Cleaned up data older than {days} days')
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки данных: {e}")
            return False
    
    def backup_database(self, backup_path: str = None) -> bool:
        """Бэкап базы данных"""
        try:
            if backup_path is None:
                backup_path = f'casino_backup_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
            
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
            self.log_action('SYSTEM', f'Database backed up to {backup_path}')
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка бэкапа БД: {e}")
            return False
    
    def close(self):
        """Закрытие соединения с БД"""
        try:
            if self.connection:
                self.connection.close()
                logger.info("✅ Соединение с БД закрыто")
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия БД: {e}")

# ==================== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ====================
try:
    db = Database()
    logger.info("✅ База данных инициализирована")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации БД: {e}")
    sys.exit(1)

# ==================== ИНИЦИАЛИЗАЦИЯ ПЛАНИРОВЩИКА ====================
try:
    import asyncio
    # Создаем новый event loop для APScheduler
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    scheduler = AsyncIOScheduler(event_loop=loop)
    scheduler.start()
    logger.info("✅ Планировщик инициализирован")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации планировщика: {e}")
    scheduler = None

# ==================== СОСТОЯНИЯ (FSM) ====================
class UserStates(StatesGroup):
    waiting_for_bet_amount = State()
    waiting_for_game_choice = State()
    waiting_for_outcome = State()
    waiting_for_deposit_amount = State()
    waiting_for_withdraw_amount = State()
    waiting_for_withdraw_address = State()
    waiting_for_promo_code = State()
    waiting_for_captcha = State()
    waiting_for_feedback = State()
    waiting_for_support_message = State()

class AdminStates(StatesGroup):
    waiting_for_admin_action = State()
    waiting_for_statistics_user_id = State()
    waiting_for_promo_code_creation = State()
    waiting_for_promo_amount = State()
    waiting_for_promo_max_uses = State()
    waiting_for_promo_expires = State()
    waiting_for_promo_description = State()
    waiting_for_kef_edit = State()
    waiting_for_kef_value = State()
    waiting_for_broadcast_message = State()
    waiting_for_broadcast_photo = State()
    waiting_for_user_balance_edit = State()
    waiting_for_user_id_for_balance = State()
    waiting_for_balance_amount = State()
    waiting_for_balance_reason = State()
    waiting_for_fake_settings = State()
    waiting_for_fake_interval_min = State()
    waiting_for_fake_interval_max = State()
    waiting_for_fake_bet_min = State()
    waiting_for_fake_bet_max = State()
    waiting_for_fake_win_chance = State()
    waiting_for_url_edit = State()
    waiting_for_url_value = State()
    waiting_for_admin_user_search = State()

# ==================== КЛАВИАТУРЫ (ПОЛНЫЙ НАБОР) ====================
def get_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    """Главное меню"""
    keyboard = [
        [KeyboardButton('💰 Мой баланс'), KeyboardButton('🎲 Сделать ставку')],
        [KeyboardButton('📎 Реферальная программа'), KeyboardButton('💭 Информация')],
        [KeyboardButton('🎁 Промокоды'), KeyboardButton('📊 Моя статистика')],
        [KeyboardButton('🆘 Поддержка'), KeyboardButton('⚙️ Настройки')]
    ]
    if user_id in ADMIN:
        keyboard.append([KeyboardButton('👑 Админка')])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, input_field_placeholder='Выберите действие👇')

def get_balance_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для баланса"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('💳 Пополнить баланс', callback_data='deposit')],
        [InlineKeyboardButton('📤 Вывести средства', callback_data='withdraw')],
        [InlineKeyboardButton('🎁 Получить бонус', callback_data='get_bonus')],
        [InlineKeyboardButton('📊 История операций', callback_data='transaction_history')],
        [InlineKeyboardButton('🔙 В меню', callback_data='back_to_menu')]
    ])

def get_games_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора игры"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton('🎲 Больше/Меньше', callback_data='game_more_less'),
            InlineKeyboardButton('🎯 Угадай число', callback_data='game_number')
        ],
        [
            InlineKeyboardButton('⚽️ Футбол', callback_data='game_football'),
            InlineKeyboardButton('🏀 Баскетбол', callback_data='game_basketball')
        ],
        [
            InlineKeyboardButton('✊ КНБ', callback_data='game_knb'),
            InlineKeyboardButton('🎡 Рулетка', callback_data='game_roulette')
        ],
        [
            InlineKeyboardButton('🎰 Слоты', callback_data='game_slots'),
            InlineKeyboardButton('🎲 Чет/Нечет', callback_data='game_even_odd')
        ],
        [
            InlineKeyboardButton('♠️ Блэкджек', callback_data='game_blackjack'),
            InlineKeyboardButton('🎯 Дартс', callback_data='game_darts')
        ],
        [InlineKeyboardButton('📊 Статистика игр', callback_data='game_stats')],
        [InlineKeyboardButton('🔙 В меню', callback_data='back_to_menu')]
    ])

def get_more_less_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для игры Больше/Меньше"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton('Больше (4-6)', callback_data='outcome_more'),
            InlineKeyboardButton('Меньше (1-3)', callback_data='outcome_less')
        ],
        [InlineKeyboardButton('🎲 Случайное число', callback_data='outcome_random')],
        [InlineKeyboardButton('📊 Статистика игры', callback_data='stats_more_less')],
        [InlineKeyboardButton('🔙 Назад к играм', callback_data='back_to_games')]
    ])

def get_numbers_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для игры Угадай число"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton('1', callback_data='outcome_1'),
            InlineKeyboardButton('2', callback_data='outcome_2'),
            InlineKeyboardButton('3', callback_data='outcome_3')
        ],
        [
            InlineKeyboardButton('4', callback_data='outcome_4'),
            InlineKeyboardButton('5', callback_data='outcome_5'),
            InlineKeyboardButton('6', callback_data='outcome_6')
        ],
        [InlineKeyboardButton('🎲 Случайное число', callback_data='outcome_random_num')],
        [InlineKeyboardButton('📊 Статистика игры', callback_data='stats_numbers')],
        [InlineKeyboardButton('🔙 Назад к играм', callback_data='back_to_games')]
    ])

def get_even_odd_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для игры Чет/Нечет"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton('🔢 Четное', callback_data='outcome_even'),
            InlineKeyboardButton('🔣 Нечетное', callback_data='outcome_odd')
        ],
        [InlineKeyboardButton('🎲 Случайное число', callback_data='outcome_random_eo')],
        [InlineKeyboardButton('📊 Статистика игры', callback_data='stats_even_odd')],
        [InlineKeyboardButton('🔙 Назад к играм', callback_data='back_to_games')]
    ])

def get_roulette_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для игры Рулетка"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton('🔴 Красное', callback_data='outcome_red'),
            InlineKeyboardButton('⚫️ Черное', callback_data='outcome_black'),
            InlineKeyboardButton('🟢 Зеленое', callback_data='outcome_green')
        ],
        [
            InlineKeyboardButton('1-12', callback_data='outcome_1_12'),
            InlineKeyboardButton('13-24', callback_data='outcome_13_24'),
            InlineKeyboardButton('25-36', callback_data='outcome_25_36')
        ],
        [
            InlineKeyboardButton('1-18', callback_data='outcome_1_18'),
            InlineKeyboardButton('Чет', callback_data='outcome_even_roulette'),
            InlineKeyboardButton('Нечет', callback_data='outcome_odd_roulette'),
            InlineKeyboardButton('19-36', callback_data='outcome_19_36')
        ],
        [InlineKeyboardButton('🎲 Случайное число', callback_data='outcome_random_roulette')],
        [InlineKeyboardButton('📊 Статистика игры', callback_data='stats_roulette')],
        [InlineKeyboardButton('🔙 Назад к играм', callback_data='back_to_games')]
    ])

def get_football_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для игры Футбол"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton('⚽️ Гол', callback_data='outcome_goal'),
            InlineKeyboardButton('❌ Мимо', callback_data='outcome_miss')
        ],
        [InlineKeyboardButton('🎲 Случайный исход', callback_data='outcome_random_football')],
        [InlineKeyboardButton('📊 Статистика игры', callback_data='stats_football')],
        [InlineKeyboardButton('🔙 Назад к играм', callback_data='back_to_games')]
    ])

def get_basketball_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для игры Баскетбол"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton('🏀 Гол', callback_data='outcome_basket_goal'),
            InlineKeyboardButton('❌ Мимо', callback_data='outcome_basket_miss')
        ],
        [InlineKeyboardButton('🎲 Случайный исход', callback_data='outcome_random_basketball')],
        [InlineKeyboardButton('📊 Статистика игры', callback_data='stats_basketball')],
        [InlineKeyboardButton('🔙 Назад к играм', callback_data='back_to_games')]
    ])

def get_knb_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для игры Камень-Ножницы-Бумага"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton('✊ Камень', callback_data='outcome_rock'),
            InlineKeyboardButton('✌️ Ножницы', callback_data='outcome_scissors'),
            InlineKeyboardButton('✋ Бумага', callback_data='outcome_paper')
        ],
        [InlineKeyboardButton('🎲 Случайный выбор', callback_data='outcome_random_knb')],
        [InlineKeyboardButton('📊 Статистика игры', callback_data='stats_knb')],
        [InlineKeyboardButton('🔙 Назад к играм', callback_data='back_to_games')]
    ])

def get_slots_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для игры Слоты"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('🎰 Крутить слоты', callback_data='spin_slots')],
        [InlineKeyboardButton('📊 Статистика игры', callback_data='stats_slots')],
        [InlineKeyboardButton('🎁 Бонусы слотов', callback_data='slots_bonuses')],
        [InlineKeyboardButton('🔙 Назад к играм', callback_data='back_to_games')]
    ])

def get_info_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для раздела информации"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('📖 Правила', callback_data='rules')],
        [InlineKeyboardButton('❓ Частые вопросы', callback_data='faq')],
        [InlineKeyboardButton('💰 Тарифы и лимиты', callback_data='tariffs')],
        [InlineKeyboardButton('🛡️ Безопасность', callback_data='security')],
        [InlineKeyboardButton('🏆 Достижения', callback_data='achievements')],
        [InlineKeyboardButton('🌟 VIP программа', callback_data='vip_program')],
        [InlineKeyboardButton('📞 Контакты', callback_data='contacts')],
        [InlineKeyboardButton('🔙 В меню', callback_data='back_to_menu')]
    ])

def get_referral_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для реферальной программы"""
    referral_link = f"https://t.me/{NICNAME}?start={user_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('📋 Мои рефералы', callback_data='my_referrals')],
        [InlineKeyboardButton('💰 Реферальные выплаты', callback_data='referral_payments')],
        [InlineKeyboardButton('📊 Статистика', callback_data='referral_stats')],
        [InlineKeyboardButton('🔗 Копировать ссылку', callback_data=f'copy_link:{referral_link}')],
        [InlineKeyboardButton('📢 Поделиться', callback_data='share_referral')],
        [InlineKeyboardButton('🔙 В меню', callback_data='back_to_menu')]
    ])

def get_promo_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для промокодов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('🎫 Активировать промокод', callback_data='activate_promo')],
        [InlineKeyboardButton('📋 Активные промокоды', callback_data='active_promos')],
        [InlineKeyboardButton('📊 Мои активации', callback_data='my_promo_activations')],
        [InlineKeyboardButton('🎁 Бонусные программы', callback_data='bonus_programs')],
        [InlineKeyboardButton('🔙 В меню', callback_data='back_to_menu')]
    ])

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ панели"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('📊 Статистика проекта', callback_data='admin_stats_project')],
        [InlineKeyboardButton('👤 Управление пользователями', callback_data='admin_users')],
        [InlineKeyboardButton('🎁 Управление промокодами', callback_data='admin_promos')],
        [InlineKeyboardButton('💰 Управление балансами', callback_data='admin_balance')],
        [InlineKeyboardButton('⚙️ Настройки фейк игр', callback_data='admin_fake_games')],
        [InlineKeyboardButton('📈 Управление коэффициентами', callback_data='admin_coefficients')],
        [InlineKeyboardButton('📣 Рассылка сообщений', callback_data='admin_broadcast')],
        [InlineKeyboardButton('🔗 Управление ссылками', callback_data='admin_urls')],
        [InlineKeyboardButton('🧹 Технические операции', callback_data='admin_tech')],
        [InlineKeyboardButton('📋 Логи и отчеты', callback_data='admin_logs')],
        [InlineKeyboardButton('⚙️ Настройки системы', callback_data='admin_settings')],
        [InlineKeyboardButton('🔙 В меню', callback_data='back_to_menu')]
    ])

def get_admin_users_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления пользователями"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('🔍 Поиск пользователя', callback_data='admin_search_user')],
        [InlineKeyboardButton('📊 Топ пользователей', callback_data='admin_top_users')],
        [InlineKeyboardButton('📈 Активность пользователей', callback_data='admin_user_activity')],
        [InlineKeyboardButton('🚫 Заблокировать', callback_data='admin_block_user')],
        [InlineKeyboardButton('✅ Разблокировать', callback_data='admin_unblock_user')],
        [InlineKeyboardButton('📧 Отправить сообщение', callback_data='admin_message_user')],
        [InlineKeyboardButton('🔙 В админку', callback_data='back_to_admin')]
    ])

def get_admin_promos_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления промокодами"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('🎫 Создать промокод', callback_data='admin_create_promo')],
        [InlineKeyboardButton('📋 Список промокодов', callback_data='admin_list_promos')],
        [InlineKeyboardButton('📊 Статистика промокодов', callback_data='admin_promo_stats')],
        [InlineKeyboardButton('❌ Деактивировать промокод', callback_data='admin_deactivate_promo')],
        [InlineKeyboardButton('📈 Аналитика промокодов', callback_data='admin_promo_analytics')],
        [InlineKeyboardButton('🔙 В админку', callback_data='back_to_admin')]
    ])

def get_admin_balance_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления балансами"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('💰 Пополнить баланс', callback_data='admin_add_balance')],
        [InlineKeyboardButton('📉 Списать баланс', callback_data='admin_deduct_balance')],
        [InlineKeyboardButton('⚡ Установить баланс', callback_data='admin_set_balance')],
        [InlineKeyboardButton('🔍 Проверить баланс', callback_data='admin_check_balance')],
        [InlineKeyboardButton('📊 Балансы пользователей', callback_data='admin_all_balances')],
        [InlineKeyboardButton('🔙 В админку', callback_data='back_to_admin')]
    ])

def get_admin_tech_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура технических операций"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('🧹 Очистить старые данные', callback_data='admin_cleanup')],
        [InlineKeyboardButton('💾 Создать бэкап БД', callback_data='admin_backup')],
        [InlineKeyboardButton('🔄 Обновить статистику', callback_data='admin_update_stats')],
        [InlineKeyboardButton('⚙️ Перезагрузить настройки', callback_data='admin_reload_settings')],
        [InlineKeyboardButton('📊 Проверить состояние', callback_data='admin_health_check')],
        [InlineKeyboardButton('🔧 Техническое обслуживание', callback_data='admin_maintenance')],
        [InlineKeyboardButton('🔙 В админку', callback_data='back_to_admin')]
    ])

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('❌ Отмена', callback_data='cancel')]
    ])

def get_back_admin_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад в админку"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('🔙 Назад в админку', callback_data='back_to_admin')]
    ])

def get_back_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад в меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('🔙 В меню', callback_data='back_to_menu')]
    ])

def get_confirm_keyboard(confirm_data: str, cancel_data: str = 'cancel') -> InlineKeyboardMarkup:
    """Клавиатура подтверждения"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton('✅ Подтвердить', callback_data=confirm_data),
            InlineKeyboardButton('❌ Отмена', callback_data=cancel_data)
        ]
    ])

def get_pagination_keyboard(current_page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура пагинации"""
    keyboard = []
    
    if current_page > 1:
        keyboard.append(InlineKeyboardButton('⬅️ Назад', callback_data=f'{prefix}_page_{current_page-1}'))
    
    keyboard.append(InlineKeyboardButton(f'{current_page}/{total_pages}', callback_data=f'{prefix}_current'))
    
    if current_page < total_pages:
        keyboard.append(InlineKeyboardButton('Вперед ➡️', callback_data=f'{prefix}_page_{current_page+1}'))
    
    return InlineKeyboardMarkup(inline_keyboard=[keyboard])

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

async def send_message_with_retry(chat_id: int, text: str, **kwargs) -> bool:
    """Отправка сообщения с повторными попытками"""
    for attempt in range(3):
        try:
            await bot.send_message(chat_id, text, **kwargs)
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения (попытка {attempt+1}): {e}")
            await asyncio.sleep(1)
    return False

async def edit_message_with_retry(message: Message, text: str, **kwargs) -> bool:
    """Редактирование сообщения с повторными попытками"""
    for attempt in range(3):
        try:
            await message.edit_text(text, **kwargs)
            return True
        except MessageNotModified:
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка редактирования сообщения (попытка {attempt+1}): {e}")
            await asyncio.sleep(1)
    return False

async def delete_message_with_retry(message: Message) -> bool:
    """Удаление сообщения с повторными попытками"""
    for attempt in range(3):
        try:
            await message.delete()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка удаления сообщения (попытка {attempt+1}): {e}")
            await asyncio.sleep(1)
    return False

def format_balance(amount: float) -> str:
    """Форматирование суммы баланса"""
    if amount is None:
        return "0.00$"
    return f"{amount:.2f}$"

def format_number(number: float) -> str:
    """Форматирование числа"""
    if number is None:
        return "0"
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}"

def format_datetime(dt: datetime.datetime) -> str:
    """Форматирование даты и времени"""
    return dt.strftime('%d.%m.%Y %H:%M:%S')

def format_date(date_str: str) -> str:
    """Форматирование даты"""
    try:
        dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%d.%m.%Y')
    except:
        return date_str

def get_user_display_name(user: Dict) -> str:
    """Получение отображаемого имени пользователя"""
    if user and user.get('username'):
        return f"@{user['username']}"
    elif user and user.get('first_name'):
        return user['first_name']
    return "Пользователь"

def calculate_win_amount(bet_amount: float, multiplier: float) -> float:
    """Расчет суммы выигрыша"""
    return bet_amount * multiplier

def check_min_bet(bet_amount: float) -> bool:
    """Проверка минимальной ставки"""
    return bet_amount >= MIN_STAVKA

def check_max_bet(bet_amount: float) -> bool:
    """Проверка максимальной ставки"""
    return bet_amount <= LIMIT_STAVKA

def check_min_withdraw(amount: float) -> bool:
    """Проверка минимального вывода"""
    return amount >= MIN_WITHDRAW

def get_game_name(game_type: str) -> str:
    """Получение названия игры"""
    game_names = {
        'more_less': '🎲 Больше/Меньше',
        'number': '🎯 Угадай число',
        'even_odd': '🎲 Чет/Нечет',
        'roulette': '🎡 Рулетка',
        'football': '⚽️ Футбол',
        'basketball': '🏀 Баскетбол',
        'knb': '✊ КНБ',
        'slots': '🎰 Слоты',
        'blackjack': '♠️ Блэкджек',
        'darts': '🎯 Дартс'
    }
    return game_names.get(game_type, '🎲 Неизвестная игра')

def get_outcome_name(outcome: str, game_type: str = None) -> str:
    """Получение названия исхода"""
    outcome_names = {
        'more': 'Больше',
        'less': 'Меньше',
        'even': 'Чет',
        'odd': 'Нечет',
        'red': 'Красное',
        'black': 'Черное',
        'green': 'Зеленое',
        'goal': 'Гол',
        'miss': 'Мимо',
        'basket_goal': 'Гол',
        'basket_miss': 'Мимо',
        'rock': 'Камень',
        'scissors': 'Ножницы',
        'paper': 'Бумага',
        'spin': 'Вращение',
        'hit': 'Попадание',
        'stand': 'Стоп'
    }
    
    if outcome in outcome_names:
        return outcome_names[outcome]
    
    # Для числовых исходов
    if outcome.isdigit():
        return f"Число {outcome}"
    
    return outcome

def get_multiplier(game_type: str, outcome: str) -> float:
    """Получение коэффициента для игры и исхода"""
    try:
        if game_type == 'more_less':
            return db.get_coefficient('KEF1')
        elif game_type == 'number':
            return db.get_coefficient('KEF2')
        elif game_type == 'even_odd':
            return db.get_coefficient('KEF3')
        elif game_type == 'roulette':
            if outcome == 'green':
                return db.get_coefficient('KEF6')
            else:
                return db.get_coefficient('KEF5')
        elif game_type == 'football':
            if outcome == 'goal':
                return db.get_coefficient('KEF12')
            else:
                return db.get_coefficient('KEF13')
        elif game_type == 'basketball':
            if outcome == 'basket_goal':
                return db.get_coefficient('KEF10')
            else:
                return db.get_coefficient('KEF11')
        elif game_type == 'knb':
            return db.get_coefficient('KEF15')
        elif game_type == 'slots':
            return random.choice([2.0, 3.0, 5.0, 10.0, 20.0])
        else:
            return 2.0
    except:
        return 2.0

async def process_game(user_id: int, game_type: str, outcome: str, bet_amount: float) -> Dict:
    """Обработка игры"""
    try:
        # Проверяем баланс
        balance = db.get_user_balance(user_id)
        if balance < bet_amount:
            return {'success': False, 'error': 'Недостаточно средств'}
        
        # Списание ставки
        if not await db.deduct_from_balance(user_id, bet_amount, 'bet', f'Ставка в {get_game_name(game_type)}'):
            return {'success': False, 'error': 'Ошибка списания средств'}
        
        # Определяем результат игры
        result = determine_game_result(game_type, outcome)
        dice_value = result.get('dice_value')
        win = result.get('win', False)
        
        # Получаем коэффициент
        multiplier = get_multiplier(game_type, outcome) if win else 1.0
        win_amount = calculate_win_amount(bet_amount, multiplier) if win else 0
        
        if win:
            # Зачисление выигрыша
            await db.add_to_balance(user_id, win_amount, 'win', f'Выигрыш в {get_game_name(game_type)}')
        
        # Записываем ставку в БД
        bet_id = db.add_bet(
            user_id=user_id,
            game_type=game_type,
            amount=bet_amount,
            outcome=outcome,
            result='win' if win else 'lose',
            win_amount=win_amount,
            multiplier=multiplier,
            dice_value=dice_value,
            is_fake=False
        )
        
        # Обновляем статистику пользователя
        db.update_user_activity(user_id)
        
        return {
            'success': True,
            'win': win,
            'bet_id': bet_id,
            'dice_value': dice_value,
            'multiplier': multiplier,
            'win_amount': win_amount,
            'new_balance': db.get_user_balance(user_id),
            'result_text': f"Выпало: {dice_value}" if dice_value else ""
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки игры: {e}")
        return {'success': False, 'error': str(e)}

def determine_game_result(game_type: str, outcome: str) -> Dict:
    """Определение результата игры"""
    result = {'win': False, 'dice_value': None}
    
    if game_type in ['more_less', 'number', 'even_odd', 'roulette']:
        # Бросок игральной кости (1-6)
        dice_value = random.randint(1, 6)
        result['dice_value'] = dice_value
        
        if game_type == 'more_less':
            if (outcome == 'more' and dice_value >= 4) or (outcome == 'less' and dice_value <= 3):
                result['win'] = True
        elif game_type == 'number':
            if str(dice_value) == outcome:
                result['win'] = True
        elif game_type == 'even_odd':
            if (outcome == 'even' and dice_value % 2 == 0) or (outcome == 'odd' and dice_value % 2 != 0):
                result['win'] = True
        elif game_type == 'roulette':
            # Рулетка: 1-36 плюс 0 (зеленое)
            roulette_number = random.randint(0, 36)
            result['dice_value'] = roulette_number
            
            if outcome == 'green':
                result['win'] = roulette_number == 0
            elif outcome == 'red':
                red_numbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
                result['win'] = roulette_number in red_numbers
            elif outcome == 'black':
                black_numbers = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
                result['win'] = roulette_number in black_numbers
    
    elif game_type in ['football', 'basketball']:
        # 50/50 шанс
        result['win'] = random.random() < 0.5
        result['dice_value'] = 1 if result['win'] else 0
    
    elif game_type == 'knb':
        # Камень-ножницы-бумага
        choices = ['rock', 'scissors', 'paper']
        bot_choice = random.choice(choices)
        
        win_conditions = {
            'rock': 'scissors',
            'scissors': 'paper',
            'paper': 'rock'
        }
        
        result['win'] = win_conditions.get(outcome) == bot_choice
        result['dice_value'] = choices.index(bot_choice) + 1
    
    elif game_type == 'slots':
        # Слоты
        symbols = ['🍒', '🍋', '🍊', '🍉', '🔔', '⭐', '7️⃣']
        reel1 = random.choice(symbols)
        reel2 = random.choice(symbols)
        reel3 = random.choice(symbols)
        
        result['dice_value'] = f"{reel1}{reel2}{reel3}"
        
        # Определяем выигрыш
        if reel1 == reel2 == reel3:
            result['win'] = True
        elif reel1 == reel2 or reel2 == reel3 or reel1 == reel3:
            result['win'] = True
    
    return result

async def send_game_result_to_channel(user_info: Dict, game_type: str, outcome: str, 
                                     bet_amount: float, result: Dict) -> Optional[int]:
    """Отправка результата игры в канал"""
    try:
        user_name = get_user_display_name(user_info)
        game_name = get_game_name(game_type)
        outcome_name = get_outcome_name(outcome, game_type)
        
        if result.get('success'):
            if result.get('win'):
                # Сообщение о победе
                win_amount = result.get('win_amount', 0)
                multiplier = result.get('multiplier', 1.0)
                
                text = (
                    f"🎉 <b>ПОБЕДА!</b>\n\n"
                    f"👤 <b>Игрок:</b> {user_name}\n"
                    f"🎮 <b>Игра:</b> {game_name}\n"
                    f"🎯 <b>Исход:</b> {outcome_name}\n"
                    f"💰 <b>Ставка:</b> {format_balance(bet_amount)}\n"
                    f"📈 <b>Коэффициент:</b> {multiplier}x\n"
                    f"💸 <b>Выигрыш:</b> {format_balance(win_amount)}\n"
                )
                
                if result.get('dice_value'):
                    text += f"🎲 <b>Результат:</b> {result['dice_value']}\n"
                
                text += f"\n🎊 <b>Поздравляем с победой!</b> 🎊"
                
            else:
                # Сообщение о проигрыше
                text = (
                    f"😔 <b>ПРОИГРЫШ</b>\n\n"
                    f"👤 <b>Игрок:</b> {user_name}\n"
                    f"🎮 <b>Игра:</b> {game_name}\n"
                    f"🎯 <b>Исход:</b> {outcome_name}\n"
                    f"💰 <b>Ставка:</b> {format_balance(bet_amount)}\n"
                )
                
                if result.get('dice_value'):
                    text += f"🎲 <b>Результат:</b> {result['dice_value']}\n"
                
                text += f"\n💪 <b>Не расстраивайтесь, удача будет на вашей стороне!</b>"
        
        else:
            # Ошибка
            text = (
                f"⚠️ <b>ОШИБКА В ИГРЕ</b>\n\n"
                f"👤 <b>Игрок:</b> {user_name}\n"
                f"🎮 <b>Игра:</b> {game_name}\n"
                f"❌ <b>Ошибка:</b> {result.get('error', 'Неизвестная ошибка')}\n\n"
                f"🛠️ <b>Обратитесь в поддержку для решения проблемы</b>"
            )
        
        # Отправляем сообщение в канал
        message = await bot.send_message(
            chat_id=channel_id,
            text=text,
            parse_mode=ParseMode.HTML
        )
        
        return message.message_id
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки результата в канал: {e}")
        return None

async def process_promo_activation(user_id: int, promo_code: str) -> Dict:
    """Обработка активации промокода"""
    try:
        # Активируем промокод
        result = await db.activate_promo_code(user_id, promo_code)
        
        if result['success']:
            # Обновляем баланс пользователя
            new_balance = db.get_user_balance(user_id)
            
            return {
                'success': True,
                'message': result['message'],
                'amount': result['amount'],
                'new_balance': new_balance
            }
        else:
            return {
                'success': False,
                'message': result['message']
            }
            
    except Exception as e:
        logger.error(f"❌ Ошибка обработки промокода: {e}")
        return {
            'success': False,
            'message': f'Ошибка активации: {str(e)}'
        }

async def send_notification(user_id: int, title: str, message: str, 
                           is_important: bool = False, action_url: str = None, 
                           action_text: str = None) -> bool:
    """Отправка уведомления пользователю"""
    try:
        # Сохраняем в БД
        cursor = db.connection.cursor()
        cursor.execute('''
            INSERT INTO notifications (user_id, type, title, message, is_important, action_url, action_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, 'system', title, message, 1 if is_important else 0, action_url, action_text))
        db.connection.commit()
        
        # Отправляем в Telegram
        text = f"🔔 <b>{title}</b>\n\n{message}"
        
        if action_url and action_text:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(action_text, url=action_url)]
            ])
            await bot.send_message(user_id, text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        else:
            await bot.send_message(user_id, text, parse_mode=ParseMode.HTML)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления {user_id}: {e}")
        return False

async def check_user_blocked(user_id: int) -> bool:
    """Проверка блокировки пользователя"""
    try:
        user = db.get_user(user_id)
        if user and user.get('is_blocked'):
            await bot.send_message(
                user_id,
                f"🚫 <b>Ваш аккаунт заблокирован!</b>\n\n"
                f"<b>Причина:</b> {user.get('block_reason', 'Не указана')}\n\n"
                f"📞 <b>Для разблокировки обратитесь в поддержку:</b> {SUPPORT_USERNAME}"
            )
            return True
        return False
    except:
        return False

# ==================== ОСНОВНЫЕ ОБРАБОТЧИКИ ====================

@dp.message_handler(commands=['start'])
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start"""
    await state.finish()
    
    user_id = message.from_user.id
    
    # Проверяем блокировку
    if await check_user_blocked(user_id):
        return
    
    # Извлекаем реферальный ID
    referer_id = None
    if len(message.text.split()) > 1:
        try:
            referer_id = int(message.text.split()[1])
        except:
            pass
    
    # Добавляем/обновляем пользователя
    db.add_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        referer_id=referer_id,
        language_code=message.from_user.language_code
    )
    
    # Получаем информацию о пользователе
    user_info = db.get_user(user_id)
    balance = db.get_user_balance(user_id)
    
    # Формируем приветственное сообщение
    welcome_text = (
        f"🎰 <b>Добро пожаловать в {NAME_CASINO}!</b>\n\n"
        f"👤 <b>Ваш профиль:</b>\n"
        f"├ ID: <code>{user_id}</code>\n"
        f"├ Баланс: <code>{format_balance(balance)}</code>\n"
        f"└ Регистрация: {format_datetime(datetime.datetime.strptime(user_info['registration_date'], '%Y-%m-%d %H:%M:%S'))}\n\n"
        
        f"🎮 <b>Доступные игры:</b>\n"
        f"├ 🎲 Больше/Меньше\n"
        f"├ 🎯 Угадай число\n"
        f"├ ⚽️ Футбол\n"
        f"├ 🏀 Баскетбол\n"
        f"├ ✊ КНБ\n"
        f"├ 🎡 Рулетка\n"
        f"├ 🎰 Слоты\n"
        f"└ 🎯 Дартс\n\n"
        
        f"💰 <b>Финансы:</b>\n"
        f"├ Минимальная ставка: <code>{MIN_STAVKA}$</code>\n"
        f"├ Максимальная ставка: <code>{LIMIT_STAVKA}$</code>\n"
        f"├ Минимальный вывод: <code>{MIN_WITHDRAW}$</code>\n"
        f"└ Реферальный процент: <code>{lose_withdraw}%</code>\n\n"
        
        f"🎁 <b>Бонусы:</b>\n"
        f"├ Приветственный: <code>{WELCOME_BONUS}%</code>\n"
        f"├ Кэшбэк: <code>{CASHBACK_PROCENT}%</code>\n"
        f"└ Реферальная программа\n\n"
        
        f"⚡ <b>Моментальные выплаты</b>\n"
        f"🛡️ <b>100% честные игры</b>\n"
        f"🔄 <b>Круглосуточная работа</b>\n\n"
        
        f"<b>Выберите действие:</b>"
    )
    
    await send_photo_message(
        user_id,
        'start',
        welcome_text,
        get_main_menu(user_id)
    )

@dp.message_handler(commands=['help'])
async def cmd_help(message: Message):
    """Обработка команды /help"""
    help_text = (
        f"🆘 <b>Помощь по {NAME_CASINO}</b>\n\n"
        
        f"<b>Основные команды:</b>\n"
        f"• /start - Запустить бота\n"
        f"• /balance - Показать баланс\n"
        f"• /stats - Моя статистика\n"
        f"• /promo - Активировать промокод\n"
        f"• /help - Эта справка\n"
        f"• /support - Связь с поддержкой\n\n"
        
        f"<b>Минимальные суммы:</b>\n"
        f"• Ставка: {MIN_STAVKA}$\n"
        f"• Вывод: {MIN_WITHDRAW}$\n\n"
        
        f"<b>Коэффициенты:</b>\n"
        f"• Больше/Меньше: 2.0x\n"
        f"• Угадай число: 6.0x\n"
        f"• Чет/Нечет: 2.0x\n"
        f"• Рулетка (красное/черное): 2.0x\n"
        f"• Рулетка (зеленое): 14.0x\n\n"
        
        f"<b>Поддержка:</b> {SUPPORT_USERNAME}\n"
        f"<b>Время работы:</b> {WORK_HOURS}\n"
        f"<b>Время ответа:</b> {RESPONSE_TIME}\n\n"
        
        f"<b>Правила:</b> https://telegra.ph/Pravila-Noxwat-Casino-01-20\n"
        f"<b>Канал выплат:</b> https://t.me/NoxwatPayments\n"
        f"<b>Новости:</b> https://t.me/noxwat"
    )
    
    await send_photo_message(message.chat.id, 'info', help_text)

@dp.message_handler(commands=['balance'])
async def cmd_balance(message: Message):
    """Обработка команды /balance"""
    user_id = message.from_user.id
    balance = db.get_user_balance(user_id)
    
    balance_text = (
        f"💰 <b>Ваш баланс:</b> <code>{format_balance(balance)}</code>\n\n"
        
        f"📊 <b>Финансовая статистика:</b>\n"
        f"├ Общий депозит: <code>{format_balance(db.get_user(user_id).get('total_deposit', 0))}</code>\n"
        f"├ Общий вывод: <code>{format_balance(db.get_user(user_id).get('total_withdraw', 0))}</code>\n"
        f"├ Выигрыши: <code>{format_balance(db.get_user(user_id).get('total_wins', 0))}</code>\n"
        f"└ Проигрыши: <code>{format_balance(db.get_user(user_id).get('total_losses', 0))}</code>\n\n"
        
        f"⚡ <b>Быстрые действия:</b>"
    )
    
    await send_photo_message(
        user_id,
        'balance',
        balance_text,
        get_balance_keyboard()
    )

@dp.message_handler(commands=['stats'])
async def cmd_stats(message: Message):
    """Обработка команды /stats"""
    user_id = message.from_user.id
    user_info = db.get_user(user_id)
    
    if not user_info:
        await send_photo_message(user_id, 'error', "❌ Информация о пользователе не найдена.")
        return
    
    # Получаем статистику ставок
    bet_stats = db.get_bet_stats(user_id=user_id)
    
    # Формируем текст статистики
    stats_text = (
        f"📊 <b>Ваша статистика</b>\n\n"
        
        f"👤 <b>Профиль:</b>\n"
        f"├ ID: <code>{user_id}</code>\n"
        f"├ Имя: {user_info.get('first_name', '')} {user_info.get('last_name', '')}\n"
        f"├ Username: @{user_info.get('username', 'нет')}\n"
        f"├ Баланс: <code>{format_balance(user_info.get('balance', 0))}</code>\n"
        f"├ VIP уровень: {user_info.get('vip_level', 'STANDARD')}\n"
        f"└ Регистрация: {format_datetime(datetime.datetime.strptime(user_info['registration_date'], '%Y-%m-%d %H:%M:%S'))}\n\n"
        
        f"🎮 <b>Статистика игр:</b>\n"
        f"├ Всего ставок: <code>{bet_stats.get('total_bets', 0)}</code>\n"
        f"├ Общая сумма ставок: <code>{format_balance(bet_stats.get('total_amount', 0))}</code>\n"
        f"├ Побед: <code>{bet_stats.get('win_count', 0)}</code>\n"
        f"├ Поражений: <code>{bet_stats.get('lose_count', 0)}</code>\n"
        f"├ Процент побед: <code>{bet_stats.get('win_rate', 0):.1f}%</code>\n"
        f"├ Выиграно: <code>{format_balance(bet_stats.get('win_amount', 0))}</code>\n"
        f"├ Проиграно: <code>{format_balance(bet_stats.get('lose_amount', 0))}</code>\n"
        f"└ Прибыль: <code>{format_balance(bet_stats.get('profit', 0))}</code>\n\n"
        
        f"👥 <b>Реферальная программа:</b>\n"
        f"├ Приглашено друзей: <code>{user_info.get('referrals_count', 0)}</code>\n"
        f"└ Заработано на рефералах: <code>{format_balance(user_info.get('referral_earnings', 0))}</code>\n\n"
        
        f"🎯 <b>Достижения:</b> {len(json.loads(user_info.get('achievements', '[]')))} получено\n"
        f"⭐ <b>VIP очки:</b> {user_info.get('vip_points', 0)}"
    )
    
    await send_photo_message(
        user_id,
        'stats_user',
        stats_text
    )

@dp.message_handler(commands=['promo'])
async def cmd_promo(message: Message):
    """Обработка команды /promo"""
    promo_text = (
        f"🎁 <b>Промокоды и бонусы</b>\n\n"
        
        f"💎 <b>Преимущества:</b>\n"
        f"• Бесплатные деньги на баланс\n"
        f"• Увеличенные коэффициенты\n"
        f"• Специальные предложения\n"
        f"• Эксклюзивные игры\n\n"
        
        f"🎫 <b>Как получить промокод:</b>\n"
        f"1. Участвуйте в розыгрышах\n"
        f"2. Следите за новостным каналом\n"
        f"3. Приглашайте друзей\n"
        f"4. Достигайте целей\n\n"
        
        f"💰 <b>Текущие акции:</b>\n"
        f"• Приветственный бонус: {WELCOME_BONUS}%\n"
        f"• Кэшбэк за проигрыши: {CASHBACK_PROCENT}%\n"
        f"• Реферальная программа: до {lose_withdraw}%\n\n"
        
        f"⚡ <b>Выберите действие:</b>"
    )
    
    await send_photo_message(
        message.chat.id,
        'promo',
        promo_text,
        get_promo_keyboard()
    )

@dp.message_handler(commands=['support'])
async def cmd_support(message: Message):
    """Обработка команды /support"""
    support_text = (
        f"🆘 <b>Служба поддержки {NAME_CASINO}</b>\n\n"
        
        f"📞 <b>Контакты:</b>\n"
        f"• Техническая поддержка: {SUPPORT_USERNAME}\n"
        f"• Администратор: {ADMIN_USERNAME}\n"
        f"• Новостной канал: https://t.me/noxwat\n"
        f"• Канал выплат: https://t.me/NoxwatPayments\n\n"
        
        f"⏰ <b>Время работы:</b>\n"
        f"• {WORK_HOURS} (МСК)\n"
        f"• Ответ в течение: {RESPONSE_TIME}\n\n"
        
        f"🔧 <b>Мы поможем с:</b>\n"
        f"• Пополнением и выводом средств\n"
        f"• Техническими проблемами\n"
        f"• Вопросами по играм\n"
        f"• Блокировкой аккаунта\n"
        f"• Предложениями и жалобами\n\n"
        
        f"⚠️ <b>Важно:</b>\n"
        f"• Не сообщайте никому данные своей учетной записи\n"
        f"• Все операции проводятся только через бота\n"
        f"• Администрация никогда не просит перевести деньги\n"
        f"• Сохраняйте скриншоты всех операций\n\n"
        
        f"📝 <b>Для обращения напишите сообщение с описанием проблемы:</b>"
    )
    
    await send_photo_message(message.chat.id, 'info', support_text)
    await UserStates.waiting_for_support_message.set()

@dp.message_handler(commands=['admin'])
async def cmd_admin(message: Message):
    """Команда /admin для админов"""
    user_id = message.from_user.id
    
    if user_id not in ADMIN:
        await send_photo_message(
            user_id,
            'error',
            "❌ <b>Доступ запрещен!</b>\n\nУ вас нет прав администратора.",
            get_main_menu(user_id)
        )
        return
    
    admin_text = (
        f"👑 <b>Админ панель {NAME_CASINO}</b>\n\n"
        
        f"📊 <b>Статистика системы:</b>\n"
        f"├ Пользователей: <code>{db.get_statistics().get('total_users', 0)}</code>\n"
        f"├ Онлайн: <code>{db.get_active_users_count(1)}</code>\n"
        f"├ Ставок сегодня: <code>{db.get_statistics().get('total_bets', 0)}</code>\n"
        f"├ Прибыль сегодня: <code>{format_balance(db.get_statistics().get('profit', 0))}</code>\n"
        f"└ Баланс системы: <code>{format_balance(0)}</code>\n\n"
        
        f"⚡ <b>Выберите раздел для управления:</b>"
    )
    
    await send_photo_message(
        user_id,
        'admin',
        admin_text,
        get_admin_keyboard()
    )

# ==================== ОБРАБОТЧИКИ КНОПОК ГЛАВНОГО МЕНЮ ====================

@dp.message_handler(lambda message: message.text == '💰 Мой баланс')
async def menu_balance(message: Message):
    """Обработка кнопки 'Мой баланс'"""
    await cmd_balance(message)

@dp.message_handler(lambda message: message.text == '🎲 Сделать ставку')
async def menu_bet(message: Message):
    """Обработка кнопки 'Сделать ставку'"""
    user_id = message.from_user.id
    
    # Проверяем блокировку
    if await check_user_blocked(user_id):
        return
    
    balance = db.get_user_balance(user_id)
    
    if balance < MIN_STAVKA:
        await send_photo_message(
            user_id,
            'error',
            f"❌ <b>Недостаточно средств для ставки</b>\n\n"
            f"💰 Ваш баланс: <code>{format_balance(balance)}</code>\n"
            f"🎲 Минимальная ставка: <code>{MIN_STAVKA}$</code>\n\n"
            f"💳 <b>Пополните баланс, чтобы начать играть!</b>\n"
            f"Или получите бонус за регистрацию!",
            get_balance_keyboard()
        )
        return
    
    games_text = (
        f"🎮 <b>Выберите игру</b>\n\n"
        f"💰 <b>Ваш баланс:</b> <code>{format_balance(balance)}</code>\n"
        f"🎯 <b>Минимальная ставка:</b> {MIN_STAVKA}$\n"
        f"📊 <b>Максимальная ставка:</b> {LIMIT_STAVKA}$\n\n"
        f"✨ <b>Доступные игры:</b>"
    )
    
    await send_photo_message(
        user_id,
        'game',
        games_text,
        get_games_keyboard()
    )

@dp.message_handler(lambda message: message.text == '📎 Реферальная программа')
async def menu_referral(message: Message):
    """Обработка кнопки 'Реферальная программа'"""
    user_id = message.from_user.id
    user_info = db.get_user(user_id)
    
    referral_link = f"https://t.me/{NICNAME}?start={user_id}"
    
    referral_text = (
        f"👥 <b>Реферальная программа {NAME_CASINO}</b>\n\n"
        
        f"💎 <b>Зарабатывайте вместе с нами!</b>\n"
        f"Приглашайте друзей и получайте бонусы с их ставок.\n\n"
        
        f"💰 <b>Ваша ссылка для приглашений:</b>\n"
        f"<code>{referral_link}</code>\n\n"
        
        f"📊 <b>Ваша статистика:</b>\n"
        f"├ Приглашено друзей: <code>{user_info.get('referrals_count', 0)}</code>\n"
        f"├ Активных рефералов: <code>{user_info.get('active_referrals', 0)}</code>\n"
        f"└ Заработано: <code>{format_balance(user_info.get('referral_earnings', 0))}</code>\n\n"
        
        f"🎯 <b>Условия программы:</b>\n"
        f"├ Вы получаете {lose_withdraw}% от проигрышей приглашенных\n"
        f"├ Минимальная ставка реферала: {min_stavka_referal}$\n"
        f"├ Вывод доступен от {MIN_WITHDRAW}$\n"
        f"└ Бонусы начисляются мгновенно\n\n"
        
        f"🏆 <b>Бонусы за количество рефералов:</b>\n"
        f"├ 5 рефералов: +5% к реферальному проценту\n"
        f"├ 10 рефералов: +10% к реферальному проценту\n"
        f"├ 25 рефералов: VIP статус на месяц\n"
        f"└ 50 рефералов: Персональный менеджер\n\n"
        
        f"⚡ <b>Выберите действие:</b>"
    )
    
    await send_photo_message(
        user_id,
        'referral',
        referral_text,
        get_referral_keyboard(user_id)
    )

@dp.message_handler(lambda message: message.text == '💭 Информация')
async def menu_info(message: Message):
    """Обработка кнопки 'Информация'"""
    info_text = (
        f"ℹ️ <b>Информация о {NAME_CASINO}</b>\n\n"
        
        f"🎰 <b>О нашем казино:</b>\n"
        f"• Открыто в 2023 году\n"
        f"• Лицензия на азартные игры\n"
        f"• Честные игры с открытым исходным кодом\n"
        f"• Мгновенные выплаты 24/7\n"
        f"• Поддержка на русском языке\n\n"
        
        f"🔒 <b>Безопасность:</b>\n"
        f"• SSL шифрование всех данных\n"
        f"• Двухфакторная аутентификация\n"
        f"• Аудит игр сторонними компаниями\n"
        f"• Защита от DDoS атак\n"
        f"• Резервное копирование данных\n\n"
        
        f"💰 <b>Финансы:</b>\n"
        f"• Пополнение: от {MIN_STAVKA}$\n"
        f"• Вывод: от {MIN_WITHDRAW}$\n"
        f"• Комиссия на вывод: 0%\n"
        f"• Время вывода: 1-15 минут\n"
        f"• Поддерживаемые валюты: USDT (TRC-20)\n\n"
        
        f"🎮 <b>Игры:</b>\n"
        f"• 10+ различных игр\n"
        f"• Коэффициенты до 20x\n"
        f"• Минимальная ставка: {MIN_STAVKA}$\n"
        f"• Максимальная ставка: {LIMIT_STAVKA}$\n"
        f"• RNG сертифицирован\n\n"
        
        f"🎁 <b>Бонусы:</b>\n"
        f"• Приветственный: {WELCOME_BONUS}%\n"
        f"• Кэшбэк: {CASHBACK_PROCENT}%\n"
        f"• Реферальная программа: до {lose_withdraw}%\n"
        f"• Ежедневные бонусы\n"
        f"• Сезонные акции\n\n"
        
        f"📞 <b>Контакты:</b>\n"
        f"• Поддержка: {SUPPORT_USERNAME}\n"
        f"• Администрация: {ADMIN_USERNAME}\n"
        f"• Новости: https://t.me/noxwat\n"
        f"• Выплаты: https://t.me/NoxwatPayments\n"
        f"• Работа: {WORK_HOURS} (МСК)\n\n"
        
        f"⚡ <b>Выберите раздел:</b>"
    )
    
    await send_photo_message(
        message.chat.id,
        'info',
        info_text,
        get_info_keyboard()
    )

@dp.message_handler(lambda message: message.text == '🎁 Промокоды')
async def menu_promo(message: Message):
    """Обработка кнопки 'Промокоды'"""
    await cmd_promo(message)

@dp.message_handler(lambda message: message.text == '📊 Моя статистика')
async def menu_stats(message: Message):
    """Обработка кнопки 'Моя статистика'"""
    await cmd_stats(message)

@dp.message_handler(lambda message: message.text == '🆘 Поддержка')
async def menu_support(message: Message):
    """Обработка кнопки 'Поддержка'"""
    await cmd_support(message)

@dp.message_handler(lambda message: message.text == '⚙️ Настройки')
async def menu_settings(message: Message):
    """Обработка кнопки 'Настройки'"""
    user_id = message.from_user.id
    user_info = db.get_user(user_id)
    
    settings_text = (
        f"⚙️ <b>Настройки аккаунта</b>\n\n"
        
        f"👤 <b>Профиль:</b>\n"
        f"├ ID: <code>{user_id}</code>\n"
        f"├ Имя: {user_info.get('first_name', '')} {user_info.get('last_name', '')}\n"
        f"├ Username: @{user_info.get('username', 'нет')}\n"
        f"├ Язык: {user_info.get('language_code', 'ru').upper()}\n"
        f"└ Регистрация: {format_datetime(datetime.datetime.strptime(user_info['registration_date'], '%Y-%m-%d %H:%M:%S'))}\n\n"
        
        f"🔔 <b>Уведомления:</b>\n"
        f"├ Новости и акции: ✅ Включено\n"
        f"├ Выплаты: ✅ Включено\n"
        f"├ Бонусы: ✅ Включено\n"
        f"└ Технические работы: ✅ Включено\n\n"
        
        f"🎮 <b>Игровые настройки:</b>\n"
        f"├ Автоповтор ставки: ❌ Выключено\n"
        f"├ Звуки в играх: ✅ Включено\n"
        f"├ Анимации: ✅ Включено\n"
        f"└ Быстрая ставка: ❌ Выключено\n\n"
        
        f"🔒 <b>Безопасность:</b>\n"
        f"├ Двухфакторная аутентификация: ❌ Выключено\n"
        f"├ Уведомления о входе: ✅ Включено\n"
        f"├ История сессий: 📋 Доступна\n"
        f"└ Смена пароля: 🔄 Доступна\n\n"
        
        f"📊 <b>Статистика:</b>\n"
        f"├ Публичная статистика: ✅ Включено\n"
        f"├ Топ игроков: 👁️‍🗨️ Виден\n"
        f"└ История игр: 📚 Сохраняется\n\n"
        
        f"⚡ <b>Действия:</b>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('🌐 Сменить язык', callback_data='change_language')],
        [InlineKeyboardButton('🔔 Настройка уведомлений', callback_data='notification_settings')],
        [InlineKeyboardButton('🎮 Игровые настройки', callback_data='game_settings')],
        [InlineKeyboardButton('🔒 Безопасность', callback_data='security_settings')],
        [InlineKeyboardButton('📊 Настройки статистики', callback_data='stats_settings')],
        [InlineKeyboardButton('🗑️ Удалить историю', callback_data='clear_history')],
        [InlineKeyboardButton('🚪 Выйти из аккаунта', callback_data='logout')],
        [InlineKeyboardButton('🔙 В меню', callback_data='back_to_menu')]
    ])
    
    await send_photo_message(user_id, 'menu', settings_text, keyboard)

@dp.message_handler(lambda message: message.text == '👑 Админка')
async def menu_admin(message: Message):
    """Обработка кнопки 'Админка'"""
    await cmd_admin(message)

# ==================== CALLBACK ОБРАБОТЧИКИ ДЛЯ ИГР ====================

@dp.callback_query_handler(lambda c: c.data == 'back_to_menu')
async def callback_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.finish()
    await callback.message.delete()
    await send_photo_message(
        callback.message.chat.id,
        'menu',
        f"🎰 <b>{NAME_CASINO}</b>\n\nВыберите действие:",
        get_main_menu(callback.from_user.id)
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'back_to_games')
async def callback_back_to_games(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору игры"""
    await state.finish()
    user_id = callback.from_user.id
    balance = db.get_user_balance(user_id)
    
    games_text = (
        f"🎮 <b>Выберите игру</b>\n\n"
        f"💰 <b>Ваш баланс:</b> <code>{format_balance(balance)}</code>\n"
        f"🎯 <b>Минимальная ставка:</b> {MIN_STAVKA}$\n"
        f"📊 <b>Максимальная ставка:</b> {LIMIT_STAVKA}$\n\n"
        f"✨ <b>Доступные игры:</b>"
    )
    
    await edit_message_with_photo(callback, 'game', games_text, get_games_keyboard())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('game_'))
async def callback_select_game(callback: CallbackQuery, state: FSMContext):
    """Выбор игры"""
    game_type = callback.data.replace('game_', '')
    
    await state.update_data(game_type=game_type)
    
    if game_type == 'more_less':
        game_text = (
            f"🎲 <b>Больше/Меньше</b>\n\n"
            f"📖 <b>Правила игры:</b>\n"
            f"Бросается игральная кость (1-6).\n"
            f"• <b>Больше</b> (4-6) - выигрыш если выпадет 4, 5 или 6\n"
            f"• <b>Меньше</b> (1-3) - выигрыш если выпадет 1, 2 или 3\n\n"
            f"💰 <b>Коэффициент:</b> {db.get_coefficient('KEF1')}x\n"
            f"🎯 <b>Шанс победы:</b> 50%\n"
            f"⚡ <b>Результат:</b> Мгновенный\n\n"
            f"✨ <b>Выберите исход:</b>"
        )
        photo_type = 'dice'
        keyboard = get_more_less_keyboard()
    
    elif game_type == 'number':
        game_text = (
            f"🎯 <b>Угадай число</b>\n\n"
            f"📖 <b>Правила игры:</b>\n"
            f"Бросается игральная кость (1-6).\n"
            f"Выберите число от 1 до 6.\n"
            f"Если вы угадаете выпавшее число - вы выигрываете!\n\n"
            f"💰 <b>Коэффициент:</b> {db.get_coefficient('KEF2')}x\n"
            f"🎯 <b>Шанс победы:</b> 16.67%\n"
            f"⚡ <b>Результат:</b> Мгновенный\n\n"
            f"✨ <b>Выберите число:</b>"
        )
        photo_type = 'dice'
        keyboard = get_numbers_keyboard()
    
    elif game_type == 'even_odd':
        game_text = (
            f"🎲 <b>Чет/Нечет</b>\n\n"
            f"📖 <b>Правила игры:</b>\n"
            f"Бросается игральная кость (1-6).\n"
            f"• <b>Чет</b> - выигрыш если выпадет четное число (2, 4, 6)\n"
            f"• <b>Нечет</b> - выигрыш если выпадет нечетное число (1, 3, 5)\n\n"
            f"💰 <b>Коэффициент:</b> {db.get_coefficient('KEF3')}x\n"
            f"🎯 <b>Шанс победы:</b> 50%\n"
            f"⚡ <b>Результат:</b> Мгновенный\n\n"
            f"✨ <b>Выберите исход:</b>"
        )
        photo_type = 'dice'
        keyboard = get_even_odd_keyboard()
    
    elif game_type == 'roulette':
        game_text = (
            f"🎡 <b>Рулетка</b>\n\n"
            f"📖 <b>Правила игры:</b>\n"
            f"Вращается колесо рулетки (0-36).\n"
            f"• <b>🔴 Красное</b> - выигрыш если выпадет красное число\n"
            f"• <b>⚫️ Черное</b> - выигрыш если выпадет черное число\n"
            f"• <b>🟢 Зеленое</b> - выигрыш если выпадет 0\n\n"
            f"💰 <b>Коэффициенты:</b>\n"
            f"├ Красное/Черное: {db.get_coefficient('KEF5')}x\n"
            f"└ Зеленое: {db.get_coefficient('KEF6')}x\n\n"
            f"🎯 <b>Шанс победы:</b>\n"
            f"├ Красное/Черное: 48.65%\n"
            f"└ Зеленое: 2.70%\n\n"
            f"⚡ <b>Результат:</b> Мгновенный\n\n"
            f"✨ <b>Выберите ставку:</b>"
        )
        photo_type = 'roulette'
        keyboard = get_roulette_keyboard()
    
    elif game_type == 'football':
        game_text = (
            f"⚽️ <b>Футбол</b>\n\n"
            f"📖 <b>Правила игры:</b>\n"
            f"Симуляция удара по воротам.\n"
            f"• <b>⚽️ Гол</b> - выигрыш если мяч попадет в ворота\n"
            f"• <b>❌ Мимо</b> - выигрыш если мяч не попадет в ворота\n\n"
            f"💰 <b>Коэффициенты:</b>\n"
            f"├ Гол: {db.get_coefficient('KEF12')}x\n"
            f"└ Мимо: {db.get_coefficient('KEF13')}x\n\n"
            f"🎯 <b>Шанс победы:</b> 50%\n"
            f"⚡ <b>Результат:</b> Мгновенный\n\n"
            f"✨ <b>Выберите исход:</b>"
        )
        photo_type = 'football'
        keyboard = get_football_keyboard()
    
    elif game_type == 'basketball':
        game_text = (
            f"🏀 <b>Баскетбол</b>\n\n"
            f"📖 <b>Правила игры:</b>\n"
            f"Симуляция броска в кольцо.\n"
            f"• <b>🏀 Гол</b> - выигрыш если мяч попадет в кольцо\n"
            f"• <b>❌ Мимо</b> - выигрыш если мяч не попадет в кольцо\n\n"
            f"💰 <b>Коэффициенты:</b>\n"
            f"├ Гол: {db.get_coefficient('KEF10')}x\n"
            f"└ Мимо: {db.get_coefficient('KEF11')}x\n\n"
            f"🎯 <b>Шанс победы:</b> 50%\n"
            f"⚡ <b>Результат:</b> Мгновенный\n\n"
            f"✨ <b>Выберите исход:</b>"
        )
        photo_type = 'basketball'
        keyboard = get_basketball_keyboard()
    
    elif game_type == 'knb':
        game_text = (
            f"✊ <b>Камень-Ножницы-Бумага</b>\n\n"
            f"📖 <b>Правила игры:</b>\n"
            f"Классическая игра против бота.\n"
            f"• <b>✊ Камень</b> бьет ножницы\n"
            f"• <b>✌️ Ножницы</b> бьют бумагу\n"
            f"• <b>✋ Бумага</b> бьет камень\n\n"
            f"💰 <b>Коэффициент:</b> {db.get_coefficient('KEF15')}x\n"
            f"🎯 <b>Шанс победы:</b> {db.get_coefficient('KNB_CHANCE')}%\n"
            f"⚡ <b>Результат:</b> Мгновенный\n\n"
            f"✨ <b>Выберите ваш ход:</b>"
        )
        photo_type = 'knb'
        keyboard = get_knb_keyboard()
    
    elif game_type == 'slots':
        game_text = (
            f"🎰 <b>Слоты</b>\n\n"
            f"📖 <b>Правила игры:</b>\n"
            f"Вращение 3 барабанов с символами.\n"
            f"• 3 одинаковых символа: {db.get_coefficient('KEF9')}x\n"
            f"• 2 одинаковых символа: {db.get_coefficient('KEF8')}x\n"
            f"• Любая комбинация: {db.get_coefficient('KEF7')}x\n\n"
            f"💰 <b>Джекпот:</b> {db.get_coefficient('KEF9')}x\n"
            f"🎯 <b>Шанс победы:</b> 30%\n"
            f"⚡ <b>Результат:</b> Мгновенный\n\n"
            f"✨ <b>Сделайте ставку:</b>"
        )
        photo_type = 'slots'
        keyboard = get_slots_keyboard()
    
    else:
        game_text = "🎮 <b>Выберите игру</b>"
        photo_type = 'game'
        keyboard = get_games_keyboard()
    
    await edit_message_with_photo(callback, photo_type, game_text, keyboard)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('outcome_'))
async def callback_select_outcome(callback: CallbackQuery, state: FSMContext):
    """Выбор исхода в игре"""
    user_id = callback.from_user.id
    outcome = callback.data.replace('outcome_', '')
    
    data = await state.get_data()
    game_type = data.get('game_type')
    
    if not game_type:
        await callback.answer("❌ Сначала выберите игру")
        return
    
    await state.update_data(outcome=outcome)
    
    # Проверяем баланс
    balance = db.get_user_balance(user_id)
    
    # Получаем информацию об игре
    game_name = get_game_name(game_type)
    outcome_name = get_outcome_name(outcome, game_type)
    multiplier = get_multiplier(game_type, outcome)
    
    await edit_message_with_photo(
        callback,
        'enter_amount',
        f"💰 <b>Введите сумму ставки</b>\n\n"
        f"🎮 <b>Игра:</b> {game_name}\n"
        f"🎯 <b>Исход:</b> {outcome_name}\n"
        f"📈 <b>Коэффициент:</b> {multiplier}x\n\n"
        f"💸 <b>Ваш баланс:</b> <code>{format_balance(balance)}</code>\n"
        f"🎲 <b>Минимальная ставка:</b> <code>{MIN_STAVKA}$</code>\n"
        f"📊 <b>Максимальная ставка:</b> <code>{LIMIT_STAVKA}$</code>\n\n"
        f"💎 <b>Примеры:</b>\n"
        f"• 1.5 (полтора доллара)\n"
        f"• 10 (десять долларов)\n"
        f"• 0.5 (пятьдесят центов)\n\n"
        f"📝 <b>Введите сумму цифрами:</b>",
        get_cancel_keyboard()
    )
    
    await UserStates.waiting_for_bet_amount.set()
    await callback.answer()

@dp.message_handler(state=UserStates.waiting_for_bet_amount)
async def process_bet_amount(message: Message, state: FSMContext):
    """Обработка суммы ставки"""
    user_id = message.from_user.id
    
    # Проверяем блокировку
    if await check_user_blocked(user_id):
        await state.finish()
        return
    
    try:
        # Парсим сумму
        amount_str = message.text.replace(',', '.').strip()
        amount = float(amount_str)
        
        # Проверяем минимальную ставку
        if amount < MIN_STAVKA:
            await send_photo_message(
                user_id,
                'error',
                f"❌ <b>Слишком маленькая ставка</b>\n\n"
                f"Минимальная ставка: <code>{MIN_STAVKA}$</code>\n"
                f"Ваша ставка: <code>{format_balance(amount)}</code>\n\n"
                f"📝 <b>Введите сумму еще раз:</b>",
                get_cancel_keyboard()
            )
            return
        
        # Проверяем максимальную ставку
        if amount > LIMIT_STAVKA:
            await send_photo_message(
                user_id,
                'error',
                f"❌ <b>Слишком большая ставка</b>\n\n"
                f"Максимальная ставка: <code>{LIMIT_STAVKA}$</code>\n"
                f"Ваша ставка: <code>{format_balance(amount)}</code>\n\n"
                f"📝 <b>Введите сумму еще раз:</b>",
                get_cancel_keyboard()
            )
            return
        
        # Проверяем баланс
        balance = db.get_user_balance(user_id)
        if amount > balance:
            await send_photo_message(
                user_id,
                'error',
                f"❌ <b>Недостаточно средств</b>\n\n"
                f"Ваш баланс: <code>{format_balance(balance)}</code>\n"
                f"Сумма ставки: <code>{format_balance(amount)}</code>\n"
                f"Не хватает: <code>{format_balance(amount - balance)}</code>\n\n"
                f"💳 <b>Пополните баланс или введите меньшую сумму:</b>",
                get_cancel_keyboard()
            )
            return
        
        # Получаем данные об игре
        data = await state.get_data()
        game_type = data.get('game_type')
        outcome = data.get('outcome')
        
        if not game_type or not outcome:
            await send_photo_message(user_id, 'error', "❌ Ошибка: данные игры не найдены. Начните заново.")
            await state.finish()
            return
        
        # Обрабатываем игру
        user_info = db.get_user(user_id)
        result = await process_game(user_id, game_type, outcome, amount)
        
        if result['success']:
            # Отправляем результат в канал
            channel_message_id = await send_game_result_to_channel(user_info, game_type, outcome, amount, result)
            
            # Обновляем сообщение в канале ID если есть
            if channel_message_id:
                db.connection.cursor().execute(
                    'UPDATE bets SET channel_message_id = ? WHERE user_id = ? ORDER BY id DESC LIMIT 1',
                    (channel_message_id, user_id)
                )
                db.connection.commit()
            
            # Формируем сообщение для пользователя
            game_name = get_game_name(game_type)
            outcome_name = get_outcome_name(outcome, game_type)
            multiplier = result.get('multiplier', 1.0)
            new_balance = result.get('new_balance', balance - amount)
            
            if result['win']:
                win_amount = result.get('win_amount', 0)
                result_text = (
                    f"🎉 <b>ПОБЕДА!</b>\n\n"
                    f"🎮 <b>Игра:</b> {game_name}\n"
                    f"🎯 <b>Исход:</b> {outcome_name}\n"
                    f"💰 <b>Ставка:</b> {format_balance(amount)}\n"
                    f"📈 <b>Коэффициент:</b> {multiplier}x\n"
                    f"💸 <b>Выигрыш:</b> {format_balance(win_amount)}\n"
                )
                
                if result.get('dice_value'):
                    result_text += f"🎲 <b>Результат:</b> {result['dice_value']}\n"
                
                result_text += f"\n💰 <b>Новый баланс:</b> <code>{format_balance(new_balance)}</code>\n\n"
                result_text += f"🎊 <b>Поздравляем с победой!</b> 🎊"
                
                photo_type = 'win'
                
            else:
                result_text = (
                    f"😔 <b>ПРОИГРЫШ</b>\n\n"
                    f"🎮 <b>Игра:</b> {game_name}\n"
                    f"🎯 <b>Исход:</b> {outcome_name}\n"
                    f"💰 <b>Ставка:</b> {format_balance(amount)}\n"
                    f"💸 <b>Проиграно:</b> {format_balance(amount)}\n"
                )
                
                if result.get('dice_value'):
                    result_text += f"🎲 <b>Результат:</b> {result['dice_value']}\n"
                
                result_text += f"\n💰 <b>Новый баланс:</b> <code>{format_balance(new_balance)}</code>\n\n"
                result_text += f"💪 <b>Не расстраивайтесь, удача будет на вашей стороне в следующий раз!</b>"
                
                photo_type = 'lose'
            
            # Проверяем кэшбэк
            if not result['win'] and amount > CASHBACK_LIMIT:
                cashback_amount = amount * (CASHBACK_PROCENT / 100)
                cashback_text = f"\n\n💎 <b>Кэшбэк:</b> Вы получаете кэшбэк {CASHBACK_PROCENT}% = {format_balance(cashback_amount)}"
                result_text += cashback_text
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton('🎮 Сделать еще ставку', callback_data='make_another_bet')],
                [InlineKeyboardButton('💰 Мой баланс', callback_data='my_balance')],
                [InlineKeyboardButton('📊 Статистика', callback_data='my_stats')],
                [InlineKeyboardButton('🔙 В меню', callback_data='back_to_menu')]
            ])
            
            await send_photo_message(user_id, photo_type, result_text, keyboard)
            
        else:
            # Ошибка в игре
            error_text = (
                f"⚠️ <b>ОШИБКА В ИГРЕ</b>\n\n"
                f"❌ <b>Причина:</b> {result.get('error', 'Неизвестная ошибка')}\n\n"
                f"🛠️ <b>Средства возвращены на ваш баланс.</b>\n"
                f"📞 <b>Если ошибка повторяется, обратитесь в поддержку:</b> {SUPPORT_USERNAME}"
            )
            
            # Возвращаем средства
            await db.add_to_balance(user_id, amount, 'refund', 'Возврат средств при ошибке в игре')
            
            await send_photo_message(user_id, 'error', error_text, get_back_menu_keyboard())
        
        await state.finish()
        
    except ValueError:
        await send_photo_message(
            user_id,
            'error',
            "❌ <b>Неверный формат суммы</b>\n\n"
            "Введите сумму цифрами (например: 1.5 или 10):\n"
            "• Используйте точку или запятую для дробных чисел\n"
            "• Не используйте буквы или символы\n\n"
            "<b>Примеры правильного ввода:</b>\n"
            "• 1.5\n"
            "• 10\n"
            "• 0.5\n"
            "• 25.75",
            get_cancel_keyboard()
        )
    except Exception as e:
        logger.error(f"❌ Ошибка обработки ставки {user_id}: {e}")
        await send_photo_message(
            user_id,
            'error',
            "❌ <b>Произошла ошибка при обработке ставки</b>\n\n"
            "🛠️ <b>Техническая информация:</b>\n"
            f"<code>{str(e)[:100]}</code>\n\n"
            "📞 <b>Обратитесь в поддержку:</b> {SUPPORT_USERNAME}"
        )
        await state.finish()

# ==================== ОБРАБОТЧИКИ ДЛЯ БАЛАНСА ====================

@dp.callback_query_handler(lambda c: c.data == 'deposit')
async def callback_deposit(callback: CallbackQuery):
    """Обработка кнопки 'Пополнить баланс'"""
    deposit_text = (
        f"💳 <b>Пополнение баланса</b>\n\n"
        
        f"💰 <b>Ваш баланс:</b> <code>{format_balance(db.get_user_balance(callback.from_user.id))}</code>\n\n"
        
        f"🎯 <b>Требования:</b>\n"
        f"├ Минимальный депозит: <code>{MIN_STAVKA}$</code>\n"
        f"├ Валюта: USDT (TRC-20)\n"
        f"├ Комиссия: 0%\n"
        f"└ Время зачисления: 1-15 минут\n\n"
        
        f"🎁 <b>Бонусы при пополнении:</b>\n"
        f"├ Первый депозит: +{WELCOME_BONUS}%\n"
        f"├ Крупный депозит (100$+): +5%\n"
        f"└ VIP депозит (1000$+): +10%\n\n"
        
        f"📝 <b>Инструкция:</b>\n"
        f"1. Введите сумму депозита\n"
        f"2. Получите адрес для перевода\n"
        f"3. Переведите USDT на указанный адрес\n"
        f"4. Средства зачислятся автоматически\n\n"
        
        f"⚠️ <b>Внимание:</b>\n"
        f"• Отправляйте только USDT (TRC-20)\n"
        f"• Минимальная сумма перевода: 1 USDT\n"
        f"• Сохраняйте TXID транзакции\n"
        f"• При проблемах - обращайтесь в поддержку\n\n"
        
        f"💎 <b>Введите сумму для пополнения (в долларах):</b>"
    )
    
    await edit_message_with_photo(callback, 'deposit', deposit_text, get_cancel_keyboard())
    await UserStates.waiting_for_deposit_amount.set()
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'withdraw')
async def callback_withdraw(callback: CallbackQuery):
    """Обработка кнопки 'Вывести средства'"""
    user_id = callback.from_user.id
    balance = db.get_user_balance(user_id)
    
    if balance < MIN_WITHDRAW:
        await edit_message_with_photo(
            callback,
            'error',
            f"❌ <b>Недостаточно средств для вывода</b>\n\n"
            f"💰 Ваш баланс: <code>{format_balance(balance)}</code>\n"
            f"📤 Минимальная сумма вывода: <code>{MIN_WITHDRAW}$</code>\n"
            f"Не хватает: <code>{format_balance(MIN_WITHDRAW - balance)}</code>\n\n"
            f"🎲 <b>Сделайте ставку или пополните баланс!</b>",
            get_back_menu_keyboard()
        )
        await callback.answer()
        return
    
    withdraw_text = (
        f"📤 <b>Вывод средств</b>\n\n"
        
        f"💰 <b>Ваш баланс:</b> <code>{format_balance(balance)}</code>\n\n"
        
        f"🎯 <b>Требования:</b>\n"
        f"├ Минимальный вывод: <code>{MIN_WITHDRAW}$</code>\n"
        f"├ Валюта: USDT (TRC-20)\n"
        f"├ Комиссия: 0%\n"
        f"└ Время выплаты: 1-15 минут\n\n"
        
        f"📝 <b>Инструкция:</b>\n"
        f"1. Введите сумму вывода\n"
        f"2. Введите адрес кошелька USDT (TRC-20)\n"
        f"3. Подтвердите вывод\n"
        f"4. Средства будут отправлены на ваш кошелек\n\n"
        
        f"⚠️ <b>Внимание:</b>\n"
        f"• Вывод только на кошельки USDT (TRC-20)\n"
        f"• Проверяйте правильность адреса\n"
        f"• Вывод только на кошелек отправителя\n"
        f"• При проблемах - обращайтесь в поддержку\n\n"
        
        f"💎 <b>Введите сумму для вывода (в долларах):</b>"
    )
    
    await edit_message_with_photo(callback, 'withdraw', withdraw_text, get_cancel_keyboard())
    await UserStates.waiting_for_withdraw_amount.set()
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'activate_promo')
async def callback_activate_promo(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Активировать промокод'"""
    promo_text = (
        f"🎫 <b>Активация промокода</b>\n\n"
        
        f"💎 <b>Что такое промокод?</b>\n"
        f"Промокод - это специальный код, который дает бонусы:\n"
        f"• Бесплатные деньги на баланс\n"
        f"• Увеличенные коэффициенты\n"
        f"• Специальные возможности\n\n"
        
        f"🎯 <b>Где получить промокод?</b>\n"
        f"• В новостном канале {NAME_CASINO}\n"
        f"• У партнеров проекта\n"
        f"• В реферальной программе\n"
        f"• На специальных мероприятиях\n\n"
        
        f"⚠️ <b>Ограничения:</b>\n"
        f"• Один промокод можно активировать только один раз\n"
        f"• Промокоды имеют срок действия\n"
        f"• Для некоторых промокодов есть условия\n"
        f"• Администрация может отозвать промокод\n\n"
        
        f"✨ <b>Введите промокод:</b>"
    )
    
    await edit_message_with_photo(callback, 'promo', promo_text, get_cancel_keyboard())
    await UserStates.waiting_for_promo_code.set()
    await callback.answer()

@dp.message_handler(state=UserStates.waiting_for_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    """Обработка промокода"""
    user_id = message.from_user.id
    promo_code = message.text.strip().upper()
    
    # Активируем промокод
    result = await process_promo_activation(user_id, promo_code)
    
    if result['success']:
        success_text = (
            f"🎉 <b>Промокод активирован!</b>\n\n"
            f"🎫 <b>Код:</b> <code>{promo_code}</code>\n"
            f"💰 <b>Получено:</b> <code>{format_balance(result['amount'])}</code>\n"
            f"💸 <b>Новый баланс:</b> <code>{format_balance(result['new_balance'])}</code>\n\n"
            f"🎲 <b>Удачи в играх!</b>"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton('🎮 Сделать ставку', callback_data='make_bet_after_promo')],
            [InlineKeyboardButton('💰 Мой баланс', callback_data='my_balance')],
            [InlineKeyboardButton('🔙 В меню', callback_data='back_to_menu')]
        ])
        
        await send_photo_message(user_id, 'success', success_text, keyboard)
    else:
        error_text = (
            f"❌ <b>Ошибка активации промокода</b>\n\n"
            f"🎫 <b>Код:</b> <code>{promo_code}</code>\n"
            f"📖 <b>Причина:</b> {result['message']}\n\n"
            f"💡 <b>Проверьте:</b>\n"
            f"• Правильность написания промокода\n"
            f"• Не истек ли срок действия\n"
            f"• Не использовали ли вы уже этот промокод\n"
            f"• Выполнены ли условия промокода\n\n"
            f"✨ <b>Попробуйте еще раз или введите другой промокод:</b>"
        )
        
        await send_photo_message(user_id, 'error', error_text, get_cancel_keyboard())
        return
    
    await state.finish()

# ==================== АДМИН ОБРАБОТЧИКИ ====================

@dp.callback_query_handler(lambda c: c.data == 'back_to_admin')
async def callback_back_to_admin(callback: CallbackQuery, state: FSMContext):
    """Возврат в админ панель"""
    await state.finish()
    
    user_id = callback.from_user.id
    
    if user_id not in ADMIN:
        await callback.answer("❌ Доступ запрещен")
        return
    
    admin_text = (
        f"👑 <b>Админ панель {NAME_CASINO}</b>\n\n"
        
        f"📊 <b>Статистика системы:</b>\n"
        f"├ Пользователей: <code>{db.get_statistics().get('total_users', 0)}</code>\n"
        f"├ Онлайн: <code>{db.get_active_users_count(1)}</code>\n"
        f"├ Ставок сегодня: <code>{db.get_statistics().get('total_bets', 0)}</code>\n"
        f"├ Прибыль сегодня: <code>{format_balance(db.get_statistics().get('profit', 0))}</code>\n"
        f"└ Баланс системы: <code>{format_balance(0)}</code>\n\n"
        
        f"⚡ <b>Выберите раздел для управления:</b>"
    )
    
    await edit_message_with_photo(callback, 'admin', admin_text, get_admin_keyboard())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'admin_stats_project')
async def callback_admin_stats_project(callback: CallbackQuery):
    """Статистика проекта"""
    user_id = callback.from_user.id
    
    if user_id not in ADMIN:
        await callback.answer("❌ Доступ запрещен")
        return
    
    # Получаем статистику
    today_stats = db.get_statistics()
    fake_settings = db.get_fake_games_settings()
    
    stats_text = (
        f"📊 <b>Статистика проекта {NAME_CASINO}</b>\n\n"
        
        f"👥 <b>Пользователи:</b>\n"
        f"├ Всего: <code>{today_stats.get('total_users', 0)}</code>\n"
        f"├ Активных сегодня: <code>{today_stats.get('active_users', 0)}</code>\n"
        f"├ Новых сегодня: <code>{today_stats.get('new_users', 0)}</code>\n"
        f"├ Активных за неделю: <code>{db.get_active_users_count(7)}</code>\n"
        f"└ Активных за месяц: <code>{db.get_active_users_count(30)}</code>\n\n"
        
        f"💰 <b>Финансы:</b>\n"
        f"├ Общий баланс: <code>{format_balance(0)}</code>\n"
        f"├ Всего депозитов: <code>{format_balance(today_stats.get('total_deposit_amount', 0))}</code>\n"
        f"├ Всего выводов: <code>{format_balance(today_stats.get('total_withdraw_amount', 0))}</code>\n"
        f"├ Прибыль системы: <code>{format_balance(0)}</code>\n"
        f"└ Прибыль от игр: <code>{format_balance(today_stats.get('profit', 0))}</code>\n\n"
        
        f"🎮 <b>Статистика игр:</b>\n"
        f"├ Всего ставок: <code>{today_stats.get('total_bets', 0)}</code>\n"
        f"├ Общая сумма ставок: <code>{format_balance(today_stats.get('total_bet_amount', 0))}</code>\n"
        f"├ Выигрышей: <code>{today_stats.get('winning_bets', 0)}</code>\n"
        f"├ Проигрышей: <code>{today_stats.get('losing_bets', 0)}</code>\n"
        f"├ Выиграно: <code>{format_balance(today_stats.get('total_win_amount', 0))}</code>\n"
        f"└ Проиграно: <code>{format_balance(today_stats.get('total_loss_amount', 0))}</code>\n\n"
        
        f"📅 <b>Статистика за сегодня ({datetime.datetime.now().strftime('%d.%m.%Y')}):</b>\n"
        f"├ Пользователей: <code>{today_stats.get('total_users', 0)}</code>\n"
        f"├ Новых: <code>{today_stats.get('new_users', 0)}</code>\n"
        f"├ Активных: <code>{today_stats.get('active_users', 0)}</code>\n"
        f"├ Ставок: <code>{today_stats.get('total_bets', 0)}</code>\n"
        f"├ Сумма ставок: <code>{format_balance(today_stats.get('total_bet_amount', 0))}</code>\n"
        f"├ Выигрышей: <code>{today_stats.get('winning_bets', 0)}</code>\n"
        f"├ Проигрышей: <code>{today_stats.get('losing_bets', 0)}</code>\n"
        f"├ Прибыль: <code>{format_balance(today_stats.get('profit', 0))}</code>\n"
        f"├ Депозитов: <code>{today_stats.get('total_deposits', 0)}</code>\n"
        f"├ Выводов: <code>{today_stats.get('total_withdrawals', 0)}</code>\n"
        f"└ Промоактиваций: <code>{today_stats.get('promo_activations', 0)}</code>\n\n"
        
        f"🤖 <b>Фейк игры:</b>\n"
        f"├ Статус: {'✅ Включены' if fake_settings.get('enabled') else '❌ Выключены'}\n"
        f"├ Интервал: {fake_settings.get('min_interval', 30)}-{fake_settings.get('max_interval', 120)} сек\n"
        f"├ Ставки: {fake_settings.get('min_bet', 1.0)}$-{fake_settings.get('max_bet', 100.0)}$\n"
        f"├ Шанс победы: {fake_settings.get('win_chance', 40)}%\n"
        f"└ Всего игр: {fake_settings.get('statistics', {}).get('total_games', 0)}\n\n"
        
        f"🔄 <b>Обновлено:</b> {datetime.datetime.now().strftime('%H:%M:%S')}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('🔄 Обновить статистику', callback_data='admin_refresh_stats')],
        [InlineKeyboardButton('📊 Подробная статистика', callback_data='admin_detailed_stats')],
        [InlineKeyboardButton('📈 Графики и аналитика', callback_data='admin_analytics')],
        [InlineKeyboardButton('📋 Экспорт данных', callback_data='admin_export_data')],
        [InlineKeyboardButton('🔙 В админку', callback_data='back_to_admin')]
    ])
    
    await edit_message_with_photo(callback, 'stats', stats_text, keyboard)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'admin_users')
async def callback_admin_users(callback: CallbackQuery):
    """Управление пользователями"""
    user_id = callback.from_user.id
    
    if user_id not in ADMIN:
        await callback.answer("❌ Доступ запрещен")
        return
    
    users_text = (
        f"👤 <b>Управление пользователями</b>\n\n"
        
        f"📊 <b>Статистика:</b>\n"
        f"├ Всего пользователей: <code>{db.get_statistics().get('total_users', 0)}</code>\n"
        f"├ Заблокированных: <code>{len([u for u in db.get_all_users(1000) if u.get('is_blocked')])}</code>\n"
        f"├ VIP пользователей: <code>{len([u for u in db.get_all_users(1000) if u.get('vip_level') != 'STANDARD'])}</code>\n"
        f"└ KYC верифицированных: <code>{len([u for u in db.get_all_users(1000) if u.get('kyc_verified')])}</code>\n\n"
        
        f"⚡ <b>Выберите действие:</b>"
    )
    
    await edit_message_with_photo(callback, 'admin', users_text, get_admin_users_keyboard())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'admin_promos')
async def callback_admin_promos(callback: CallbackQuery):
    """Управление промокодами"""
    user_id = callback.from_user.id
    
    if user_id not in ADMIN:
        await callback.answer("❌ Доступ запрещен")
        return
    
    promos = db.get_promo_codes(is_active=True)
    
    promos_text = (
        f"🎁 <b>Управление промокодами</b>\n\n"
        
        f"📊 <b>Статистика:</b>\n"
        f"├ Всего промокодов: <code>{len(promos)}</code>\n"
        f"├ Активировано раз: <code>{sum(p['used_count'] for p in promos)}</code>\n"
        f"├ Всего выдано: <code>{format_balance(sum(p['amount'] * p['used_count'] for p in promos))}</code>\n"
        f"└ Создано вами: <code>{len([p for p in promos if p.get('created_by') == user_id])}</code>\n\n"
        
        f"⚡ <b>Выберите действие:</b>"
    )
    
    await edit_message_with_photo(callback, 'promo', promos_text, get_admin_promos_keyboard())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'admin_balance')
async def callback_admin_balance(callback: CallbackQuery):
    """Управление балансами"""
    user_id = callback.from_user.id
    
    if user_id not in ADMIN:
        await callback.answer("❌ Доступ запрещен")
        return
    
    users = db.get_all_users(limit=100)
    total_balance = sum(user.get('balance', 0) for user in users)
    
    balance_text = (
        f"💰 <b>Управление балансами</b>\n\n"
        
        f"📊 <b>Статистика:</b>\n"
        f"├ Всего пользователей: <code>{len(users)}</code>\n"
        f"├ Общий баланс: <code>{format_balance(total_balance)}</code>\n"
        f"├ Средний баланс: <code>{format_balance(total_balance / len(users) if users else 0)}</code>\n"
        f"└ Максимальный баланс: <code>{format_balance(max(user.get('balance', 0) for user in users) if users else 0)}</code>\n\n"
        
        f"💡 <b>Функции:</b>\n"
        f"• Пополнить баланс пользователю\n"
        f"• Списать средства с баланса\n"
        f"• Установить конкретный баланс\n"
        f"• Проверить баланс любого пользователя\n\n"
        
        f"⚡ <b>Выберите действие:</b>"
    )
    
    await edit_message_with_photo(callback, 'add_balance', balance_text, get_admin_balance_keyboard())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'admin_create_promo')
async def callback_admin_create_promo(callback: CallbackQuery, state: FSMContext):
    """Создание промокода - начало"""
    user_id = callback.from_user.id
    
    if user_id not in ADMIN:
        await callback.answer("❌ Доступ запрещен")
        return
    
    await edit_message_with_photo(
        callback,
        'promo',
        "🎫 <b>Создание промокода</b>\n\nВведите код промокода (только буквы и цифры):",
        get_cancel_keyboard()
    )
    
    await AdminStates.waiting_for_promo_code_creation.set()
    await callback.answer()

@dp.message_handler(state=AdminStates.waiting_for_promo_code_creation)
async def process_admin_create_promo_code(message: Message, state: FSMContext):
    """Обработка кода промокода"""
    user_id = message.from_user.id
    promo_code = message.text.strip().upper()
    
    if user_id not in ADMIN:
        await state.finish()
        return
    
    # Проверяем формат промокода
    if not promo_code.isalnum():
        await send_photo_message(
            user_id,
            'error',
            "❌ <b>Неверный формат промокода!</b>\n\n"
            "Промокод должен содержать только буквы и цифры.\n"
            "Пример: NOXWAT2024, BONUS50, WELCOME100\n\n"
            "Введите промокод еще раз:",
            get_cancel_keyboard()
        )
        return
    
    # Проверяем существование промокода
    existing_promo = db.get_promo_code(promo_code)
    if existing_promo:
        await send_photo_message(
            user_id,
            'error',
            f"❌ <b>Промокод уже существует!</b>\n\n"
            f"Код <code>{promo_code}</code> уже используется.\n"
            f"Использовано раз: {existing_promo.get('used_count', 0)}\n"
            f"Статус: {'✅ Активен' if existing_promo.get('is_active') else '❌ Неактивен'}\n\n"
            f"Введите другой промокод:",
            get_cancel_keyboard()
        )
        return
    
    await state.update_data(promo_code=promo_code)
    
    await send_photo_message(
        user_id,
        'promo',
        f"✅ <b>Код принят:</b> <code>{promo_code}</code>\n\n"
        f"💎 <b>Введите сумму бонуса:</b>\n\n"
        f"Примеры:\n"
        f"• 10 (10 долларов)\n"
        f"• 5.5 (пять с половиной долларов)\n"
        f"• 100 (сто долларов)\n\n"
        f"💡 <b>Можно вводить дробные числа через точку</b>",
        get_cancel_keyboard()
    )
    
    await AdminStates.waiting_for_promo_amount.set()

@dp.message_handler(state=AdminStates.waiting_for_promo_amount)
async def process_admin_promo_amount(message: Message, state: FSMContext):
    """Обработка суммы промокода"""
    user_id = message.from_user.id
    
    if user_id not in ADMIN:
        await state.finish()
        return
    
    try:
        amount = float(message.text.replace(',', '.').strip())
        
        if amount <= 0:
            await send_photo_message(
                user_id,
                'error',
                "❌ <b>Сумма должна быть больше 0!</b>\n\n"
                "Введите положительную сумму:",
                get_cancel_keyboard()
            )
            return
        
        await state.update_data(promo_amount=amount)
        
        data = await state.get_data()
        promo_code = data.get('promo_code')
        
        await send_photo_message(
            user_id,
            'promo',
            f"✅ <b>Сумма принята:</b> {format_balance(amount)}\n"
            f"🎫 <b>Код:</b> <code>{promo_code}</code>\n\n"
            f"📊 <b>Введите максимальное количество использований:</b>\n\n"
            f"• 0 - без ограничений\n"
            f"• 1 - одноразовый\n"
            f"• 10 - для 10 человек\n"
            f"• 100 - для 100 человек\n\n"
            f"💡 <b>Рекомендуется: 50-100 для публичных промокодов</b>",
            get_cancel_keyboard()
        )
        
        await AdminStates.waiting_for_promo_max_uses.set()
        
    except ValueError:
        await send_photo_message(
            user_id,
            'error',
            "❌ <b>Неверный формат суммы!</b>\n\n"
            "Введите число (например: 10 или 5.5):",
            get_cancel_keyboard()
        )

@dp.message_handler(state=AdminStates.waiting_for_promo_max_uses)
async def process_admin_promo_max_uses(message: Message, state: FSMContext):
    """Обработка максимального количества использований"""
    user_id = message.from_user.id
    
    if user_id not in ADMIN:
        await state.finish()
        return
    
    try:
        max_uses = int(message.text.strip())
        
        if max_uses < 0:
            await send_photo_message(
                user_id,
                'error',
                "❌ <b>Количество не может быть отрицательным!</b>\n\n"
                "Введите число от 0 (без ограничений):",
                get_cancel_keyboard()
            )
            return
        
        await state.update_data(promo_max_uses=max_uses)
        
        data = await state.get_data()
        promo_code = data.get('promo_code')
        amount = data.get('promo_amount')
        
        await send_photo_message(
            user_id,
            'promo',
            f"✅ <b>Лимит использований:</b> {max_uses if max_uses > 0 else 'без ограничений'}\n"
            f"🎫 <b>Код:</b> <code>{promo_code}</code>\n"
            f"💰 <b>Сумма:</b> {format_balance(amount)}\n\n"
            f"📅 <b>Введите дату окончания действия (или '0' для бессрочного):</b>\n\n"
            f"Формат: ДД.ММ.ГГГГ\n"
            f"Примеры:\n"
            f"• 31.12.2024 - до конца 2024 года\n"
            f"• 01.06.2024 - до 1 июня 2024\n"
            f"• 0 - бессрочный промокод\n\n"
            f"💡 <b>Оставьте пустым для бессрочного действия</b>",
            get_cancel_keyboard()
        )
        
        await AdminStates.waiting_for_promo_expires.set()
        
    except ValueError:
        await send_photo_message(
            user_id,
            'error',
            "❌ <b>Неверный формат числа!</b>\n\n"
            "Введите целое число (например: 0, 10, 100):",
            get_cancel_keyboard()
        )

@dp.message_handler(state=AdminStates.waiting_for_promo_expires)
async def process_admin_promo_expires(message: Message, state: FSMContext):
    """Обработка даты окончания промокода"""
    user_id = message.from_user.id
    
    if user_id not in ADMIN:
        await state.finish()
        return
    
    expires_text = message.text.strip()
    expires_at = None
    
    if expires_text and expires_text != '0':
        try:
            # Парсим дату
            expires_at = datetime.datetime.strptime(expires_text, '%d.%m.%Y')
            expires_at = expires_at.replace(hour=23, minute=59, second=59)
            expires_at_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            await send_photo_message(
                user_id,
                'error',
                "❌ <b>Неверный формат даты!</b>\n\n"
                "Используйте формат ДД.ММ.ГГГГ\n"
                "Пример: 31.12.2024\n\n"
                "Введите дату еще раз или '0' для бессрочного:",
                get_cancel_keyboard()
            )
            return
    else:
        expires_at_str = None
    
    await state.update_data(promo_expires=expires_at_str)
    
    data = await state.get_data()
    promo_code = data.get('promo_code')
    amount = data.get('promo_amount')
    max_uses = data.get('promo_max_uses')
    
    await send_photo_message(
        user_id,
        'promo',
        f"✅ <b>Данные промокода:</b>\n\n"
        f"🎫 <b>Код:</b> <code>{promo_code}</code>\n"
        f"💰 <b>Сумма:</b> {format_balance(amount)}\n"
        f"📊 <b>Лимит использований:</b> {max_uses if max_uses > 0 else 'без ограничений'}\n"
        f"📅 <b>Действует до:</b> {expires_at.strftime('%d.%m.%Y') if expires_at else 'бессрочно'}\n\n"
        f"📝 <b>Введите описание промокода (необязательно):</b>\n\n"
        f"Примеры:\n"
        f"• Новогодний промокод 2024\n"
        f"• Бонус за регистрацию\n"
        f"• Акция для новых пользователей\n"
        f"• Подарок от администрации\n\n"
        f"💡 <b>Можно оставить пустым</b>",
        get_cancel_keyboard()
    )
    
    await AdminStates.waiting_for_promo_description.set()

@dp.message_handler(state=AdminStates.waiting_for_promo_description)
async def process_admin_promo_description(message: Message, state: FSMContext):
    """Обработка описания промокода и создание"""
    user_id = message.from_user.id
    
    if user_id not in ADMIN:
        await state.finish()
        return
    
    description = message.text.strip()
    if not description:
        description = f"Промокод создан администратором"
    
    data = await state.get_data()
    promo_code = data.get('promo_code')
    amount = data.get('promo_amount')
    max_uses = data.get('promo_max_uses')
    expires_at = data.get('promo_expires')
    
    # Создаем промокод
    success = db.create_promo_code(
        code=promo_code,
        amount=amount,
        max_uses=max_uses,
        expires_at=expires_at,
        created_by=user_id,
        description=description
    )
    
    if success:
        result_text = (
            f"🎉 <b>Промокод успешно создан!</b>\n\n"
            f"🎫 <b>Код:</b> <code>{promo_code}</code>\n"
            f"💰 <b>Сумма:</b> {format_balance(amount)}\n"
            f"📊 <b>Лимит использований:</b> {max_uses if max_uses > 0 else 'без ограничений'}\n"
            f"📅 <b>Действует до:</b> {datetime.datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y') if expires_at else 'бессрочно'}\n"
            f"📝 <b>Описание:</b> {description}\n\n"
            f"👑 <b>Создал:</b> {user_id}\n"
            f"⏰ <b>Время:</b> {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
            f"💡 <b>Промокод готов к использованию!</b>"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton('🎫 Создать еще промокод', callback_data='admin_create_promo')],
            [InlineKeyboardButton('📋 Список промокодов', callback_data='admin_list_promos')],
            [InlineKeyboardButton('🔙 В админку', callback_data='back_to_admin')]
        ])
        
        await send_photo_message(user_id, 'success', result_text, keyboard)
        
        # Логируем создание промокода
        logger.info(f"✅ Админ {user_id} создал промокод {promo_code} на {amount}$")
        
    else:
        await send_photo_message(
            user_id,
            'error',
            "❌ <b>Ошибка создания промокода!</b>\n\n"
            "Попробуйте еще раз или обратитесь к разработчику.",
            get_back_admin_keyboard()
        )
    
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'admin_add_balance')
async def callback_admin_add_balance(callback: CallbackQuery, state: FSMContext):
    """Пополнение баланса пользователю"""
    user_id = callback.from_user.id
    
    if user_id not in ADMIN:
        await callback.answer("❌ Доступ запрещен")
        return
    
    await edit_message_with_photo(
        callback,
        'add_balance',
        "💰 <b>Пополнение баланса пользователю</b>\n\n"
        "Введите ID пользователя или @username:\n\n"
        "Примеры:\n"
        "• 123456789 (ID пользователя)\n"
        "• @username (если есть)\n"
        "• Имя Фамилия (если нет username)\n\n"
        "💡 <b>Можно найти пользователя через поиск</b>",
        get_cancel_keyboard()
    )
    
    await AdminStates.waiting_for_user_id_for_balance.set()
    await callback.answer()

@dp.message_handler(state=AdminStates.waiting_for_user_id_for_balance)
async def process_admin_user_id_for_balance(message: Message, state: FSMContext):
    """Обработка ID пользователя для пополнения"""
    user_id = message.from_user.id
    
    if user_id not in ADMIN:
        await state.finish()
        return
    
    query = message.text.strip()
    users = db.search_users(query, limit=5)
    
    if not users:
        await send_photo_message(
            user_id,
            'error',
            f"❌ <b>Пользователь не найден!</b>\n\n"
            f"Запрос: <code>{query}</code>\n\n"
            f"Попробуйте:\n"
            "• Ввести точный ID\n"
            "• Использовать @username\n"
            "• Искать по имени\n\n"
            "Введите данные пользователя еще раз:",
            get_cancel_keyboard()
        )
        return
    
    if len(users) > 1:
        # Показываем список пользователей
        users_text = "👥 <b>Найдены пользователи:</b>\n\n"
        for i, user in enumerate(users, 1):
            users_text += (
                f"{i}. {get_user_display_name(user)} "
                f"(ID: <code>{user['user_id']}</code>) "
                f"- {format_balance(user.get('balance', 0))}\n"
            )
        
        users_text += f"\n📝 <b>Введите ID нужного пользователя:</b>"
        
        await send_photo_message(
            user_id,
            'add_balance',
            users_text,
            get_cancel_keyboard()
        )
        return
    
    # Найден один пользователь
    target_user = users[0]
    await state.update_data(target_user_id=target_user['user_id'])
    
    await send_photo_message(
        user_id,
        'add_balance',
        f"✅ <b>Пользователь найден:</b>\n\n"
        f"👤 <b>Имя:</b> {get_user_display_name(target_user)}\n"
        f"🆔 <b>ID:</b> <code>{target_user['user_id']}</code>\n"
        f"💰 <b>Текущий баланс:</b> {format_balance(target_user.get('balance', 0))}\n\n"
        f"💎 <b>Введите сумму для пополнения:</b>\n\n"
        f"Примеры:\n"
        f"• 10 (десять долларов)\n"
        f"• 5.5 (пять с половиной)\n"
        f"• 100 (сто долларов)\n\n"
        f"💡 <b>Можно вводить дробные числа через точку</b>",
        get_cancel_keyboard()
    )
    
    await AdminStates.waiting_for_balance_amount.set()

@dp.message_handler(state=AdminStates.waiting_for_balance_amount)
async def process_admin_balance_amount(message: Message, state: FSMContext):
    """Обработка суммы для пополнения"""
    admin_id = message.from_user.id
    
    if admin_id not in ADMIN:
        await state.finish()
        return
    
    try:
        amount = float(message.text.replace(',', '.').strip())
        
        if amount <= 0:
            await send_photo_message(
                admin_id,
                'error',
                "❌ <b>Сумма должна быть больше 0!</b>\n\n"
                "Введите положительную сумму:",
                get_cancel_keyboard()
            )
            return
        
        await state.update_data(balance_amount=amount)
        
        data = await state.get_data()
        target_user_id = data.get('target_user_id')
        
        target_user = db.get_user(target_user_id)
        current_balance = target_user.get('balance', 0)
        new_balance = current_balance + amount
        
        await send_photo_message(
            admin_id,
            'add_balance',
            f"✅ <b>Сумма принята:</b> {format_balance(amount)}\n\n"
            f"👤 <b>Пользователь:</b> {get_user_display_name(target_user)}\n"
            f"🆔 <b>ID:</b> <code>{target_user_id}</code>\n"
            f"💰 <b>Текущий баланс:</b> {format_balance(current_balance)}\n"
            f"📈 <b>Будет после пополнения:</b> {format_balance(new_balance)}\n\n"
            f"📝 <b>Введите причину пополнения:</b>\n\n"
            f"Примеры:\n"
            f"• Бонус за активность\n"
            f"• Исправление ошибки\n"
            f"• Подарок от администрации\n"
            f"• Выигрыш в конкурсе\n\n"
            f"💡 <b>Эта информация будет видна пользователю</b>",
            get_cancel_keyboard()
        )
        
        await AdminStates.waiting_for_balance_reason.set()
        
    except ValueError:
        await send_photo_message(
            admin_id,
            'error',
            "❌ <b>Неверный формат суммы!</b>\n\n"
            "Введите число (например: 10 или 5.5):",
            get_cancel_keyboard()
        )

@dp.message_handler(state=AdminStates.waiting_for_balance_reason)
async def process_admin_balance_reason(message: Message, state: FSMContext):
    """Обработка причины пополнения и выполнение"""
    admin_id = message.from_user.id
    
    if admin_id not in ADMIN:
        await state.finish()
        return
    
    reason = message.text.strip()
    if not reason:
        reason = "Пополнение от администратора"
    
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    amount = data.get('balance_amount')
    
    # Получаем информацию о пользователе
    target_user = db.get_user(target_user_id)
    current_balance = target_user.get('balance', 0)
    
    # Пополняем баланс
    success = await db.admin_add_balance(target_user_id, amount, admin_id, reason)
    
    if success:
        result_text = (
            f"🎉 <b>Баланс успешно пополнен!</b>\n\n"
            f"👤 <b>Пользователь:</b> {get_user_display_name(target_user)}\n"
            f"🆔 <b>ID:</b> <code>{target_user_id}</code>\n"
            f"💰 <b>Сумма пополнения:</b> {format_balance(amount)}\n"
            f"📈 <b>Было:</b> {format_balance(current_balance)}\n"
            f"💳 <b>Стало:</b> {format_balance(current_balance + amount)}\n"
            f"📝 <b>Причина:</b> {reason}\n\n"
            f"👑 <b>Администратор:</b> {admin_id}\n"
            f"⏰ <b>Время:</b> {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
            f"✅ <b>Операция успешно выполнена!</b>"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton('💰 Пополнить еще', callback_data='admin_add_balance')],
            [InlineKeyboardButton('📉 Списать баланс', callback_data='admin_deduct_balance')],
            [InlineKeyboardButton('🔙 В админку', callback_data='back_to_admin')]
        ])
        
        await send_photo_message(admin_id, 'success', result_text, keyboard)
        
        # Логируем операцию
        logger.info(f"✅ Админ {admin_id} пополнил баланс {target_user_id} на {amount}$")
        
    else:
        await send_photo_message(
            admin_id,
            'error',
            "❌ <b>Ошибка пополнения баланса!</b>\n\n"
            "Попробуйте еще раз или обратитесь к разработчику.",
            get_back_admin_keyboard()
        )
    
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'admin_deduct_balance')
async def callback_admin_deduct_balance(callback: CallbackQuery, state: FSMContext):
    """Списание баланса у пользователя"""
    user_id = callback.from_user.id
    
    if user_id not in ADMIN:
        await callback.answer("❌ Доступ запрещен")
        return
    
    await edit_message_with_photo(
        callback,
        'add_balance',
        "📉 <b>Списание баланса у пользователя</b>\n\n"
        "⚠️ <b>Внимание!</b> Эта операция необратима.\n\n"
        "Введите ID пользователя или @username:\n\n"
        "Примеры:\n"
        "• 123456789 (ID пользователя)\n"
        "• @username (если есть)\n"
        "• Имя Фамилия (если нет username)\n\n"
        "💡 <b>Можно найти пользователя через поиск</b>",
        get_cancel_keyboard()
    )
    
    await AdminStates.waiting_for_user_id_for_balance.set()
    await state.update_data(action_type='deduct')
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'admin_set_balance')
async def callback_admin_set_balance(callback: CallbackQuery, state: FSMContext):
    """Установка баланса пользователю"""
    user_id = callback.from_user.id
    
    if user_id not in ADMIN:
        await callback.answer("❌ Доступ запрещен")
        return
    
    await edit_message_with_photo(
        callback,
        'add_balance',
        "⚡ <b>Установка баланса пользователю</b>\n\n"
        "⚠️ <b>Внимание!</b> Эта операция установит точный баланс.\n\n"
        "Введите ID пользователя или @username:\n\n"
        "Примеры:\n"
        "• 123456789 (ID пользователя)\n"
        "• @username (если есть)\n"
        "• Имя Фамилия (если нет username)\n\n"
        "💡 <b>Можно найти пользователя через поиск</b>",
        get_cancel_keyboard()
    )
    
    await AdminStates.waiting_for_user_id_for_balance.set()
    await state.update_data(action_type='set')
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'admin_check_balance')
async def callback_admin_check_balance(callback: CallbackQuery, state: FSMContext):
    """Проверка баланса пользователя"""
    user_id = callback.from_user.id
    
    if user_id not in ADMIN:
        await callback.answer("❌ Доступ запрещен")
        return
    
    await edit_message_with_photo(
        callback,
        'balance',
        "🔍 <b>Проверка баланса пользователя</b>\n\n"
        "Введите ID пользователя или @username:\n\n"
        "Примеры:\n"
        "• 123456789 (ID пользователя)\n"
        "• @username (если есть)\n"
        "• Имя Фамилия (если нет username)\n\n"
        "💡 <b>Можно найти пользователя через поиск</b>",
        get_cancel_keyboard()
    )
    
    await AdminStates.waiting_for_user_id_for_balance.set()
    await state.update_data(action_type='check')
    await callback.answer()

# Обработка остальных админ функций будет аналогично...

# ==================== ПЛАНИРОВЩИК ЗАДАЧ ====================

async def scheduled_statistics_update():
    """Ежедневное обновление статистики"""
    try:
        logger.info("🔄 Обновление ежедневной статистики")
        
        # Создаем запись на сегодня если ее нет
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        db.get_statistics(today)
        
        # Очищаем старые данные
        db.cleanup_old_data(30)
        
        logger.info("✅ Статистика обновлена")
    except Exception as e:
        logger.error(f"❌ Ошибка обновления статистики: {e}")

async def scheduled_fake_games():
    """Запуск фейк игр по расписанию"""
    try:
        settings = db.get_fake_games_settings()
        
        if not settings.get('enabled'):
            return
        
        # Проверяем время с последнего запуска
        last_run = settings.get('last_run')
        if last_run:
            last_run_dt = datetime.datetime.strptime(last_run, '%Y-%m-%d %H:%M:%S')
            min_interval = settings.get('min_interval', 30)
            if (datetime.datetime.now() - last_run_dt).seconds < min_interval:
                return
        
        # Выбираем случайный интервал
        min_interval = settings.get('min_interval', 30)
        max_interval = settings.get('max_interval', 120)
        interval = random.randint(min_interval, max_interval)
        
        # Обновляем время последнего запуска
        db.update_fake_games_settings(last_run=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Ждем перед следующей фейк игрой
        await asyncio.sleep(interval)
        
        # Запускаем фейк игру
        await run_fake_game()
        
    except Exception as e:
        logger.error(f"❌ Ошибка в планировщике фейк игр: {e}")

async def run_fake_game():
    """Запуск одной фейк игры"""
    try:
        settings = db.get_fake_games_settings()
        
        if not settings.get('enabled'):
            return
        
        # Выбираем случайные параметры
        games = ['more_less', 'number', 'even_odd', 'roulette', 'football', 'basketball', 'knb']
        game_type = random.choice(games)
        
        # Выбираем исход в зависимости от игры
        if game_type == 'more_less':
            outcome = random.choice(['more', 'less'])
        elif game_type == 'number':
            outcome = str(random.randint(1, 6))
        elif game_type == 'even_odd':
            outcome = random.choice(['even', 'odd'])
        elif game_type == 'roulette':
            outcome = random.choice(['red', 'black', 'green'])
        elif game_type in ['football', 'basketball']:
            outcome = random.choice(['goal', 'miss'])
        elif game_type == 'knb':
            outcome = random.choice(['rock', 'scissors', 'paper'])
        else:
            outcome = 'default'
        
        # Выбираем сумму ставки
        min_bet = settings.get('min_bet', 1.0)
        max_bet = settings.get('max_bet', 100.0)
        bet_amount = round(random.uniform(min_bet, max_bet), 2)
        
        # Выбираем имя игрока
        fake_name = random.choice(FAKE_NICKNAME)
        
        # Определяем результат (с учетом настройки win_chance)
        win_chance = settings.get('win_chance', 40)
        win = random.randint(1, 100) <= win_chance
        
        # Получаем коэффициент
        multiplier = get_multiplier(game_type, outcome) if win else 1.0
        win_amount = calculate_win_amount(bet_amount, multiplier) if win else 0
        
        # Создаем сообщение в канале
        game_name = get_game_name(game_type)
        outcome_name = get_outcome_name(outcome, game_type)
        
        if win:
            result_text = (
                f"🎉 <b>ПОБЕДА! (Фейк игра)</b>\n\n"
                f"👤 <b>Игрок:</b> {fake_name}\n"
                f"🎮 <b>Игра:</b> {game_name}\n"
                f"🎯 <b>Исход:</b> {outcome_name}\n"
                f"💰 <b>Ставка:</b> {format_balance(bet_amount)}\n"
                f"📈 <b>Коэффициент:</b> {multiplier}x\n"
                f"💸 <b>Выигрыш:</b> {format_balance(win_amount)}\n\n"
                f"🎊 <b>Поздравляем с победой!</b> 🎊"
            )
        else:
            result_text = (
                f"😔 <b>ПРОИГРЫШ (Фейк игра)</b>\n\n"
                f"👤 <b>Игрок:</b> {fake_name}\n"
                f"🎮 <b>Игра:</b> {game_name}\n"
                f"🎯 <b>Исход:</b> {outcome_name}\n"
                f"💰 <b>Ставка:</b> {format_balance(bet_amount)}\n"
                f"💸 <b>Проиграно:</b> {format_balance(bet_amount)}\n\n"
                f"💪 <b>Не расстраивайтесь, удача будет на вашей стороне!</b>"
            )
        
        # Отправляем в канал
        await bot.send_message(
            chat_id=channel_id,
            text=result_text,
            parse_mode=ParseMode.HTML
        )
        
        # Записываем в статистику
        db.add_fake_game_stat(bet_amount, win_amount, 'win' if win else 'lose')
        
        logger.info(f"✅ Фейк игра запущена: {fake_name} - {game_name} - {'Выигрыш' if win else 'Проигрыш'}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска фейк игры: {e}")

# ==================== ЗАПУСК БОТА ====================

async def on_startup(dp: Dispatcher):
    """Действия при запуске бота"""
    try:
        # Проверяем токен бота
        me = await bot.get_me()
        logger.info(f"🤖 Бот запущен: @{me.username} (ID: {me.id})")
        
        # Устанавливаем команды
        await bot.set_my_commands([
            types.BotCommand("start", "Запустить бота"),
            types.BotCommand("balance", "Показать баланс"),
            types.BotCommand("stats", "Моя статистика"),
            types.BotCommand("promo", "Активировать промокод"),
            types.BotCommand("help", "Помощь"),
            types.BotCommand("support", "Связь с поддержкой"),
            types.BotCommand("admin", "Админ панель")
        ])
        
        # Запускаем планировщик если он есть
        if scheduler:
            # Ежедневное обновление статистики в 00:00
            scheduler.add_job(
                scheduled_statistics_update,
                CronTrigger(hour=0, minute=0),
                id='daily_stats'
            )
            
            # Фейк игры каждые 30-120 секунд
            scheduler.add_job(
                scheduled_fake_games,
                IntervalTrigger(seconds=30),
                id='fake_games'
            )
            
            logger.info("✅ Планировщик задач запущен")
        
        # Отправляем сообщение о запуске
        startup_text = (
            f"🚀 <b>Бот {NAME_CASINO} успешно запущен!</b>\n\n"
            f"🤖 <b>Бот:</b> @{me.username}\n"
            f"👑 <b>Админы:</b> {len(ADMIN)}\n"
            f"👥 <b>Пользователей в БД:</b> {db.get_statistics().get('total_users', 0)}\n"
            f"💰 <b>Общий баланс:</b> {format_balance(0)}\n"
            f"🎮 <b>Фейк игры:</b> {'✅ Включены' if db.get_fake_games_settings().get('enabled') else '❌ Выключены'}\n\n"
            f"🔄 <b>Время запуска:</b> {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
        
        # Отправляем в лог канал если указан
        if URL_LOG_CHANNAL:
            try:
                await bot.send_message(URL_LOG_CHANNAL, startup_text, parse_mode=ParseMode.HTML)
            except:
                pass
        
        # Красивый вывод в консоль
        print(f"\n{'='*60}")
        print(f"🎰 {NAME_CASINO}")
        print(f"{'='*60}")
        print(f"🤖 Бот: @{me.username}")
        print(f"👑 Админы: {len(ADMIN)}")
        print(f"👥 Пользователей: {db.get_statistics().get('total_users', 0)}")
        print(f"💰 Минимальная ставка: {MIN_STAVKA}$")
        print(f"🎮 Фейк игры: {'ВКЛ' if db.get_fake_games_settings().get('enabled') else 'ВЫКЛ'}")
        print(f"🔄 Версия: AIOGRAM 2.25.1")
        print(f"⏰ Время: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        print(f"{'='*60}")
        print("✅ Бот успешно запущен! Ожидаю сообщений...")
        print(f"{'='*60}\n")
        
        logger.info("✅ Бот успешно запущен и готов к работе")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
        raise

async def on_shutdown(dp: Dispatcher):
    """Действия при выключении бота"""
    try:
        logger.info("🛑 Завершение работы бота...")
        
        # Сохраняем данные и закрываем соединения
        if scheduler:
            scheduler.shutdown()
            logger.info("✅ Планировщик остановлен")
        
        db.connection.commit()
        db.close()
        logger.info("✅ База данных сохранена и закрыта")
        
        # Отправляем сообщение о выключении
        shutdown_text = (
            f"🛑 <b>Бот {NAME_CASINO} завершает работу</b>\n\n"
            f"⏰ <b>Время:</b> {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"📊 <b>Статистика:</b>\n"
            f"├ Пользователей: {db.get_statistics().get('total_users', 0)}\n"
            f"├ Онлайн: {db.get_active_users_count(1)}\n"
            f"└ Сессия: {datetime.datetime.now().strftime('%H:%M:%S')}\n\n"
            f"🔧 <b>Технические работы</b>"
        )
        
        if URL_LOG_CHANNAL:
            try:
                await bot.send_message(URL_LOG_CHANNAL, shutdown_text, parse_mode=ParseMode.HTML)
            except:
                pass
        
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.close()
        
        print(f"\n{'='*60}")
        print(f"🛑 {NAME_CASINO} завершает работу")
        print(f"⏰ Время: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        print(f"👥 Пользователей: {db.get_statistics().get('total_users', 0)}")
        print(f"{'='*60}")
        
        logger.info("✅ Бот успешно завершил работу")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при завершении работы: {e}")

# ==================== ЗАПУСК ОСНОВНОГО ЦИКЛА ====================

def main():
    """Основная функция запуска бота"""
    try:
        logger.info(f"🚀 Запуск {NAME_CASINO}...")
        
        # Запускаем бота
        executor.start_polling(
            dp,
            skip_updates=True,  # Пропускаем обновления, пока бот был офлайн
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            timeout=60,
            relax=0.1,
            fast=True
        )
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске бота: {e}")
        sys.exit(1)

# ==================== ТОЧКА ВХОДА ====================

if __name__ == '__main__':
    # Проверяем наличие обязательных переменных
    if not BOT_TOKEN:
        logger.error("❌ Отсутствует BOT_TOKEN в конфиге!")
        sys.exit(1)
    
    if not ADMIN:
        logger.error("❌ Отсутствует ADMIN в конфиге!")
        sys.exit(1)
    
    if not channel_id:
        logger.error("❌ Отсутствует channel_id в конфиге!")
        sys.exit(1)
    
    # Запускаем основную функцию
    try:
        main()
    except KeyboardInterrupt:
        logger.info("⚠️  Бот остановлен пользователем")
        print(f"\n{'='*60}")
        print("⚠️  Бот остановлен пользователем (Ctrl+C)")
        print(f"{'='*60}")
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")
        print(f"\n{'='*60}")
        print(f"❌ Критическая ошибка: {e}")
        print(f"{'='*60}")
        sys.exit(1)