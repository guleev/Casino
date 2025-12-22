from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.markdown import hlink
from config import *
import database

db = database.DataBase()

# ==================== КНОПКИ ДЛЯ МЕНЮ ====================

def kb_menu(user_id):
    """Клавиатура главного меню"""
    keyboard = [
        [KeyboardButton(text='💰 Мой баланс'), KeyboardButton(text='🎲 Сделать ставку')],
        [KeyboardButton(text='📎 Реферальная программа'), KeyboardButton(text='💭 Информация')],
        [KeyboardButton(text='🎁 Промокоды'), KeyboardButton(text='📊 Моя статистика')],
    ]
    if user_id in ADMIN:
        keyboard.append([KeyboardButton(text='👑 Админка')])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, input_field_placeholder='Выберите действие👇')

def kb_admin():
    """Клавиатура админ панели"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📊 Статистика проекта', callback_data='stats_project')],
        [InlineKeyboardButton(text='👤 Статистика игрока', callback_data='stats_user')],
        [InlineKeyboardButton(text='🎁 Промокоды', callback_data='promo_codes')],
        [InlineKeyboardButton(text='⚙️ Настройки фейк игр', callback_data='settings_fake')],
        [InlineKeyboardButton(text='📈 Коэффициенты', callback_data='kef_edit')],
        [InlineKeyboardButton(text='📣 Рассылка', callback_data='all_message_send')],
        [InlineKeyboardButton(text='🔗 Ссылки проекта', callback_data='urls')],
        [InlineKeyboardButton(text='🧹 Удалить чеки', callback_data='deleted_checks')],
        [InlineKeyboardButton(text='💳 Пополнить баланс казино', callback_data='add_balance')],
        [InlineKeyboardButton(text='🔙 В меню', callback_data='back_to_main_menu')]
    ])

def kb_back_admin():
    """Кнопка назад в админку"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_admin')]
    ])

def kb_balance():
    """Клавиатура для баланса"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='💳 Пополнить баланс', callback_data='deposit')],
        [InlineKeyboardButton(text='📤 Вывести средства', callback_data='withdraw')],
        [InlineKeyboardButton(text='🔙 В меню', callback_data='back_to_main_menu')]
    ])

def kb_games():
    """Клавиатура для выбора игры"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='🎲 Больше/Меньше', callback_data='game_more_less'),
            InlineKeyboardButton(text='🎯 Число', callback_data='game_number')
        ],
        [
            InlineKeyboardButton(text='⚽️ Футбол', callback_data='game_football'),
            InlineKeyboardButton(text='🏀 Баскетбол', callback_data='game_basketball')
        ],
        [
            InlineKeyboardButton(text='✊✌️✋ КНБ', callback_data='game_knb'),
            InlineKeyboardButton(text='🎡 Рулетка', callback_data='game_roulette')
        ],
        [
            InlineKeyboardButton(text='🎰 Слоты', callback_data='game_slots'),
            InlineKeyboardButton(text='🎲 Чет/Нечет', callback_data='game_even_odd')
        ],
        [InlineKeyboardButton(text='🔙 В меню', callback_data='back_to_main_menu')]
    ])

def kb_more_less():
    """Клавиатура для игры Больше/Меньше"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='Больше (4-6)', callback_data='outcome_more'),
            InlineKeyboardButton(text='Меньше (1-3)', callback_data='outcome_less')
        ],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_games')]
    ])

def kb_numbers():
    """Клавиатура для игры Угадай число"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='1', callback_data='outcome_1'),
            InlineKeyboardButton(text='2', callback_data='outcome_2'),
            InlineKeyboardButton(text='3', callback_data='outcome_3')
        ],
        [
            InlineKeyboardButton(text='4', callback_data='outcome_4'),
            InlineKeyboardButton(text='5', callback_data='outcome_5'),
            InlineKeyboardButton(text='6', callback_data='outcome_6')
        ],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_games')]
    ])

def kb_football():
    """Клавиатура для игры Футбол"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='⚽️ Гол', callback_data='outcome_goal'),
            InlineKeyboardButton(text='❌ Мимо', callback_data='outcome_miss')
        ],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_games')]
    ])

def kb_basketball():
    """Клавиатура для игры Баскетбол"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='🏀 Гол', callback_data='outcome_basket_goal'),
            InlineKeyboardButton(text='❌ Мимо', callback_data='outcome_basket_miss')
        ],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_games')]
    ])

def kb_knb():
    """Клавиатура для игры Камень-Ножницы-Бумага"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='✊', callback_data='outcome_rock'),
            InlineKeyboardButton(text='✌️', callback_data='outcome_scissors'),
            InlineKeyboardButton(text='✋', callback_data='outcome_paper')
        ],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_games')]
    ])

def kb_roulette():
    """Клавиатура для игры Рулетка"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='🔴', callback_data='outcome_red'),
            InlineKeyboardButton(text='⚫️', callback_data='outcome_black'),
            InlineKeyboardButton(text='🟢', callback_data='outcome_green')
        ],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_games')]
    ])

def kb_even_odd():
    """Клавиатура для игры Чет/Нечет"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='🔢 Чет', callback_data='outcome_even'),
            InlineKeyboardButton(text='🔣 Нечет', callback_data='outcome_odd')
        ],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_games')]
    ])

def kb_info():
    """Клавиатура для раздела информации"""
    urls = db.get_URL()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔗 Новостной канал', url=urls.get('news', 'https://t.me/noxwat'))],
        [InlineKeyboardButton(text='📞 Поддержка', url=f'https://t.me/{ADMIN_USERNAME[1:]}')],
        [InlineKeyboardButton(text='📋 Правила', url='https://telegra.ph/Pravila-Noxwat-Casino-01-20')],
        [InlineKeyboardButton(text='❓ FAQ', url=urls.get('faq_games', 'https://teletype.in/@oeaow-144350/NJa3KsktZ-'))],
        [InlineKeyboardButton(text='🔙 В меню', callback_data='back_to_main_menu')]
    ])

def kb_referral():
    """Клавиатура для реферальной программы"""
    urls = db.get_URL()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔗 Новостной канал', url=urls.get('news', 'https://t.me/noxwat'))],
        [InlineKeyboardButton(text='🔙 В меню', callback_data='back_to_main_menu')]
    ])

def kb_promo():
    """Клавиатура для промокодов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎫 Активировать промокод', callback_data='activate_promo')],
        [InlineKeyboardButton(text='🔙 В меню', callback_data='back_to_main_menu')]
    ])

def kb_cancel():
    """Кнопка отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='❌ Отмена', callback_data='cancel')]
    ])

def kb_fake_switch(status: bool):
    """Кнопки для переключения фейк игр"""
    if status:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='✅ Включено', callback_data='fake_toggle')],
            [InlineKeyboardButton(text='🔙 Назад', callback_data='back_admin')]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='❌ Выключено', callback_data='fake_toggle')],
            [InlineKeyboardButton(text='🔙 Назад', callback_data='back_admin')]
        ])

def kb_edit_kef(all_kef: dict):
    """Кнопки для редактирования коэффициентов"""
    keyboard = []
    for key, value in all_kef.items():
        keyboard.append([InlineKeyboardButton(text=f'{key}: {value}', callback_data=f'edit_kef_{key}')])
    
    keyboard.append([InlineKeyboardButton(text='🔙 Назад', callback_data='back_admin')])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def kb_urls():
    """Кнопки для редактирования ссылок"""
    urls = db.get_URL()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✏️ Новости', callback_data=f'url_edit_news|{urls.get("news", "")}')],
        [InlineKeyboardButton(text='✏️ Как сделать ставку', callback_data=f'url_edit_info_stavka|{urls.get("info_stavka", "")}')],
        [InlineKeyboardButton(text='✏️ Выплаты', callback_data=f'url_edit_transfer|{urls.get("transfer", "")}')],
        [InlineKeyboardButton(text='✏️ Канал игр', callback_data=f'url_edit_channals|{urls.get("channals", "")}')],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_admin')]
    ])

def kb_broadcast_type():
    """Кнопки выбора типа рассылки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📝 Текст', callback_data='broadcast_text')],
        [InlineKeyboardButton(text='🖼 Текст + Фото', callback_data='broadcast_photo')],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_admin')]
    ])

def kb_broadcast_confirm():
    """Кнопка подтверждения рассылки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📤 Отправить', callback_data='broadcast_send')],
        [InlineKeyboardButton(text='❌ Отмена', callback_data='back_admin')]
    ])

def kb_delete_checks_confirm():
    """Кнопки подтверждения удаления чеков"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Да', callback_data='delete_checks_yes')],
        [InlineKeyboardButton(text='❌ Нет', callback_data='back_admin')]
    ])

def kb_promo_admin():
    """Клавиатура для управления промокодами в админке"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎫 Создать промокод', callback_data='promo_create')],
        [InlineKeyboardButton(text='📊 Статистика промокодов', callback_data='promo_stats')],
        [InlineKeyboardButton(text='📋 Список промокодов', callback_data='promo_list')],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_admin')]
    ])

def send_stavka():
    """Кнопка для канала после ставки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎲 Сделать ставку в боте', url=f"https://t.me/{NICNAME}")]
    ])

def send_okey():
    """Кнопка подтверждения выплаты"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Успешно выплачено', callback_data='okey')]
    ])

def get_cashback(user, amount):
    """Кнопка для получения кэшбэка"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='💸 Забрать кэшбэк', callback_data=f'cashback|{user}|{amount}')]
    ])

def get_fake_cashback(amount, status):
    """Фейковая кнопка кэшбэка"""
    if status == 0:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f'💸 Забрать кэшбэк {amount}$', callback_data='cashback_fake')]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='✅ Кэшбэк получен', callback_data='cashback_fake_okey')]
        ])

def ikb_stop():
    """Кнопка остановки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='❌ Отмена', callback_data='back_admin')]
    ])

def ikb_tip_rassilka():
    """Кнопки выбора типа рассылки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📝 Текст', callback_data='Texts')],
        [InlineKeyboardButton(text='🖼 Текст + Фото', callback_data='photo')],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_admin')]
    ])

def ikb_send_post():
    """Кнопка отправки рассылки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📤 Отправить', callback_data='post_go')],
        [InlineKeyboardButton(text='❌ Отмена', callback_data='back_admin')]
    ])

def ikb_send_post_photo():
    """Кнопка отправки рассылки с фото"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📤 Отправить', callback_data='post_photo_go')],
        [InlineKeyboardButton(text='❌ Отмена', callback_data='back_admin')]
    ])

def kb_answer_delete():
    """Кнопки подтверждения удаления чеков"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Да', callback_data='YesDel')],
        [InlineKeyboardButton(text='❌ Нет', callback_data='back_admin')]
    ])

def keybord_add_balance(url):
    """Кнопка для пополнения баланса казино"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='💳 Оплатить', url=url)],
        [InlineKeyboardButton(text='🔙 Назад', callback_data='back_admin')]
    ])

def kb_viev_post(url, amount):
    """Кнопка для просмотра чека"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f'🎁 Чек на {amount}$', url=url)]
    ])

def kb_send_chek(url):
    """Кнопка для отправки чека"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='💸 Получить выигрыш', url=url)]
    ])