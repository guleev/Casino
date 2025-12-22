#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import asyncio
import random
import logging
import os
import sys
import time
import ssl
import aiohttp
from typing import Optional, Dict, List, Any, Union, Tuple
import sqlite3
import pytz
import json
from string import digits
from contextlib import asynccontextmanager

# ==================== НАСТРОЙКА ЛОГГИРОВАНИЯ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==================== ИМПОРТЫ AIOGRAM 3.23.0 ====================
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.types import (
    Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardButton, InlineKeyboardMarkup, InputFile, FSInputFile,
    BotCommand, BotCommandScopeDefault, ReplyKeyboardRemove, ContentType,
    PreCheckoutQuery, SuccessfulPayment, LabeledPrice, ShippingOption,
    ShippingQuery, Dice
)
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

# ==================== ИМПОРТ КОНФИГА ====================
try:
    from config import *
    logger.info("✅ Конфиг загружен")
except Exception as e:
    logger.error(f"❌ Ошибка загрузки конфига: {e}")
    raise

# ==================== ИМПОРТ БАЗЫ ДАННЫХ ====================
try:
    from database import DataBase
    db = DataBase()
    logger.info("✅ База данных загружена")
except Exception as e:
    logger.error(f"❌ Ошибка загрузки базы данных: {e}")
    raise

# ==================== ИМПОРТ КЛАВИАТУР ====================
try:
    import keyboards as kb
    logger.info("✅ Клавиатуры загружены")
except Exception as e:
    logger.error(f"❌ Ошибка загрузки клавиатур: {e}")
    raise

# ==================== ФУНКЦИЯ СОЗДАНИЯ ОПТИМИЗИРОВАННОЙ СЕССИИ ====================
def create_optimized_session():
    """Создает оптимизированную сессию для обхода проблем с подключением"""
    
    # 1. SSL контекст - отключаем строгую проверку сертификатов
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # 2. Оптимизированный коннектор
    connector = aiohttp.TCPConnector(
        ssl=ssl_context,
        limit=100,               # Максимум соединений
        ttl_dns_cache=300,       # Кэш DNS на 5 минут
        enable_cleanup_closed=True,
        force_close=True,
        use_dns_cache=True,
        keepalive_timeout=30     # Keep-alive
    )
    
    # 3. Таймауты (увеличены для плохого интернета)
    timeout = aiohttp.ClientTimeout(
        total=60,      # Общий таймаут - 60 секунд
        connect=30,    # Таймаут на подключение - 30 секунд
        sock_read=25,  # Таймаут на чтение - 25 секунд
        sock_connect=20 # Таймаут на соединение сокета
    )
    
    # 4. Создаем сессию с оптимизированными настройками
    session = AiohttpSession(
        connector=connector,
        timeout=timeout
    )
    
    logger.info("🔧 Создана оптимизированная сессия с увеличенными таймаутами")
    return session

# ==================== СОЗДАНИЕ БОТА С ОПТИМИЗИРОВАННОЙ СЕССИЕЙ ====================
try:
    logger.info("🔄 Создаем бота с оптимизированным подключением...")
    
    # Создаем оптимизированную сессию
    session = create_optimized_session()
    
    # Создаем бота
    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True
        )
    )
    
    logger.info(f"✅ Бот {NICNAME} инициализирован")
    
except Exception as e:
    logger.error(f"❌ Ошибка инициализации бота: {e}")
    print(f"\n🔥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
    print("🔧 Проверьте:")
    print("   1. Интернет подключение на сервере")
    print("   2. Правильность BOT_TOKEN в config.py")
    print("   3. Что порт 443 не заблокирован")
    sys.exit(1)

# ==================== ИНИЦИАЛИЗАЦИЯ ДИСПЕТЧЕРА ====================
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== СОСТОЯНИЯ (FSM) ====================
class UserStates(StatesGroup):
    waiting_for_bet_amount = State()
    waiting_for_game_choice = State()
    waiting_for_outcome = State()
    waiting_for_deposit_amount = State()
    waiting_for_withdraw_amount = State()
    waiting_for_withdraw_address = State()
    waiting_for_promo_code = State()
    admin_waiting_for_promo_amount = State()
    admin_waiting_for_promo_code = State()
    admin_waiting_for_promo_max_uses = State()
    admin_waiting_for_promo_expires = State()
    admin_waiting_for_message = State()
    admin_waiting_for_photo = State()
    admin_waiting_for_kef_value = State()
    admin_waiting_for_user_id = State()

class AdminStates(StatesGroup):
    waiting_for_statistics_user_id = State()
    waiting_for_promo_code_creation = State()
    waiting_for_kef_edit = State()
    waiting_for_broadcast_message = State()
    waiting_for_broadcast_photo = State()
    waiting_for_user_balance_edit = State()

# ==================== ФУНКЦИИ ПОМОЩНИКИ ====================
async def set_default_commands():
    """Установка команд бота"""
    await bot.set_my_commands([
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/balance", description="Показать баланс"),
        BotCommand(command="/stats", description="Моя статистика"),
        BotCommand(command="/promo", description="Активировать промокод"),
        BotCommand(command="/help", description="Помощь"),
    ])

async def get_name_game(text: str) -> str:
    """Получение названия игры по тексту"""
    game_dict = {
        'Больше': '🎲 Больше|Меньше',
        'Меньше': '🎲 Больше|Меньше',
        'more': '🎲 Больше|Меньше',
        'less': '🎲 Больше|Меньше',
        '1': '🎲 Угадай число',
        '2': '🎲 Угадай число',
        '3': '🎲 Угадай число',
        '4': '🎲 Угадай число',
        '5': '🎲 Угадай число',
        '6': '🎲 Угадай число',
        'goal': '⚽️ Футбол',
        'miss': '⚽️ Футбол',
        'basket_goal': '🏀 Баскетбол',
        'basket_miss': '🏀 Баскетбол',
        'rock': '✊ Камень',
        'scissors': '✌️ Ножницы',
        'paper': '✋ Бумага',
        'red': '🎡 Красное',
        'black': '🎡 Черное',
        'green': '🎡 Зеленое',
        'even': '🎲 Чет',
        'odd': '🎲 Нечет',
        'spin': '🎰 Слоты',
    }
    
    return game_dict.get(text, '🎲 Игра')

async def send_message_win_users(usdt: float, result_win_amount: float, message_id: int, user_name: str = "", status: str = None) -> Message:
    """Отправка сообщения о победе в канал"""
    try:
        photo = FSInputFile('photos/Wins.jpg')
        caption = f'<b><blockquote>🟢 Победа! \n\n'
        
        if user_name:
            caption += f'👤 Игрок: {user_name}\n'
        
        caption += f'💸 Выигрыш: {round(float(usdt), 2)}$ ({result_win_amount}₽)\n'
        caption += f'🕊 Средства автоматически поступили на ваш кошелек CryptoBot\n'
        caption += f'♻️ Удачи в следующих играх!</blockquote></b>'
        
        return await bot.send_photo(
            chat_id=channal_id,
            photo=photo,
            caption=caption,
            reply_to_message_id=message_id,
            reply_markup=kb.send_stavka()
        )
    except Exception as e:
        logger.error(f"Ошибка отправки фото победы: {e}")
        caption = f'<b><blockquote>🟢 Победа! \n\n'
        
        if user_name:
            caption += f'👤 Игрок: {user_name}\n'
        
        caption += f'💸 Выигрыш: {round(float(usdt), 2)}$ ({result_win_amount}₽)\n'
        caption += f'🕊 Средства автоматически поступили на ваш кошелек CryptoBot\n'
        caption += f'♻️ Удачи в следующих играх!</blockquote></b>'
        
        return await bot.send_message(
            chat_id=channal_id,
            text=caption,
            reply_to_message_id=message_id,
            reply_markup=kb.send_stavka()
        )

async def send_message_lose_users(message_id: int, user_name: str = "") -> Message:
    """Отправка сообщения о проигрыше в канал"""
    await asyncio.sleep(3)
    
    try:
        photo = FSInputFile('photos/Lose.jpg')
        caption = f'<b>🥵 Поражение!\n\n'
        if user_name:
            caption += f'<blockquote>👤 Игрок: {user_name}\n\n'
        else:
            caption += '<blockquote>'
        
        caption += f'Попытай свою удачу снова!\n'
        caption += f'Желаю удачи в следующих ставках!</blockquote></b>'
        
        await bot.send_photo(
            chat_id=channal_id,
            photo=photo,
            caption=caption,
            reply_to_message_id=message_id,
            reply_markup=kb.send_stavka()
        )
    except Exception as e:
        logger.error(f"Ошибка отправки фото проигрыша: {e}")
        caption = f'<b>🥵 Поражение!\n\n'
        if user_name:
            caption += f'<blockquote>👤 Игрок: {user_name}\n\n'
        else:
            caption += '<blockquote>'
        
        caption += f'Попытай свою удачу снова!\n'
        caption += f'Желаю удачи в следующих ставках!</blockquote></b>'
        
        await bot.send_message(
            chat_id=channal_id,
            text=caption,
            reply_to_message_id=message_id,
            reply_markup=kb.send_stavka()
        )

async def create_stavka_message_channel(user_name: str, amount: float, outcome_name: str, is_fake: bool = False) -> Message:
    """Создание сообщения о ставке в канале"""
    urls = db.get_URL()
    help_stavka = hlink('Как сделать ставку', urls.get('info_stavka', 'https://teletype.in/@oeaow-144350/tsIRVcpdqg'))
    info_channel = hlink('Новостной канал', urls.get('news', 'https://t.me/noxwat'))
    url_viplata = hlink('Выплаты', urls.get('transfer', 'https://t.me/NoxwatPayments'))
    url_referal_programm = hlink(f'Реферальная программа [{lose_withdraw}%]', URL_BOT)
    
    game_name = await get_name_game(outcome_name)
    
    header = f'<b>Noxwat Casino | @{NICNAME}:</b>\n\n'
    
    message_channel = await bot.send_message(
        chat_id=channal_id,
        text=header +
             f'🤵🏻‍♂️ Крупье принял новую ставку.\n\n'
             f'👤 Игрок: <b>{user_name}</b>\n'
             f'💸 Ставка: <b>{amount}$</b>\n'
             f'☁️ Исход: <b>{outcome_name}</b>\n'
             f'🕹 Игра: <b>({game_name})</b>\n\n'
             f'<b>{help_stavka} | {info_channel} | {url_viplata}\n'
             f'[ {url_referal_programm} ]</b>',
        reply_markup=kb.send_stavka(),
        disable_web_page_preview=True
    )
    
    return message_channel

async def fake_send_message_win_users(amount: float, KEF: float, rubs_price: float, message_id: int, user_name: str = "") -> Message:
    """Фейковая отправка сообщения о победе"""
    usdt = float(amount) * KEF
    rub = float(rubs_price) * float(usdt)
    result_win_amount = round(float(rub), 2)
    
    await asyncio.sleep(3)
    
    fake_users = "".join(random.choice(digits) for _ in range(5))
    fake_transfer = "".join(random.choice(digits) for _ in range(6))
    date = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        photo = FSInputFile('photos/Wins.jpg')
        await bot.send_photo(
            chat_id=channal_id,
            photo=photo,
            caption=f'<b><blockquote>🔵 Победа! \n\n'
                    f'👤 Игрок: {user_name}\n'
                    f'💸 Выигрыш: {round(float(usdt), 2)}$ ({result_win_amount}₽)\n'
                    f'🕊 Средства автоматически поступили на ваш кошелек CryptoBot\n'
                    f'💙 Удачи в следующих играх!</blockquote></b>',
            reply_to_message_id=message_id,
            reply_markup=kb.send_stavka()
        )
    except Exception as e:
        logger.error(f"Ошибка отправки фейк победы: {e}")
        await bot.send_message(
            chat_id=channal_id,
            text=f'<b><blockquote>🔵 Победа! \n\n'
                 f'👤 Игрок: {user_name}\n'
                 f'💸 Выигрыш: {round(float(usdt), 2)}$ ({result_win_amount}₽)\n'
                 f'🕊 Средства автоматически поступили на ваш кошелек CryptoBot\n'
                 f'💙 Удачи в следующих играх!</blockquote></b>',
            reply_to_message_id=message_id,
            reply_markup=kb.send_stavka()
        )
    
    try:
        photo = FSInputFile('photos/payments.jpg')
        return await bot.send_photo(
            chat_id=ID_SEND_TRANSFER,
            photo=photo,
            caption='💸 <b>Выплата победителю:</b>\n'
                   f'<b>┠ User ID:</b> <code>*****{fake_users}</code>\n'
                   f'<b>┠ ID перевода:</b> <code>{fake_transfer}</code>\n'
                   f'<b>┠ Дата:</b> <code>{date}</code>\n'
                   f'<b>┖ Сумма:</b> <code>{round(float(amount), 2)}$</code>',
            reply_markup=kb.send_okey()
        )
    except Exception as e:
        logger.error(f"Ошибка отправки фейк выплаты: {e}")
        return await bot.send_message(
            chat_id=ID_SEND_TRANSFER,
            text='💸 <b>Выплата победителю:</b>\n'
                 f'<b>┠ User ID:</b> <code>*****{fake_users}</code>\n'
                 f'<b>┠ ID перевода:</b> <code>{fake_transfer}</code>\n'
                 f'<b>┠ Дата:</b> <code>{date}</code>\n'
                 f'<b>┖ Сумма:</b> <code>{round(float(amount), 2)}$</code>',
            reply_markup=kb.send_okey()
        )

async def fake_send_message_lose_users(message_id: int, name: str, stavka: float):
    """Фейковая отправка сообщения о проигрыше"""
    cashback_amount = float(stavka) / 100 * CASHBACK_PROCENT
    
    await asyncio.sleep(3)
    
    try:
        photo = FSInputFile('photos/Lose.jpg')
        await bot.send_photo(
            chat_id=channal_id,
            photo=photo,
            caption=f'<b>🥵 Поражение!\n\n'
                    f'<blockquote>👤 Игрок: {name}\n\n'
                    f'Попытай свою удачу снова!\n'
                    f'Желаю удачи в следующих ставках!</blockquote></b>',
            reply_to_message_id=message_id,
            reply_markup=kb.send_stavka()
        )
    except Exception as e:
        logger.error(f"Ошибка отправки фейк проигрыша: {e}")
        await bot.send_message(
            chat_id=channal_id,
            text=f'<b>🥵 Поражение!\n\n'
                 f'<blockquote>👤 Игрок: {name}\n\n'
                 f'Попытай свою удачу снова!\n'
                 f'Желаю удачи в следующих ставках!</blockquote></b>',
            reply_to_message_id=message_id,
            reply_markup=kb.send_stavka()
        )
    
    if float(stavka) > CASHBACK_LIMIT:
        res = await bot.send_message(
            chat_id=channal_id,
            text=f'💸 <b>{name} получите ваш кэшбэк {round(float(cashback_amount), 1)}$ ({CASHBACK_PROCENT}% от ставки)</b>',
            reply_to_message_id=message_id,
            reply_markup=kb.get_fake_cashback(amount=round(float(cashback_amount), 1), status=0)
        )
        await asyncio.sleep(random.randint(4, 9))
        await bot.edit_message_reply_markup(
            chat_id=channal_id,
            message_id=res.message_id,
            reply_markup=kb.get_fake_cashback(amount=round(float(cashback_amount), 1), status=1)
        )

async def fake_game_adm():
    """Фейковые игры в канале (для активности)"""
    try:
        values_fake = db.get_fake_games_status()
        
        if not values_fake:
            logger.info("❌ Фейк игры отключены")
            return
            
        urls = db.get_URL()
        help_stavka = hlink('Как сделать ставку', urls.get('info_stavka', 'https://teletype.in/@oeaow-144350/tsIRVcpdqg'))
        info_channel = hlink('Новостной канал', urls.get('news', 'https://t.me/noxwat'))
        url_viplata = hlink('Выплаты', urls.get('transfer', 'https://t.me/NoxwatPayments'))
        url_referal_programm = hlink(f'Реферальная программа [{lose_withdraw}%]', URL_BOT)
        
        text_game = random.choice(["Больше", "Меньше", "Чет", "Нечет"])
        amount = random.uniform(DIAPAZONE_AMOUNT[0], DIAPAZONE_AMOUNT[1])
        name = random.choice(FAKE_NICKNAME)
        
        header = f'<b>Noxwat Casino | @{NICNAME}:</b>\n\n'
        
        res = await bot.send_message(
            chat_id=channal_id,
            text=header +
                 f'🤵🏻‍♂️ Крупье принял новую ставку.\n\n'
                 f'👤 Игрок: <b>{name}</b>\n'
                 f'💸 Ставка: <b>{round(float(amount), 1)}$</b>\n'
                 f'☁️ Исход: <b>{text_game}</b>\n'
                 f'🕹 Игра: <b>({await get_name_game(text_game)})</b>\n\n'
                 f'<b>{help_stavka} | {info_channel} | {url_viplata}\n'
                 f'[ {url_referal_programm} ]</b>',
            reply_markup=kb.send_stavka(),
            disable_web_page_preview=True
        )
        
        game = await bot.send_dice(
            chat_id=channal_id,
            emoji='🎲',
            reply_to_message_id=res.message_id
        )
        
        result_game = game.dice.value
        
        # Для фейк игр используем статичный курс
        rubs_price = 100
        
        # Логика определения выигрыша/проигрыша
        if (text_game == 'Меньше' and result_game <= 3) or \
           (text_game == 'Больше' and result_game >= 4) or \
           (text_game == "Чет" and result_game % 2 == 0) or \
           (text_game == "Нечет" and result_game % 2 != 0):
            
            kef = db.get_cur_KEF('KEF1') if text_game in ['Меньше', 'Больше'] else db.get_cur_KEF('KEF5')
            await fake_send_message_win_users(
                amount=round(float(amount), 1),
                KEF=kef,
                message_id=res.message_id,
                rubs_price=rubs_price,
                user_name=name
            )
        else:
            await fake_send_message_lose_users(
                message_id=res.message_id,
                name=name,
                stavka=amount
            )
    except Exception as e:
        logger.error(f"Ошибка в fake_game_adm: {e}")

async def send_promo_activation_photo(user_id: int, promo_code: str, amount: float, new_balance: float):
    """Отправка фотки активации промокода"""
    try:
        photo = FSInputFile('photos/promo_activite.jpg')
        await bot.send_photo(
            chat_id=user_id,
            photo=photo,
            caption=f'🎉 <b>Промокод активирован!</b>\n\n'
                   f'🎫 Код: <code>{promo_code}</code>\n'
                   f'💰 Получено: <code>{amount}$</code>\n'
                   f'💸 Ваш баланс: <code>{round(new_balance, 2)}$</code>\n\n'
                   f'🎲 Удачи в играх!'
        )
    except Exception as e:
        logger.error(f"Ошибка отправки фото промокода: {e}")
        await bot.send_message(
            chat_id=user_id,
            text=f'🎉 <b>Промокод активирован!</b>\n\n'
                 f'🎫 Код: <code>{promo_code}</code>\n'
                 f'💰 Получено: <code>{amount}$</code>\n'
                 f'💸 Ваш баланс: <code>{round(new_balance, 2)}$</code>\n\n'
                 f'🎲 Удачи в играх!'
        )

async def process_game_result(user_id: int, game_type: str, outcome: str, amount: float, message_channel: Message, user_name: str = ""):
    """Обработка результата игры"""
    try:
        # Отправляем игральную кость
        dice_message = await bot.send_dice(
            chat_id=channal_id,
            emoji='🎲',
            reply_to_message_id=message_channel.message_id
        )
        
        await asyncio.sleep(3)
        
        result_game = dice_message.dice.value
        
        # Определяем результат игры
        win = False
        multiplier = 1.0
        
        if game_type == 'more_less':
            if (outcome == 'more' and result_game >= 4) or (outcome == 'less' and result_game <= 3):
                win = True
                multiplier = db.get_cur_KEF('KEF1')
        
        elif game_type == 'number':
            if str(result_game) == outcome:
                win = True
                multiplier = db.get_cur_KEF('KEF2')
        
        elif game_type == 'even_odd':
            if (outcome == 'even' and result_game % 2 == 0) or (outcome == 'odd' and result_game % 2 != 0):
                win = True
                multiplier = db.get_cur_KEF('KEF5')
        
        elif game_type == 'football':
            if (outcome == 'goal' and result_game >= 4) or (outcome == 'miss' and result_game <= 3):
                win = True
                multiplier = db.get_cur_KEF('KEF12' if outcome == 'goal' else 'KEF13')
        
        elif game_type == 'basketball':
            if (outcome == 'basket_goal' and result_game >= 4) or (outcome == 'basket_miss' and result_game <= 3):
                win = True
                multiplier = db.get_cur_KEF('KEF10' if outcome == 'goal' else 'KEF11')
        
        elif game_type == 'roulette':
            if outcome == 'green' and result_game == 6:
                win = True
                multiplier = db.get_cur_KEF('KEF17')
            elif outcome == 'red' and result_game in [1, 3, 5]:
                win = True
                multiplier = db.get_cur_KEF('KEF16')
            elif outcome == 'black' and result_game in [2, 4]:
                win = True
                multiplier = db.get_cur_KEF('KEF16')
        
        elif game_type == 'knb':
            # Простая логика для КНБ
            bot_choice = random.choice(['rock', 'scissors', 'paper'])
            win_chance = db.get_cur_KEF('KNB') / 100
            
            if random.random() < win_chance:
                win = True
                multiplier = db.get_cur_KEF('KEF15')
        
        # Обработка результата
        if win:
            win_amount = amount * multiplier
            db.update_balance(user_id, win_amount, 'add')
            db.add_count_pay(user_id, 'win', win_amount)
            db.add_count_pay_stats_day('win', win_amount)
            
            # Отправляем сообщение о победе
            rubs_price = 100  # Статичный курс для упрощения
            rub_amount = win_amount * rubs_price
            await send_message_win_users(win_amount, rub_amount, message_channel.message_id, user_name)
            
            await bot.send_message(
                chat_id=user_id,
                text=f'🎉 <b>ПОБЕДА!</b>\n\n'
                     f'💰 Вы выиграли: <code>{win_amount:.2f}$</code>\n'
                     f'📈 Коэффициент: <code>{multiplier}x</code>\n'
                     f'💸 Ваш баланс: <code>{db.get_user_balance(user_id):.2f}$</code>'
            )
        else:
            db.add_count_pay(user_id, 'lose', amount)
            db.add_count_pay_stats_day('lose', amount)
            
            # Отправляем сообщение о проигрыше
            await send_message_lose_users(message_channel.message_id, user_name)
            
            await bot.send_message(
                chat_id=user_id,
                text=f'😔 <b>ПРОИГРЫШ</b>\n\n'
                     f'💰 Вы проиграли: <code>{amount:.2f}$</code>\n'
                     f'💸 Ваш баланс: <code>{db.get_user_balance(user_id):.2f}$</code>\n\n'
                     f'Не расстраивайтесь, удача будет на вашей стороне в следующий раз!'
            )
            
    except Exception as e:
        logger.error(f"Ошибка обработки игры: {e}")
        await bot.send_message(user_id, "❌ Произошла ошибка при обработке игры. Попробуйте еще раз.")

# ==================== ОБРАБОТЧИКИ КОМАНД ====================

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start"""
    await state.clear()
    
    user_id = message.from_user.id
    
    # Извлекаем реферальный ID из параметров
    referer_id = None
    if len(message.text.split()) > 1:
        try:
            referer_id = int(message.text.split()[1])
        except:
            pass
    
    # Добавляем/обновляем пользователя
    db.add_user(user_id, referer_id)
    
    welcome_text = (
        f"🎰 <b>Добро пожаловать в {NAME_CASINO}!</b>\n\n"
        f"💰 <b>Ваш баланс:</b> <code>{db.get_user_balance(user_id):.2f}$</code>\n\n"
        f"⚡ <b>Моментальные выплаты</b>\n"
        f"🎁 <b>Бонус за первый депозит:</b> {WELCOME_BONUS}%\n"
        f"👥 <b>Реферальная программа:</b> до {lose_withdraw}%\n\n"
        f"<b>Выберите действие:</b>"
    )
    
    await message.answer(welcome_text, reply_markup=kb.kb_menu(user_id))

@dp.message(Command('help'))
async def cmd_help(message: Message):
    """Обработка команды /help"""
    help_text = (
        f"🆘 <b>Помощь по {NAME_CASINO}</b>\n\n"
        f"<b>Основные команды:</b>\n"
        f"• /start - Запустить бота\n"
        f"• /balance - Показать баланс\n"
        f"• /stats - Моя статистика\n"
        f"• /promo - Активировать промокод\n"
        f"• /help - Эта справка\n\n"
        f"<b>Минимальные суммы:</b>\n"
        f"• Ставка: {MIN_STAVKA}$\n"
        f"• Вывод: {MIN_WITHDRAW}$\n\n"
        f"<b>Поддержка:</b> {SUPPORT_USERNAME}\n"
        f"<b>Время работы:</b> {WORK_HOURS}\n"
        f"<b>Время ответа:</b> {RESPONSE_TIME}"
    )
    
    await message.answer(help_text)

@dp.message(Command('balance'))
async def cmd_balance(message: Message):
    """Обработка команды /balance"""
    user_id = message.from_user.id
    balance = db.get_user_balance(user_id)
    
    balance_text = (
        f"💰 <b>Ваш баланс:</b> <code>{balance:.2f}$</code>\n\n"
        f"💳 <b>Пополнение:</b> от {MIN_STAVKA}$\n"
        f"📤 <b>Вывод:</b> от {MIN_WITHDRAW}$\n"
        f"🎲 <b>Минимальная ставка:</b> {MIN_STAVKA}$"
    )
    
    await message.answer(balance_text, reply_markup=kb.kb_balance())

@dp.message(Command('stats'))
async def cmd_stats(message: Message):
    """Обработка команды /stats"""
    user_id = message.from_user.id
    user_info = db.user_exists(user_id)
    
    if not user_info:
        await message.answer("❌ Информация о пользователе не найдена.")
        return
    
    stats_text = (
        f"📊 <b>Ваша статистика</b>\n\n"
        f"👤 <b>Пользователь:</b> {message.from_user.first_name} {message.from_user.last_name if message.from_user.last_name else ''}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n\n"
        f"💰 <b>Баланс:</b> <code>{db.get_user_balance(user_id):.2f}$</code>\n\n"
        f"🎲 <b>Минимальная ставка:</b> {MIN_STAVKA}$\n"
        f"📤 <b>Минимальный вывод:</b> {MIN_WITHDRAW}$\n"
        f"👥 <b>Реферальная программа:</b> до {lose_withdraw}%"
    )
    
    await message.answer(stats_text)

@dp.message(Command('promo'))
async def cmd_promo(message: Message):
    """Обработка команды /promo"""
    await message.answer(
        "🎁 <b>Промокоды</b>\n\n"
        "Здесь вы можете активировать промокод для получения бонуса на баланс.\n\n"
        "Для активации нажмите кнопку ниже:",
        reply_markup=kb.kb_promo()
    )

# ==================== ОБРАБОТЧИКИ КНОПОК ГЛАВНОГО МЕНЮ ====================

@dp.message(F.text == '💰 Мой баланс')
async def my_balance(message: Message):
    """Обработка кнопки 'Мой баланс'"""
    user_id = message.from_user.id
    balance = db.get_user_balance(user_id)
    
    balance_text = (
        f"💰 <b>Ваш баланс:</b> <code>{balance:.2f}$</code>\n\n"
        f"💳 <b>Пополнение:</b> от {MIN_STAVKA}$\n"
        f"📤 <b>Вывод:</b> от {MIN_WITHDRAW}$\n"
        f"🎲 <b>Минимальная ставка:</b> {MIN_STAVKA}$"
    )
    
    await message.answer(balance_text, reply_markup=kb.kb_balance())

@dp.message(F.text == '🎲 Сделать ставку')
async def make_bet(message: Message, state: FSMContext):
    """Обработка кнопки 'Сделать ставку'"""
    user_id = message.from_user.id
    balance = db.get_user_balance(user_id)
    
    if balance < MIN_STAVKA:
        await message.answer(
            f"❌ <b>Недостаточно средств для ставки</b>\n\n"
            f"💰 Ваш баланс: <code>{balance:.2f}$</code>\n"
            f"🎲 Минимальная ставка: <code>{MIN_STAVKA}$</code>\n\n"
            f"Пополните баланс, чтобы начать играть!"
        )
        return
    
    await message.answer(
        f"🎲 <b>Выберите игру</b>\n\n"
        f"💰 <b>Ваш баланс:</b> <code>{balance:.2f}$</code>\n"
        f"🎯 <b>Минимальная ставка:</b> {MIN_STAVKA}$\n\n"
        f"Выберите игру из списка ниже:",
        reply_markup=kb.kb_games()
    )

@dp.message(F.text == '📎 Реферальная программа')
async def referral_program(message: Message):
    """Обработка кнопки 'Реферальная программа'"""
    user_id = message.from_user.id
    
    referral_link = f"https://t.me/{NICNAME}?start={user_id}"
    
    referral_text = (
        f"👥 <b>Реферальная программа {NAME_CASINO}</b>\n\n"
        f"💸 <b>Ваша ссылка для приглашений:</b>\n"
        f"<code>{referral_link}</code>\n\n"
        f"🎁 <b>Условия программы:</b>\n"
        f"• Вы получаете {lose_withdraw}% от проигрышей приглашенных\n"
        f"• Минимальная ставка реферала: {min_stavka_referal}$\n"
        f"• Вывод доступен от {MIN_WITHDRAW}$\n\n"
        f"Приглашайте друзей и зарабатывайте вместе с нами!"
    )
    
    await message.answer(referral_text, reply_markup=kb.kb_referral())

@dp.message(F.text == '💭 Информация')
async def information(message: Message):
    """Обработка кнопки 'Информация'"""
    info_text = (
        f"ℹ️ <b>Информация о {NAME_CASINO}</b>\n\n"
        f"🎰 <b>О нашем казино:</b>\n"
        f"• Моментальные выплаты\n"
        f"• Честные игры\n"
        f"• Высокие коэффициенты\n"
        f"• Круглосуточная поддержка\n\n"
        f"💰 <b>Минимальные суммы:</b>\n"
        f"• Ставка: {MIN_STAVKA}$\n"
        f"• Вывод: {MIN_WITHDRAW}$\n\n"
        f"🎁 <b>Бонусы:</b>\n"
        f"• Приветственный бонус: {WELCOME_BONUS}%\n"
        f"• Кэшбэк: {CASHBACK_PROCENT}%\n"
        f"• Реферальная программа: до {lose_withdraw}%\n\n"
        f"⏰ <b>Время работы поддержки:</b> {WORK_HOURS}\n"
        f"⚡ <b>Время ответа:</b> {RESPONSE_TIME}"
    )
    
    await message.answer(info_text, reply_markup=kb.kb_info())

@dp.message(F.text == '🎁 Промокоды')
async def promocodes(message: Message):
    """Обработка кнопки 'Промокоды'"""
    await message.answer(
        "🎁 <b>Промокоды</b>\n\n"
        "Здесь вы можете активировать промокод для получения бонуса на баланс.\n\n"
        "Для активации нажмите кнопку ниже:",
        reply_markup=kb.kb_promo()
    )

@dp.message(F.text == '📊 Моя статистика')
async def my_stats(message: Message):
    """Обработка кнопки 'Моя статистика'"""
    await cmd_stats(message)

@dp.message(F.text == '👑 Админка')
async def admin_panel(message: Message):
    """Обработка кнопки 'Админка'"""
    if message.from_user.id not in ADMIN:
        await message.answer("❌ У вас нет доступа к админ панели.")
        return
    
    admin_text = (
        f"👑 <b>Админ панель {NAME_CASINO}</b>\n\n"
        f"👤 <b>Администратор:</b> {message.from_user.first_name}\n"
        f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n\n"
        f"Выберите раздел для управления:"
    )
    
    await message.answer(admin_text, reply_markup=kb.kb_admin())

# ==================== ОБРАБОТЧИКИ CALLBACK-ЗАПРОСОВ ====================

@dp.callback_query(F.data == 'back_to_main_menu')
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.delete()
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=f"🎰 <b>{NAME_CASINO}</b>\n\nВыберите действие:",
        reply_markup=kb.kb_menu(callback.from_user.id)
    )

@dp.callback_query(F.data == 'back_to_games')
async def back_to_games(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору игры"""
    await state.clear()
    user_id = callback.from_user.id
    balance = db.get_user_balance(user_id)
    
    await callback.message.edit_text(
        f"🎲 <b>Выберите игру</b>\n\n"
        f"💰 <b>Ваш баланс:</b> <code>{balance:.2f}$</code>\n"
        f"🎯 <b>Минимальная ставка:</b> {MIN_STAVKA}$\n\n"
        f"Выберите игру из списка ниже:",
        reply_markup=kb.kb_games()
    )

@dp.callback_query(F.data == 'cancel')
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена действия"""
    await state.clear()
    await callback.message.delete()
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text="❌ Действие отменено.",
        reply_markup=kb.kb_menu(callback.from_user.id)
    )

@dp.callback_query(F.data.startswith('game_'))
async def select_game(callback: CallbackQuery, state: FSMContext):
    """Выбор игры"""
    game_type = callback.data.replace('game_', '')
    
    await state.update_data(game_type=game_type)
    
    if game_type == 'more_less':
        await callback.message.edit_text(
            "🎲 <b>Больше/Меньше</b>\n\n"
            "Выберите исход:\n"
            "• <b>Больше</b> (4-6) - выигрыш если выпадет 4, 5 или 6\n"
            "• <b>Меньше</b> (1-3) - выигрыш если выпадет 1, 2 или 3\n\n"
            "Коэффициент: 2.0x",
            reply_markup=kb.kb_more_less()
        )
    
    elif game_type == 'number':
        await callback.message.edit_text(
            "🎯 <b>Угадай число</b>\n\n"
            "Выберите число от 1 до 6:\n"
            "Если вы угадаете выпавшее число - вы выигрываете!\n\n"
            "Коэффициент: 6.0x",
            reply_markup=kb.kb_numbers()
        )
    
    elif game_type == 'even_odd':
        await callback.message.edit_text(
            "🎲 <b>Чет/Нечет</b>\n\n"
            "Выберите исход:\n"
            "• <b>Чет</b> - выигрыш если выпадет четное число (2, 4, 6)\n"
            "• <b>Нечет</b> - выигрыш если выпадет нечетное число (1, 3, 5)\n\n"
            "Коэффициент: 2.0x",
            reply_markup=kb.kb_even_odd()
        )
    
    elif game_type == 'football':
        await callback.message.edit_text(
            "⚽️ <b>Футбол</b>\n\n"
            "Выберите исход:\n"
            "• <b>Гол</b> - выигрыш если выпадет 4, 5 или 6\n"
            "• <b>Мимо</b> - выигрыш если выпадет 1, 2 или 3\n\n"
            "Коэффициент: 2.5x",
            reply_markup=kb.kb_football()
        )
    
    elif game_type == 'basketball':
        await callback.message.edit_text(
            "🏀 <b>Баскетбол</b>\n\n"
            "Выберите исход:\n"
            "• <b>Гол</b> - выигрыш если выпадет 4, 5 или 6\n"
            "• <b>Мимо</b> - выигрыш если выпадет 1, 2 или 3\n\n"
            "Коэффициент: 2.5x",
            reply_markup=kb.kb_basketball()
        )
    
    elif game_type == 'roulette':
        await callback.message.edit_text(
            "🎡 <b>Рулетка</b>\n\n"
            "Выберите цвет:\n"
            "• <b>🔴 Красное</b> - выигрыш если выпадет 1, 3 или 5\n"
            "• <b>⚫️ Черное</b> - выигрыш если выпадет 2 или 4\n"
            "• <b>🟢 Зеленое</b> - выигрыш если выпадет 6\n\n"
            "Коэффициенты:\n"
            "• Красное/Черное: 2.0x\n"
            "• Зеленое: 14.0x",
            reply_markup=kb.kb_roulette()
        )
    
    elif game_type == 'knb':
        await callback.message.edit_text(
            "✊✌️✋ <b>Камень-Ножницы-Бумага</b>\n\n"
            "Выберите ваш ход:\n"
            "• <b>✊ Камень</b>\n"
            "• <b>✌️ Ножницы</b>\n"
            "• <b>✋ Бумага</b>\n\n"
            "Шанс победы: 50%\n"
            "Коэффициент: 3.0x",
            reply_markup=kb.kb_knb()
        )
    
    elif game_type == 'slots':
        await callback.message.edit_text(
            "🎰 <b>Слоты</b>\n\n"
            "Нажмите кнопку ниже, чтобы сделать ставку на слоты.\n\n"
            "Коэффициенты:\n"
            "• 3 одинаковых символа: 5.0x\n"
            "• 2 одинаковых символа: 2.0x",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='🎰 Сделать ставку на слоты', callback_data='outcome_spin')],
                [InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_games')]
            ])
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith('outcome_'))
async def select_outcome(callback: CallbackQuery, state: FSMContext):
    """Выбор исхода в игре"""
    user_id = callback.from_user.id
    outcome = callback.data.replace('outcome_', '')
    
    data = await state.get_data()
    game_type = data.get('game_type')
    
    if not game_type:
        await callback.answer("❌ Сначала выберите игру")
        return
    
    await state.update_data(outcome=outcome)
    
    # Запрашиваем сумму ставки
    await callback.message.edit_text(
        f"💰 <b>Введите сумму ставки</b>\n\n"
        f"🎲 Игра: <b>{game_type}</b>\n"
        f"🎯 Исход: <b>{outcome}</b>\n\n"
        f"💰 Ваш баланс: <code>{db.get_user_balance(user_id):.2f}$</code>\n"
        f"🎲 Минимальная ставка: <code>{MIN_STAVKA}$</code>\n"
        f"📊 Максимальная ставка: <code>{LIMIT_STAVKA}$</code>\n\n"
        f"Введите сумму цифрами (например: 1.5):",
        reply_markup=kb.kb_cancel()
    )
    
    await state.set_state(UserStates.waiting_for_bet_amount)
    await callback.answer()

@dp.message(UserStates.waiting_for_bet_amount)
async def process_bet_amount(message: Message, state: FSMContext):
    """Обработка суммы ставки"""
    user_id = message.from_user.id
    
    try:
        amount = float(message.text.replace(',', '.'))
        
        if amount < MIN_STAVKA:
            await message.answer(
                f"❌ <b>Слишком маленькая ставка</b>\n\n"
                f"Минимальная ставка: <code>{MIN_STAVKA}$</code>\n"
                f"Введите сумму еще раз:"
            )
            return
        
        if amount > LIMIT_STAVKA:
            await message.answer(
                f"❌ <b>Слишком большая ставка</b>\n\n"
                f"Максимальная ставка: <code>{LIMIT_STAVKA}$</code>\n"
                f"Введите сумму еще раз:"
            )
            return
        
        balance = db.get_user_balance(user_id)
        if amount > balance:
            await message.answer(
                f"❌ <b>Недостаточно средств</b>\n\n"
                f"Ваш баланс: <code>{balance:.2f}$</code>\n"
                f"Сумма ставки: <code>{amount:.2f}$</code>\n\n"
                f"Введите меньшую сумму:"
            )
            return
        
        # Списываем средства
        if not db.update_balance(user_id, amount, 'subtract'):
            await message.answer("❌ Ошибка при списании средств. Попробуйте еще раз.")
            await state.clear()
            return
        
        data = await state.get_data()
        game_type = data.get('game_type')
        outcome = data.get('outcome')
        
        # Получаем имя пользователя для отображения
        user = message.from_user
        user_name = user.username if user.username else f"{user.first_name} {user.last_name if user.last_name else ''}".strip()
        
        # Создаем сообщение о ставке в канале
        outcome_name = outcome
        if game_type == 'more_less':
            outcome_name = "Больше" if outcome == "more" else "Меньше"
        elif game_type == 'even_odd':
            outcome_name = "Чет" if outcome == "even" else "Нечет"
        elif game_type == 'football':
            outcome_name = "Гол" if outcome == "goal" else "Мимо"
        elif game_type == 'basketball':
            outcome_name = "Гол" if outcome == "basket_goal" else "Мимо"
        elif game_type == 'roulette':
            outcome_name = "Красное" if outcome == "red" else ("Черное" if outcome == "black" else "Зеленое")
        elif game_type == 'knb':
            outcome_name = "Камень" if outcome == "rock" else ("Ножницы" if outcome == "scissors" else "Бумага")
        
        message_channel = await create_stavka_message_channel(user_name, amount, outcome_name)
        
        # Запускаем обработку игры
        await process_game_result(user_id, game_type, outcome, amount, message_channel, user_name)
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат суммы</b>\n\n"
            "Введите сумму цифрами (например: 1.5 или 10):"
        )
    except Exception as e:
        logger.error(f"Ошибка обработки ставки: {e}")
        await message.answer("❌ Произошла ошибка при обработке ставки. Попробуйте еще раз.")
        await state.clear()

@dp.callback_query(F.data == 'deposit')
async def deposit_callback(callback: CallbackQuery):
    """Обработка кнопки 'Пополнить баланс'"""
    await callback.message.edit_text(
        "💳 <b>Пополнение баланса</b>\n\n"
        "Для пополнения баланса свяжитесь с администратором:\n"
        f"👤 {SUPPORT_USERNAME}\n\n"
        f"Минимальная сумма пополнения: {MIN_STAVKA}$\n"
        f"Бонус за первый депозит: {WELCOME_BONUS}%",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='📞 Связаться с поддержкой', url=f'https://t.me/{ADMIN_USERNAME[1:]}')],
            [InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_main_menu')]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == 'withdraw')
async def withdraw_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Вывести средства'"""
    user_id = callback.from_user.id
    balance = db.get_user_balance(user_id)
    
    if balance < MIN_WITHDRAW:
        await callback.message.edit_text(
            f"❌ <b>Недостаточно средств для вывода</b>\n\n"
            f"💰 Ваш баланс: <code>{balance:.2f}$</code>\n"
            f"📤 Минимальная сумма вывода: <code>{MIN_WITHDRAW}$</code>\n\n"
            f"Пополните баланс или сделайте ставку, чтобы вывести средства!",
            reply_markup=kb.kb_cancel()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"📤 <b>Вывод средств</b>\n\n"
        f"💰 <b>Ваш баланс:</b> <code>{balance:.2f}$</code>\n"
        f"📊 <b>Минимальная сумма:</b> {MIN_WITHDRAW}$\n\n"
        f"Для вывода средств свяжитесь с администратором:\n"
        f"👤 {SUPPORT_USERNAME}\n\n"
        f"Укажите сумму вывода и адрес кошелька USDT (TRC-20).",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='📞 Связаться с поддержкой', url=f'https://t.me/{ADMIN_USERNAME[1:]}')],
            [InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_main_menu')]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == 'activate_promo')
async def activate_promo_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Активировать промокод'"""
    await callback.message.edit_text(
        "🎫 <b>Активация промокода</b>\n\n"
        "Введите промокод для активации:",
        reply_markup=kb.kb_cancel()
    )
    await state.set_state(UserStates.waiting_for_promo_code)
    await callback.answer()

@dp.message(UserStates.waiting_for_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    """Обработка промокода"""
    user_id = message.from_user.id
    promo_code = message.text.strip().upper()
    
    # Активируем промокод
    result = db.activate_promo_code(user_id, promo_code)
    
    if result['success']:
        amount = result['amount']
        new_balance = result.get('new_balance', db.get_user_balance(user_id))
        
        # Отправляем фото с сообщением об активации
        await send_promo_activation_photo(user_id, promo_code, amount, new_balance)
    else:
        await message.answer(
            f"❌ <b>Ошибка активации промокода</b>\n\n"
            f"{result['message']}\n\n"
            f"Попробуйте еще раз или введите другой промокод:",
            reply_markup=kb.kb_cancel()
        )
        return
    
    await state.clear()

# ==================== ЗАПУСК БОТА ====================

async def on_startup():
    """Действия при запуске бота"""
    await set_default_commands()
    
    # Запуск фейк игр в фоновом режиме
    if db.get_fake_games_status():
        asyncio.create_task(run_fake_games())
    
    logger.info(f"✅ Бот {NICNAME} запущен")
    print(f"\n{'='*50}")
    print(f"🚀 {NAME_CASINO} запущен!")
    print(f"🤖 Бот: @{NICNAME}")
    print(f"👑 Админы: {len(ADMIN)}")
    print(f"👥 Пользователей в БД: {db.get_total_users()}")
    print(f"{'='*50}\n")

async def run_fake_games():
    """Запуск фейк игр в фоновом режиме"""
    while True:
        try:
            if db.get_fake_games_status():
                interval = TIMER
                await asyncio.sleep(interval)
                
                await fake_game_adm()
            else:
                await asyncio.sleep(60)  # Проверяем каждую минуту
        except Exception as e:
            logger.error(f"Ошибка в фейк играх: {e}")
            await asyncio.sleep(60)

async def on_shutdown():
    """Действия при выключении бота"""
    logger.info("🛑 Бот выключается...")
    await bot.session.close()

if __name__ == "__main__":
    # Запуск бота
    try:
        async def main():
            await on_startup()
            await dp.start_polling(bot)
        
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске бота: {e}")
        sys.exit(1)