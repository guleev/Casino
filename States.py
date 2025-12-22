from aiogram.fsm.state import StatesGroup, State


class Captcha_users(StatesGroup):
    status = State()


class UserStats(StatesGroup):
    user_id = State()


class AddBalanceCasino(StatesGroup):
    amount = State()


class NewKefGame(StatesGroup):
    value = State()


#Текст
class AdminText(StatesGroup):
    text = State()
    send = State()


class AdminPhotoText(StatesGroup):
    text = State()
    photo = State()
    send_photo = State()


class NewUrlAdmin(StatesGroup):
    url = State()
