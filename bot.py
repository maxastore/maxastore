import asyncio
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

DB_PATH = Path(os.getenv('DB_PATH', 'maxa_store.db'))
TOKEN = os.getenv('BOT_TOKEN')

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY, username TEXT, created_at TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS support_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER NOT NULL, text TEXT NOT NULL, created_at TEXT NOT NULL)')
    conn.commit()
    return conn

def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📱 Каталог', callback_data='catalog'), InlineKeyboardButton(text='📲 Мои устройства', callback_data='devices')],
        [InlineKeyboardButton(text='💎 Подписка', callback_data='subscription'), InlineKeyboardButton(text='🛟 Поддержка', callback_data='support')],
    ])

def back():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='← Главное меню', callback_data='home')]])

dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    user = message.from_user
    with db() as conn:
        conn.execute('INSERT OR IGNORE INTO users (telegram_id, username, created_at) VALUES (?, ?, ?)', (user.id, user.username, datetime.now(timezone.utc).isoformat()))
    await message.answer('🚀 Добро пожаловать в MAXA Store!\n\nВыберите раздел:', reply_markup=menu())

@dp.callback_query(F.data.in_({'home', 'catalog', 'devices', 'subscription', 'support'}))
async def navigate(call: CallbackQuery):
    screens = {
        'home': ('🚀 MAXA Store\n\nВыберите раздел:', menu()),
        'catalog': ('📱 Каталог\n\nПриложения появятся здесь после добавления администратором и проверки прав на распространение.', back()),
        'devices': ('📲 Мои устройства\n\nУ вас пока нет привязанных устройств.', back()),
        'subscription': ('💎 Подписка\n\nТарифы пока не подключены. Оплата недоступна.', back()),
        'support': ('🛟 Поддержка\n\nЧтобы отправить обращение, напишите /support ваш вопрос.', back()),
    }
    text, keyboard = screens[call.data]
    await call.message.edit_text(text, reply_markup=keyboard)
    await call.answer()

@dp.message(F.text.startswith('/support '))
async def support(message: Message):
    text = message.text[len('/support '):].strip()
    if not text:
        await message.answer('Напишите: /support ваш вопрос')
        return
    with db() as conn:
        conn.execute('INSERT INTO support_requests (telegram_id, text, created_at) VALUES (?, ?, ?)', (message.from_user.id, text, datetime.now(timezone.utc).isoformat()))
    await message.answer('✅ Обращение сохранено. Ответы пока обрабатываются вручную.')

@dp.message()
async def fallback(message: Message):
    await message.answer('Откройте главное меню командой /start или напишите /support ваш вопрос.')

async def main():
    if not TOKEN:
        raise RuntimeError('Set BOT_TOKEN environment variable')
    db().close()
    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
