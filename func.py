import datetime
import random
import asyncio
import pytz
import os

from aiogram.filters import BaseFilter
from aiogram.types import BotCommand, BotCommandScopeDefault, Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hlink

from loader import bot, crypto, db, scheduler
from string import digits
from aiocryptopay.exceptions import CodeErrorFactory
from aiogram import types
from config import *
from keybords import *


async def set_default_commands():
    await bot.set_my_commands([
        BotCommand(command="/start", description="Запустить бота")
    ], scope=BotCommandScopeDefault())

async def scheduler_jobs():
    scheduler.add_job(del_order_day, "cron", day='*', hour=0, minute=0)
    scheduler.add_job(fake_game_adm, 'interval', seconds=TIMER)
    scheduler.add_job(warning_check_day, "cron", day='*', hour=23, minute=55)

async def del_order_day():
    """Обнуляем статистику за день и удаляем все чеки"""
    db.del_stats_day()
    print('✅ Статистика за день обновлена')
    
    try:
        all_checks = await crypto.get_checks(asset='USDT', status='active')
        if all_checks:
            for check in all_checks:
                try:
                    await crypto.delete_check(check.check_id)
                except Exception as e:
                    print(f"Ошибка удаления чека: {e}")
            await bot.send_message(channal_id, text="<b>✅ Активные чеки удалены</b>")
    except Exception as e:
        print(f"Ошибка получения чеков: {e}")

async def warning_check_day():
    """Предупреждение об удалении чеков"""
    await bot.send_message(channal_id, text='<b>⏳ Через 5 минут будет удаление всех активных чеков</b>')

async def get_transfer_channel():
    """Получение информации о переводе"""
    try:
        info = await crypto.get_transfers(asset='USDT', count=1)
        if info and len(info) > 0:
            transfer = info[0]
            date = transfer.completed_at
            user_id = transfer.user_id
            amount = transfer.amount
            transfer_id = transfer.transfer_id
            
            date_str = date.now(pytz.timezone('Europe/Moscow')).strftime('%Y-%m-%d %H:%M:%S')
            user = str(user_id)[-5:] if len(str(user_id)) > 5 else str(user_id)
            
            # Отправляем с фоткой payments.jpg
            try:
                photo = FSInputFile('photos/payments.jpg')
                return await bot.send_photo(
                    chat_id=ID_SEND_TRANSFER,
                    photo=photo,
                    caption='💸 <b>Выплата победителю:</b>\n'
                           f'<b>┠ User ID:</b> <code>*****{user}</code>\n'
                           f'<b>┠ ID перевода:</b> <code>{transfer_id}</code>\n'
                           f'<b>┠ Дата:</b> <code>{date_str}</code>\n'
                           f'<b>┖ Сумма:</b> <code>{round(float(amount), 2)}$</code>',
                    reply_markup=send_okey()
                )
            except:
                return await bot.send_message(
                    chat_id=ID_SEND_TRANSFER,
                    text='💸 <b>Выплата победителю:</b>\n'
                         f'<b>┠ User ID:</b> <code>*****{user}</code>\n'
                         f'<b>┠ ID перевода:</b> <code>{transfer_id}</code>\n'
                         f'<b>┠ Дата:</b> <code>{date_str}</code>\n'
                         f'<b>┖ Сумма:</b> <code>{round(float(amount), 2)}$</code>',
                    reply_markup=send_okey()
                )
    except Exception as e:
        print(f"Ошибка получения информации о переводе: {e}")
        return None

async def send_message_win_users(usdt, result_win_amount, message_id, user_name="", status=None):
    """Отправка сообщения о победе в канал (унифицированная)"""
    try:
        photo = FSInputFile('photos/Wins.jpg')  # ИЗМЕНЕНО: .png -> .jpg
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
            reply_markup=send_stavka()
        )
    except Exception as e:
        print(f"Ошибка отправки фото победы: {e}")
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
            reply_markup=send_stavka()
        )

async def fake_send_message_win_users(amount, KEF, rubs_price, message_id, user_name=""):
    """Фейковая отправка сообщения о победе"""
    usdt = float(amount) * KEF
    rub = float(rubs_price) * float(usdt)
    result_win_amount = round(float(rub), 2)
    
    await asyncio.sleep(3)
    
    fake_users = "".join(random.choice(digits) for _ in range(5))
    fake_transfer = "".join(random.choice(digits) for _ in range(6))
    date = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime('%Y-%m-%d %H:%M:%S')
    
    # Отправляем в игровой канал
    try:
        photo = FSInputFile('photos/Wins.jpg')  # ИЗМЕНЕНО: .png -> .jpg
        await bot.send_photo(
            chat_id=channal_id,
            photo=photo,
            caption=f'<b><blockquote>🔵 Победа! \n\n'
                    f'👤 Игрок: {user_name}\n'
                    f'💸 Выигрыш: {round(float(usdt), 2)}$ ({result_win_amount}₽)\n'
                    f'🕊 Средства автоматически поступили на ваш кошелек CryptoBot\n'
                    f'💙 Удачи в следующих играх!</blockquote></b>',
            reply_to_message_id=message_id,
            reply_markup=send_stavka()
        )
    except:
        await bot.send_message(
            chat_id=channal_id,
            text=f'<b><blockquote>🔵 Победа! \n\n'
                 f'👤 Игрок: {user_name}\n'
                 f'💸 Выигрыш: {round(float(usdt), 2)}$ ({result_win_amount}₽)\n'
                 f'🕊 Средства автоматически поступили на ваш кошелек CryptoBot\n'
                 f'💙 Удачи в следующих играх!</blockquote></b>',
            reply_to_message_id=message_id,
            reply_markup=send_stavka()
        )
    
    # Отправляем в канал выплат с фоткой
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
            reply_markup=send_okey()
        )
    except:
        return await bot.send_message(
            chat_id=ID_SEND_TRANSFER,
            text='💸 <b>Выплата победителю:</b>\n'
                 f'<b>┠ User ID:</b> <code>*****{fake_users}</code>\n'
                 f'<b>┠ ID перевода:</b> <code>{fake_transfer}</code>\n'
                 f'<b>┠ Дата:</b> <code>{date}</code>\n'
                 f'<b>┖ Сумма:</b> <code>{round(float(amount), 2)}$</code>',
            reply_markup=send_okey()
        )

async def send_message_lose_users(message_id, user_name=""):
    """Отправка сообщения о проигрыше в канал (унифицированная)"""
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
            reply_markup=send_stavka()
        )
    except:
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
            reply_markup=send_stavka()
        )

async def fake_send_message_lose_users(message_id, name, stavka):
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
            reply_markup=send_stavka()
        )
    except:
        await bot.send_message(
            chat_id=channal_id,
            text=f'<b>🥵 Поражение!\n\n'
                 f'<blockquote>👤 Игрок: {name}\n\n'
                 f'Попытай свою удачу снова!\n'
                 f'Желаю удачи в следующих ставках!</blockquote></b>',
            reply_to_message_id=message_id,
            reply_markup=send_stavka()
        )
    
    if float(stavka) > CASHBACK_LIMIT:
        res = await bot.send_message(
            chat_id=channal_id,
            text=f'💸 <b>{name} получите ваш кэшбэк {round(float(cashback_amount), 1)}$ ({CASHBACK_PROCENT}% от ставки)</b>',
            reply_to_message_id=message_id,
            reply_markup=get_fake_cashback(amount=round(float(cashback_amount), 1), status=0)
        )
        await asyncio.sleep(random.randint(4, 9))
        await bot.edit_message_reply_markup(
            chat_id=channal_id,
            message_id=res.message_id,
            reply_markup=get_fake_cashback(amount=round(float(cashback_amount), 1), status=1)
        )

async def create_stavka_message_channel(user_name, amount, outcome_name, is_fake=False):
    """Создание сообщения о ставке в канале (унифицированная)"""
    url = db.get_URL()
    help_stavka = hlink('Как сделать ставку', url.get('info_stavka', 'https://teletype.in/@oeaow-144350/tsIRVcpdqg'))
    info_channel = hlink('Новостной канал', url.get('news', 'https://t.me/noxwat'))
    url_viplata = hlink('Выплаты', url.get('transfer', 'https://t.me/NoxwatPayments'))
    url_referal_programm = hlink(f'Реферальная программа [{lose_withdraw}%]', URL_BOT)
    
    game_name = await get_name_game(outcome_name)
    
    # Заголовок с казино и юзернеймом бота
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
        reply_markup=send_stavka(),
        disable_web_page_preview=True
    )
    
    return message_channel

async def get_name_game(text: str):
    """Получение названия игры по тексту"""
    game_dict = {
        'Больше': '🎲 Больше|Меньше',
        'Меньше': '🎲 Больше|Меньше',
        '1': '🎲 Угадай число',
        '2': '🎲 Угадай число',
        '3': '🎲 Угадай число',
        '4': '🎲 Угадай число',
        '5': '🎲 Угадай число',
        '6': '🎲 Угадай число',
        'more': '🎲 Больше|Меньше',
        'less': '🎲 Больше|Меньше',
        'spin': '🎰 Слоты',
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
    }
    
    return game_dict.get(text, '🎲 Игра')

class IsAdmin(BaseFilter):
    """Фильтр для проверки админа"""
    async def __call__(self, message: Message):
        return message.from_user.id in ADMIN

async def fake_game_adm():
    """Фейковые игры в канале (для активности)"""
    try:
        values_fake = db.get_fake_values()
        
        if not values_fake:
            print("❌ Фейк игры отключены")
            return
            
        urls = db.get_URL()
        help_stavka = hlink('Как сделать ставку', urls.get('info_stavka', 'https://teletype.in/@oeaow-144350/tsIRVcpdqg'))
        info_channel = hlink('Новостной канал', urls.get('news', 'https://t.me/noxwat'))
        url_viplata = hlink('Выплаты', urls.get('transfer', 'https://t.me/NoxwatPayments'))
        url_referal_programm = hlink(f'Реферальная программа [{lose_withdraw}%]', URL_BOT)
        
        text_game = random.choice(["Больше", "Меньше", "Чет", "Нечет"])
        amount = random.uniform(DIAPAZONE_AMOUNT[0], DIAPAZONE_AMOUNT[1])
        name = random.choice(FAKE_NICKNAME)
        
        # Отправляем сообщение о ставке
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
            reply_markup=send_stavka(),
            disable_web_page_preview=True
        )
        
        game = await bot.send_dice(
            chat_id=channal_id,
            emoji='🎲',
            reply_to_message_id=res.message_id
        )
        
        result_game = game.dice.value
        
        try:
            exchange = await crypto.get_exchange_rates()
            rubs_price = exchange[0].rate if exchange else 100
        except:
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
        print(f"Ошибка в fake_game_adm: {e}")

async def send_promo_activation_photo(user_id, promo_code, amount, new_balance):
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
    except:
        await bot.send_message(
            chat_id=user_id,
            text=f'🎉 <b>Промокод активирован!</b>\n\n'
                 f'🎫 Код: <code>{promo_code}</code>\n'
                 f'💰 Получено: <code>{amount}$</code>\n'
                 f'💸 Ваш баланс: <code>{round(new_balance, 2)}$</code>\n\n'
                 f'🎲 Удачи в играх!'
        )