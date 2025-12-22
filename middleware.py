# middleware.py
from aiogram import BaseMiddleware
from aiogram.types import Message
from config import ADMIN

class IsAdmin(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        if str(event.from_user.id) in ADMIN:
            return await handler(event, data)
        # Не блокируем, просто не показываем кнопку админки
        return

class LoggingUsers(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # Ваша существующая логика логирования
        return await handler(event, data)