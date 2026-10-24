import asyncio
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

DB_PATH = Path(os.getenv('DB_PATH', 'maxa_store.db'))
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = {389330780}


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY, username TEXT, created_at TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS support_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER NOT NULL, text TEXT NOT NULL, created_at TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS apps (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT "", url TEXT NOT NULL, created_at TEXT NOT NULL)')
    conn.commit()
    return conn


def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📱 Каталог', callback_data='catalog'), InlineKeyboardButton(text='📲 Мои устройства', callback_data='devices')],
        [InlineKeyboardButton(text='💎 Подписка', callback_data='subscription'), InlineKeyboardButton(text='🛟 Поддержка', callback_data='support')],
    ])


def back():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='← Главное меню', callback_data='home')]])


def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📊 Статистика', callback_data='adm_stats'), InlineKeyboardButton(text='📱 Каталог', callback_data='adm_apps')],
        [InlineKeyboardButton(text='🛟 Обращения', callback_data='adm_support'), InlineKeyboardButton(text='👥 Пользователи', callback_data='adm_users')],
        [InlineKeyboardButton(text='← Главное меню', callback_data='home')],
    ])


def is_admin(user):
    return bool(user and user.id in ADMIN_IDS)


def now():
    return datetime.now(timezone.utc).isoformat()


def catalog_text():
    with db() as conn:
        apps = conn.execute('SELECT id, name, description, url FROM apps ORDER BY id DESC LIMIT 30').fetchall()
    if not apps:
        return '📱 Каталог\n\nПриложения появятся здесь после добавления администратором и проверки прав на распространение.'
    return '📱 Каталог\n\n' + '\n\n'.join(f'#{i} {name}\n{desc}\n{url}' for i, name, desc, url in apps)


dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    user = message.from_user
    with db() as conn:
        conn.execute('INSERT OR IGNORE INTO users (telegram_id, username, created_at) VALUES (?, ?, ?)', (user.id, user.username, now()))
    await message.answer('🚀 Добро пожаловать в MAXA Store!\n\nВыберите раздел:', reply_markup=menu())


@dp.message(Command('admin'))
async def admin(message: Message):
    if not is_admin(message.from_user):
        await message.answer('⛔ Доступ запрещён.')
        return
    await message.answer('⚙️ Панель администратора MAXA Store\n\nДобавить приложение: /addapp Название | Описание | https://example.com\nУдалить: /delapp ID', reply_markup=admin_menu())


@dp.message(Command('addapp'))
async def add_app(message: Message):
    if not is_admin(message.from_user):
        await message.answer('⛔ Доступ запрещён.')
        return
    parts = (message.text or '').partition(' ')[2].split('|')
    if len(parts) != 3:
        await message.answer('Формат: /addapp Название | Описание | https://example.com')
        return
    name, description, url = (p.strip() for p in parts)
    if not name or len(name) > 100 or len(description) > 500 or not url.startswith(('https://', 'http://')) or len(url) > 1000:
        await message.answer('Проверьте название, описание и ссылку (http/https).')
        return
    with db() as conn:
        cursor = conn.execute('INSERT INTO apps (name, description, url, created_at) VALUES (?, ?, ?, ?)', (name, description, url, now()))
        app_id = cursor.lastrowid
    await message.answer(f'✅ Приложение добавлено в каталог. ID: {app_id}')


@dp.message(Command('delapp'))
async def delete_app(message: Message):
    if not is_admin(message.from_user):
        await message.answer('⛔ Доступ запрещён.')
        return
    arg = (message.text or '').partition(' ')[2].strip()
    if not arg.isdecimal():
        await message.answer('Формат: /delapp ID')
        return
    with db() as conn:
        result = conn.execute('DELETE FROM apps WHERE id = ?', (int(arg),))
    await message.answer('✅ Удалено.' if result.rowcount else 'Приложение не найдено.')


@dp.callback_query(F.data.in_({'adm_stats', 'adm_apps', 'adm_support', 'adm_users'}))
async def admin_nav(call: CallbackQuery):
    if not is_admin(call.from_user):
        await call.answer('Доступ запрещён', show_alert=True)
        return
    with db() as conn:
        if call.data == 'adm_stats':
            users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            apps = conn.execute('SELECT COUNT(*) FROM apps').fetchone()[0]
            requests = conn.execute('SELECT COUNT(*) FROM support_requests').fetchone()[0]
            text = f'📊 Статистика\n\nПользователей: {users}\nПриложений: {apps}\nОбращений: {requests}'
        elif call.data == 'adm_apps':
            apps = conn.execute('SELECT id, name FROM apps ORDER BY id DESC LIMIT 20').fetchall()
            text = '📱 Приложения\n\n' + ('\n'.join(f'#{i} — {name}' for i, name in apps) if apps else 'Каталог пуст.') + '\n\nДобавить: /addapp Название | Описание | https://example.com\nУдалить: /delapp ID'
        elif call.data == 'adm_support':
            requests = conn.execute('SELECT id, telegram_id, text FROM support_requests ORDER BY id DESC LIMIT 10').fetchall()
            text = '🛟 Последние обращения\n\n' + ('\n\n'.join(f'#{i} от {uid}: {body[:250]}' for i, uid, body in requests) if requests else 'Обращений пока нет.')
        else:
            users = conn.execute('SELECT telegram_id, username FROM users ORDER BY created_at DESC LIMIT 20').fetchall()
            text = '👥 Последние пользователи\n\n' + ('\n'.join(f'{uid} — @{username}' if username else str(uid) for uid, username in users) if users else 'Пользователей пока нет.')
    await call.message.edit_text(text[:3900], reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='← Админ-панель', callback_data='adm_home')]]))
    await call.answer()


@dp.callback_query(F.data == 'adm_home')
async def admin_home(call: CallbackQuery):
    if not is_admin(call.from_user):
        await call.answer('Доступ запрещён', show_alert=True)
        return
    await call.message.edit_text('⚙️ Панель администратора MAXA Store', reply_markup=admin_menu())
    await call.answer()


@dp.callback_query(F.data.in_({'home', 'catalog', 'devices', 'subscription', 'support'}))
async def navigate(call: CallbackQuery):
    screens = {
        'home': ('🚀 MAXA Store\n\nВыберите раздел:', menu()),
        'catalog': (catalog_text(), back()),
        'devices': ('📲 Мои устройства\n\nУ вас пока нет привязанных устройств.', back()),
        'subscription': ('💎 Подписка\n\nТарифы пока не подключены. Оплата недоступна.', back()),
        'support': ('🛟 Поддержка\n\nЧтобы отправить обращение, напишите /support ваш вопрос.', back()),
    }
    text, keyboard = screens[call.data]
    await call.message.edit_text(text[:3900], reply_markup=keyboard)
    await call.answer()


@dp.message(Command('support'))
async def support(message: Message):
    text = (message.text or '').partition(' ')[2].strip()
    if not text:
        await message.answer('Напишите: /support ваш вопрос')
        return
    with db() as conn:
        conn.execute('INSERT INTO support_requests (telegram_id, text, created_at) VALUES (?, ?, ?)', (message.from_user.id, text, now()))
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
