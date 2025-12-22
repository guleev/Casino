import sqlite3
import datetime
import os
import logging
from typing import Optional, Dict, List, Any, Union, Tuple

logger = logging.getLogger(__name__)

class DataBase:
    def __init__(self, path: str = 'database.db'):
        """Инициализация базы данных"""
        self.path = path
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.init_all_tables()
    
    def init_all_tables(self):
        """Инициализация всех таблиц"""
        cursor = self.connection.cursor()
        
        # Таблица пользователей
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            referi_id INTEGER,
            data_reg TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Таблица промокодов (ИСПРАВЛЕНА)
        cursor.execute('''CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            amount REAL NOT NULL,
            max_uses INTEGER DEFAULT 0,
            used_count INTEGER DEFAULT 0,
            expires_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            created_by INTEGER
        )''')
        
        # Таблица активаций промокодов
        cursor.execute('''CREATE TABLE IF NOT EXISTS promo_activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            promo_code TEXT NOT NULL,
            activated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            amount REAL NOT NULL,
            FOREIGN KEY (promo_code) REFERENCES promo_codes(code),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )''')
        
        # Таблица статистики игр
        cursor.execute('''CREATE TABLE IF NOT EXISTS count_pay (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Таблица реферальных доходов
        cursor.execute('''CREATE TABLE IF NOT EXISTS referal_money (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Таблица транзакций
        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            status TEXT NOT NULL,
            invoice_id TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Таблица статистики за день
        cursor.execute('''CREATE TABLE IF NOT EXISTS stats_day (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT DEFAULT CURRENT_DATE,
            games INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            loses INTEGER DEFAULT 0,
            payout REAL DEFAULT 0.0,
            bet_total REAL DEFAULT 0.0,
            UNIQUE(date)
        )''')
        
        # Таблица фейк настроек
        cursor.execute('''CREATE TABLE IF NOT EXISTS fake_settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            is_active INTEGER DEFAULT 1,
            UNIQUE(id)
        )''')
        
        # Таблица коэффициентов
        cursor.execute('''CREATE TABLE IF NOT EXISTS kef_values (
            key TEXT PRIMARY KEY,
            value REAL
        )''')
        
        # Таблица ссылок
        cursor.execute('''CREATE TABLE IF NOT EXISTS urls (
            id TEXT PRIMARY KEY,
            url TEXT
        )''')
        
        self.connection.commit()
        
        # Инициализируем коэффициенты если их нет
        self.init_kef_values()
        
        # Инициализируем фейк настройки если их нет
        self.init_fake_settings()
        
        # Инициализируем ссылки если их нет
        self.init_urls()
    
    def init_kef_values(self):
        """Инициализация коэффициентов"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM kef_values")
        if cursor.fetchone()[0] == 0:
            from config import DEFAULT_KEF
            default_kefs = DEFAULT_KEF
            for key, value in default_kefs.items():
                cursor.execute("INSERT OR REPLACE INTO kef_values (key, value) VALUES (?, ?)", (key, value))
            self.connection.commit()
            logger.info("✅ Коэффициенты инициализированы")
    
    def init_fake_settings(self):
        """Инициализация фейк настроек"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM fake_settings")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO fake_settings (is_active) VALUES (1)")
            self.connection.commit()
            logger.info("✅ Фейк настройки инициализированы")
    
    def init_urls(self):
        """Инициализация ссылок"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM urls")
        if cursor.fetchone()[0] == 0:
            urls = [
                ('news', 'https://t.me/noxwat'),
                ('info_stavka', 'https://teletype.in/@oeaow-144350/tsIRVcpdqg'),
                ('transfer', 'https://t.me/NoxwatPayments'),
                ('channals', 'https://t.me/noxwatgames'),
                ('faq_vyplata', 'https://teletype.in/@oeaow-144350/HNYMwzmANm'),
                ('faq_games', 'https://teletype.in/@oeaow-144350/NJa3KsktZ-')
            ]
            for id, url in urls:
                cursor.execute("INSERT OR REPLACE INTO urls (id, url) VALUES (?, ?)", (id, url))
            self.connection.commit()
            logger.info("✅ Ссылки инициализированы")
    
    # ==================== ФУНКЦИИ ПРОМОКОДОВ (ИСПРАВЛЕНЫ) ====================
    
    def create_promo_code(self, code, amount, max_uses=0, expires_at=None, created_by=None):
        """Создание нового промокода"""
        try:
            cursor = self.connection.cursor()
            
            # Проверяем, существует ли уже такой код
            cursor.execute("SELECT code FROM promo_codes WHERE code = ?", (code,))
            if cursor.fetchone():
                logger.warning(f"Промокод {code} уже существует")
                return False
            
            # Преобразуем дату в строку если она есть
            expires_at_str = None
            if expires_at:
                expires_at_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')
            
            # Вставляем новый промокод
            cursor.execute('''INSERT INTO promo_codes 
                             (code, amount, max_uses, expires_at, created_by) 
                             VALUES (?, ?, ?, ?, ?)''',
                          (code, amount, max_uses, expires_at_str, created_by))
            
            self.connection.commit()
            logger.info(f"✅ Создан промокод: {code}, сумма: {amount}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при создании промокода: {e}")
            return False
    
    def activate_promo_code(self, user_id, code):
        """Активация промокода пользователем - ИСПРАВЛЕНО"""
        try:
            cursor = self.connection.cursor()
            
            # Проверяем существование промокода
            cursor.execute('''SELECT amount, max_uses, used_count, expires_at, is_active 
                             FROM promo_codes WHERE code = ?''', (code,))
            promo = cursor.fetchone()
            
            if not promo:
                logger.warning(f"Промокод {code} не найден")
                return {'success': False, 'message': 'Промокод не найден'}
            
            amount, max_uses, used_count, expires_at, is_active = promo
            
            # Проверяем активность
            if is_active != 1:
                logger.warning(f"Промокод {code} неактивен")
                return {'success': False, 'message': 'Промокод неактивен'}
            
            # Проверяем срок действия
            if expires_at:
                try:
                    expires_dt = datetime.datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
                    if expires_dt < datetime.datetime.now():
                        logger.warning(f"Промокод {code} истек")
                        return {'success': False, 'message': 'Срок действия промокода истек'}
                except ValueError:
                    # Если формат даты некорректен, пропускаем проверку
                    pass
            
            # Проверяем лимит использований
            if max_uses > 0 and used_count >= max_uses:
                logger.warning(f"Промокод {code} исчерпал лимит")
                return {'success': False, 'message': 'Лимит использований промокода исчерпан'}
            
            # Проверяем, активировал ли пользователь уже этот промокод
            cursor.execute('''SELECT id FROM promo_activations 
                             WHERE user_id = ? AND promo_code = ?''', (user_id, code))
            if cursor.fetchone():
                logger.warning(f"Пользователь {user_id} уже активировал промокод {code}")
                return {'success': False, 'message': 'Вы уже активировали этот промокод'}
            
            # Активируем промокод
            cursor.execute('''UPDATE promo_codes SET used_count = used_count + 1 
                             WHERE code = ?''', (code,))
            
            # Записываем активацию
            cursor.execute('''INSERT INTO promo_activations (user_id, promo_code, amount) 
                             VALUES (?, ?, ?)''', (user_id, code, amount))
            
            # Обновляем баланс пользователя
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            if user:
                current_balance = user[0]
                new_balance = current_balance + amount
                cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (new_balance, user_id))
            
            self.connection.commit()
            logger.info(f"✅ Промокод {code} активирован пользователем {user_id}, сумма: {amount}")
            return {'success': True, 'amount': amount, 'new_balance': new_balance if user else amount}
            
        except Exception as e:
            logger.error(f"❌ Ошибка при активации промокода: {e}")
            return {'success': False, 'message': 'Ошибка при активации промокода'}
    
    def get_all_promo_codes(self):
        """Получить все промокоды"""
        cursor = self.connection.cursor()
        cursor.execute('''SELECT code, amount, used_count, max_uses, expires_at, 
                         created_at, is_active, created_by 
                         FROM promo_codes ORDER BY created_at DESC''')
        return cursor.fetchall()
    
    def get_promo_stats(self):
        """Получить статистику по промокодам"""
        cursor = self.connection.cursor()
        
        # Общее количество промокодов
        cursor.execute("SELECT COUNT(*) FROM promo_codes")
        total_codes = cursor.fetchone()[0]
        
        # Активные промокоды
        cursor.execute("SELECT COUNT(*) FROM promo_codes WHERE is_active = 1")
        active_codes = cursor.fetchone()[0]
        
        # Общее количество использований
        cursor.execute("SELECT SUM(used_count) FROM promo_codes")
        total_used = cursor.fetchone()[0] or 0
        
        # Общая сумма выданных бонусов
        cursor.execute('''SELECT SUM(pa.amount) 
                         FROM promo_activations pa 
                         JOIN promo_codes pc ON pa.promo_code = pc.code''')
        total_amount = cursor.fetchone()[0] or 0.0
        
        return total_codes, active_codes, total_used, total_amount
    
    def has_user_activated_promo(self, user_id, code):
        """Проверить, активировал ли пользователь промокод"""
        cursor = self.connection.cursor()
        cursor.execute('''SELECT id FROM promo_activations 
                         WHERE user_id = ? AND promo_code = ?''', (user_id, code))
        return cursor.fetchone() is not None
    
    # ==================== ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ ФЕЙК ИГРАМИ ====================
    
    def toggle_fake_games(self, status: bool):
        """Включить/выключить фейк игры"""
        cursor = self.connection.cursor()
        cursor.execute("UPDATE fake_settings SET is_active = ? WHERE id = 1", (1 if status else 0,))
        self.connection.commit()
        logger.info(f"✅ Фейк игры {'включены' if status else 'выключены'}")
    
    def get_fake_games_status(self):
        """Получить статус фейк игр"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT is_active FROM fake_settings WHERE id = 1")
        result = cursor.fetchone()
        return result[0] if result else 0
    
    # ==================== ФУНКЦИИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ====================
    
    def user_exists(self, user_id: int) -> bool:
        """Проверить существование пользователя"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None
    
    def add_user(self, user_id: int, referer_id: Optional[int] = None):
        """Добавить пользователя"""
        try:
            cursor = self.connection.cursor()
            
            if self.user_exists(user_id):
                # Обновляем время последней активности
                cursor.execute("UPDATE users SET data_reg = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
            else:
                # Добавляем нового пользователя
                cursor.execute('''INSERT INTO users (user_id, referi_id, data_reg) 
                                VALUES (?, ?, CURRENT_TIMESTAMP)''',
                             (user_id, referer_id))
                
                # Увеличиваем счетчик рефералов у реферера
                if referer_id:
                    # TODO: Добавить логику рефералов если нужно
                    pass
            
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка добавления пользователя: {e}")
            return False
    
    def get_user_balance(self, user_id: int) -> float:
        """Получить баланс пользователя"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0.0
    
    def update_balance(self, user_id: int, amount: float, operation: str = 'add') -> bool:
        """Обновить баланс пользователя"""
        try:
            cursor = self.connection.cursor()
            
            if operation == 'add':
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            elif operation == 'subtract':
                cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
            elif operation == 'set':
                cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (amount, user_id))
            
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка обновления баланса: {e}")
            return False
    
    def get_all_users(self):
        """Получить всех пользователей"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users ORDER BY data_reg DESC")
        return cursor.fetchall()
    
    def get_total_users(self) -> int:
        """Получить общее количество пользователей"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]
    
    def get_total_balance(self) -> float:
        """Получить общий баланс всех пользователей"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT SUM(balance) FROM users")
        result = cursor.fetchone()
        return result[0] if result[0] is not None else 0.0
    
    # ==================== ФУНКЦИИ ДЛЯ КОЭФФИЦИЕНТОВ ====================
    
    def get_cur_KEF(self, kef_name: str) -> float:
        """Получить текущий коэффициент"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT value FROM kef_values WHERE key = ?", (kef_name,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            # Если коэффициент не найден, возвращаем значение по умолчанию
            from config import DEFAULT_KEF
            return DEFAULT_KEF.get(kef_name, 1.0)
    
    def update_KEF(self, kef_name: str, value: float) -> bool:
        """Обновить коэффициент"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("INSERT OR REPLACE INTO kef_values (key, value) VALUES (?, ?)", (kef_name, value))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка обновления коэффициента: {e}")
            return False
    
    def get_all_kef(self):
        """Получить все коэффициенты"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM kef_values")
        results = cursor.fetchall()
        return {row[0]: row[1] for row in results}
    
    # ==================== ФУНКЦИИ ДЛЯ СТАТИСТИКИ ====================
    
    def add_count_pay(self, user_id: int, text: str, amount: float):
        """Добавить статистику платежа"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''INSERT INTO count_pay (user_id, text, amount) 
                            VALUES (?, ?, ?)''', (user_id, text, amount))
            self.connection.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка добавления статистики платежа: {e}")
    
    def add_count_pay_stats_day(self, text: str, amount: float):
        """Добавить дневную статистику"""
        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            cursor = self.connection.cursor()
            
            # Проверяем, есть ли запись на сегодня
            cursor.execute("SELECT id FROM stats_day WHERE date = ?", (today,))
            result = cursor.fetchone()
            
            if result:
                # Обновляем существующую запись
                if text == 'win':
                    cursor.execute('''UPDATE stats_day SET 
                                    games = games + 1,
                                    wins = wins + 1,
                                    bet_total = bet_total + ?,
                                    payout = payout + ?
                                    WHERE date = ?''', (amount, amount, today))
                elif text == 'lose':
                    cursor.execute('''UPDATE stats_day SET 
                                    games = games + 1,
                                    loses = loses + 1,
                                    bet_total = bet_total + ?
                                    WHERE date = ?''', (amount, today))
            else:
                # Создаем новую запись
                if text == 'win':
                    cursor.execute('''INSERT INTO stats_day (date, games, wins, bet_total, payout) 
                                    VALUES (?, 1, 1, ?, ?)''', (today, amount, amount))
                elif text == 'lose':
                    cursor.execute('''INSERT INTO stats_day (date, games, loses, bet_total) 
                                    VALUES (?, 1, 1, ?)''', (today, amount))
            
            self.connection.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка добавления дневной статистики: {e}")
    
    def del_stats_day(self):
        """Удалить статистику за предыдущие дни"""
        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM stats_day WHERE date < ?", (today,))
            self.connection.commit()
            logger.info("✅ Статистика за предыдущие дни удалена")
        except Exception as e:
            logger.error(f"❌ Ошибка удаления статистики: {e}")
    
    def get_today_stats(self):
        """Получить статистику за сегодня"""
        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM stats_day WHERE date = ?", (today,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'date': result[1],
                    'games': result[2],
                    'wins': result[3],
                    'loses': result[4],
                    'payout': result[5],
                    'bet_total': result[6]
                }
            else:
                return {
                    'date': today,
                    'games': 0,
                    'wins': 0,
                    'loses': 0,
                    'payout': 0.0,
                    'bet_total': 0.0
                }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {}
    
    # ==================== ФУНКЦИИ ДЛЯ ССЫЛОК ====================
    
    def get_URL(self):
        """Получить все ссылки"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM urls")
        results = cursor.fetchall()
        urls_dict = {}
        for row in results:
            urls_dict[row[0]] = row[1]
        return urls_dict
    
    def update_url(self, url_id: str, new_url: str) -> bool:
        """Обновить ссылку"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("INSERT OR REPLACE INTO urls (id, url) VALUES (?, ?)", (url_id, new_url))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка обновления ссылки: {e}")
            return False