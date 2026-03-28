from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

import database as db


def get_categories_keyboard(subscribed: list[str] = None):
    if subscribed is None:
        subscribed = []
    categories = db.get_categories()
    builder = InlineKeyboardBuilder()
    for category in categories:
        is_subscribed = category in subscribed
        text = f"✅ {category}" if is_subscribed else f"📌 {category}"
        callback = f"unsubscribe_{category}" if is_subscribed else f"subscribe_{category}"
        builder.add(InlineKeyboardButton(text=text, callback_data=callback))
    if subscribed:
        builder.add(InlineKeyboardButton(text="🗑 Отписаться от всего", callback_data="unsubscribe_all"))
    builder.adjust(2)
    return builder.as_markup()


def get_remove_category_keyboard():
    categories = db.get_categories()
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.add(InlineKeyboardButton(
            text=f"🗑 {category}",
            callback_data=f"admin_removecat_{category}"
        ))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))
    builder.adjust(2)
    return builder.as_markup()


def get_send_category_keyboard():
    categories = db.get_categories()
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.add(InlineKeyboardButton(
            text=f"📢 {category}",
            callback_data=f"admin_send_{category}"
        ))
    builder.add(InlineKeyboardButton(text="📣 Всем", callback_data="admin_send_ALL"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))
    builder.adjust(2)
    return builder.as_markup()


def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📌 Подписки"))
    builder.add(KeyboardButton(text="📋 Мои подписки"))
    if is_admin:
        builder.add(KeyboardButton(text="📊 Статистика"))
        builder.add(KeyboardButton(text="📢 Рассылка"))
        builder.add(KeyboardButton(text="⚙️ Категории"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)
