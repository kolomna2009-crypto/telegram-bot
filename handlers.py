import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

import database as db
from keyboards import (
    get_categories_keyboard,
    get_main_menu_keyboard,
    get_send_category_keyboard,
    get_remove_category_keyboard,
)
from states import BroadcastState, GreetingState, AddCategoryState

router = Router()

ADMIN_ID = 5188203773


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ─── /start ───────────────────────────────────────────────────────────────────

@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    if db.is_banned(user_id):
        await message.answer("⛔ Вы заблокированы и не можете использовать этого бота.")
        return

    username = message.from_user.username or "Нет username"
    first_name = message.from_user.first_name or "Пользователь"
    db.add_user(user_id, username, first_name)

    greeting = db.get_greeting()
    subscribed = db.get_user_categories(user_id)

    await message.answer(
        f"👋 Привет, {first_name}!\n\n{greeting}",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin(user_id))
    )
    await message.answer(
        "Выбери категории (✅ — уже подписан):",
        reply_markup=get_categories_keyboard(subscribed)
    )


# ─── /help ────────────────────────────────────────────────────────────────────

@router.message(Command("help"))
async def help_command(message: Message, state: FSMContext):
    await state.clear()
    text = (
        "📖 <b>Доступные команды:</b>\n\n"
        "/start — перезапустить бота\n"
        "/categories — управление подписками\n"
        "/mysubs — мои подписки\n"
        "/help — справка\n"
    )
    if is_admin(message.from_user.id):
        text += (
            "\n<b>Команды администратора:</b>\n"
            "/admin — статистика\n"
            "/send — рассылка (выбор категории)\n"
            "/addcat — добавить категорию\n"
            "/removecat — удалить категорию\n"
            "/setgreeting — изменить приветствие\n"
            "/ban &lt;user_id&gt; — заблокировать пользователя\n"
            "/unban &lt;user_id&gt; — разблокировать пользователя\n"
        )
    await message.answer(text)


# ─── /categories ──────────────────────────────────────────────────────────────

@router.message(Command("categories"))
@router.message(F.text == "📌 Подписки")
async def categories_command(message: Message, state: FSMContext):
    await state.clear()
    if db.is_banned(message.from_user.id):
        return
    subscribed = db.get_user_categories(message.from_user.id)
    await message.answer(
        "Выбери категории (✅ — уже подписан):",
        reply_markup=get_categories_keyboard(subscribed)
    )


# ─── /mysubs ──────────────────────────────────────────────────────────────────

@router.message(Command("mysubs"))
@router.message(F.text == "📋 Мои подписки")
async def mysubs_command(message: Message, state: FSMContext):
    await state.clear()
    if db.is_banned(message.from_user.id):
        return
    subscribed = db.get_user_categories(message.from_user.id)
    if subscribed:
        text = "📋 <b>Твои подписки:</b>\n\n" + "\n".join(f"• {cat}" for cat in subscribed)
    else:
        text = "📭 Ты ни на что не подписан.\n\nНажми «📌 Подписки», чтобы выбрать категории."
    await message.answer(text)


# ─── Subscribe / Unsubscribe callbacks ────────────────────────────────────────

@router.callback_query(F.data.startswith("subscribe_"))
async def subscribe_callback(callback: CallbackQuery):
    category = callback.data.replace("subscribe_", "")
    user_id = callback.from_user.id
    if db.is_banned(user_id):
        await callback.answer("⛔ Вы заблокированы.")
        return
    db.add_category(user_id, category)
    subscribed = db.get_user_categories(user_id)
    await callback.answer(f"✅ Подписан на «{category}»")
    await callback.message.edit_text(
        "Выбери категории (✅ — уже подписан):",
        reply_markup=get_categories_keyboard(subscribed)
    )


@router.callback_query(F.data.startswith("unsubscribe_") & ~F.data.endswith("_all"))
async def unsubscribe_callback(callback: CallbackQuery):
    category = callback.data.replace("unsubscribe_", "")
    user_id = callback.from_user.id
    db.remove_category(user_id, category)
    subscribed = db.get_user_categories(user_id)
    await callback.answer(f"❌ Отписан от «{category}»")
    await callback.message.edit_text(
        "Выбери категории (✅ — уже подписан):",
        reply_markup=get_categories_keyboard(subscribed)
    )


@router.callback_query(F.data == "unsubscribe_all")
async def unsubscribe_all_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.remove_all_categories(user_id)
    await callback.answer("🗑 Отписан от всех категорий")
    await callback.message.edit_text(
        "Выбери категории (✅ — уже подписан):",
        reply_markup=get_categories_keyboard([])
    )


# ─── /admin ───────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
@router.message(F.text == "📊 Статистика")
async def admin_command(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return
    total_users, banned_count, category_stats = db.get_stats()
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Активных пользователей: <b>{total_users}</b>\n"
        f"🚫 Заблокированных: <b>{banned_count}</b>\n\n"
    )
    if category_stats:
        text += "📌 Подписки по категориям:\n"
        for cat, count in category_stats:
            text += f"  • {cat}: <b>{count}</b> чел.\n"
    else:
        text += "Нет подписок\n"
    categories = db.get_categories()
    text += f"\n📁 Категорий: <b>{len(categories)}</b>\n"
    text += "  " + " | ".join(categories)
    await message.answer(text)


# ─── /send — broadcast with category selection ────────────────────────────────

@router.message(Command("send"))
@router.message(F.text == "📢 Рассылка")
async def send_command(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return
    await message.answer(
        "📢 Выбери аудиторию для рассылки:",
        reply_markup=get_send_category_keyboard()
    )
    await state.set_state(BroadcastState.choosing_category)


@router.callback_query(BroadcastState.choosing_category, F.data.startswith("admin_send_"))
async def broadcast_category_chosen(callback: CallbackQuery, state: FSMContext):
    target = callback.data.replace("admin_send_", "")
    await state.update_data(target=target)
    await callback.message.edit_text(
        f"📝 Отправь сообщение для рассылки "
        f"({'всем пользователям' if target == 'ALL' else f'подписчикам «{target}»'}).\n\n"
        "Поддерживается текст, фото, видео, документы и голосовые сообщения.\n\n"
        "Напиши /cancel для отмены."
    )
    await state.set_state(BroadcastState.waiting_for_message)


@router.callback_query(F.data == "admin_cancel")
async def admin_cancel_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отменено.")


@router.message(BroadcastState.waiting_for_message)
async def broadcast_message_received(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Рассылка отменена.")
        return

    data = await state.get_data()
    target = data.get("target", "ALL")
    await state.clear()

    if target == "ALL":
        users = db.get_all_users()
        label = "всем пользователям"
    else:
        users = db.get_users_by_category(target)
        label = f"подписчикам «{target}»"

    if not users:
        await message.answer(f"❌ Нет активных подписчиков ({label}).")
        return

    await message.answer(f"📢 Начинаю рассылку {len(users)} пользователям ({label})...")

    success = 0
    for user_id in users:
        try:
            await message.bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await message.answer(
        f"✅ Рассылка завершена!\n\n"
        f"📤 Успешно: <b>{success}</b> из <b>{len(users)}</b>"
    )


# ─── /setgreeting ─────────────────────────────────────────────────────────────

@router.message(Command("setgreeting"))
async def setgreeting_command(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return
    current = db.get_greeting()
    await message.answer(
        f"✏️ Текущее приветствие:\n\n<i>{current}</i>\n\n"
        "Отправь новый текст приветствия.\n"
        "Напиши /cancel для отмены."
    )
    await state.set_state(GreetingState.waiting_for_text)


@router.message(GreetingState.waiting_for_text)
async def greeting_received(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено.")
        return
    if not message.text:
        await message.answer("⚠️ Приветствие должно быть текстовым. Попробуй ещё раз.")
        return
    db.set_greeting(message.text)
    await state.clear()
    await message.answer(f"✅ Приветствие обновлено:\n\n<i>{message.text}</i>")


# ─── /addcat ──────────────────────────────────────────────────────────────────

@router.message(Command("addcat"))
@router.message(F.text == "⚙️ Категории")
async def addcat_command(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return
    categories = db.get_categories()
    text = (
        "📁 <b>Управление категориями</b>\n\n"
        f"Текущие: {', '.join(categories) if categories else 'нет'}\n\n"
        "Отправь название новой категории для добавления.\n"
        "Или нажми «Удалить категорию» ниже.\n"
        "Напиши /cancel для отмены."
    )
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🗑 Удалить категорию", callback_data="admin_show_removecat"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_msg"))
    await message.answer(text, reply_markup=builder.as_markup())
    await state.set_state(AddCategoryState.waiting_for_name)


@router.callback_query(F.data == "admin_show_removecat")
async def show_removecat(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    categories = db.get_categories()
    if not categories:
        await callback.answer("Нет категорий для удаления")
        return
    await callback.message.edit_text(
        "🗑 Выбери категорию для удаления:",
        reply_markup=get_remove_category_keyboard()
    )


@router.callback_query(F.data.startswith("admin_removecat_"))
async def removecat_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    cat = callback.data.replace("admin_removecat_", "")
    ok = db.remove_category_db(cat)
    if ok:
        await callback.answer(f"✅ Категория «{cat}» удалена")
        await callback.message.edit_text(f"✅ Категория «{cat}» удалена.")
    else:
        await callback.answer("❌ Не найдено")


@router.callback_query(F.data == "admin_cancel_msg")
async def admin_cancel_msg_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отменено.")


@router.message(AddCategoryState.waiting_for_name)
async def addcat_name_received(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено.")
        return
    if not message.text:
        await message.answer("⚠️ Название должно быть текстовым. Попробуй ещё раз.")
        return
    name = message.text.strip()
    ok = db.add_category_db(name)
    await state.clear()
    if ok:
        await message.answer(f"✅ Категория «{name}» добавлена.")
    else:
        await message.answer(f"⚠️ Категория «{name}» уже существует.")


# ─── /removecat ───────────────────────────────────────────────────────────────

@router.message(Command("removecat"))
async def removecat_command(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return
    categories = db.get_categories()
    if not categories:
        await message.answer("❌ Нет категорий для удаления.")
        return
    await message.answer(
        "🗑 Выбери категорию для удаления:",
        reply_markup=get_remove_category_keyboard()
    )


# ─── /ban / /unban ────────────────────────────────────────────────────────────

@router.message(Command("ban"))
async def ban_command(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("⚠️ Использование: /ban <user_id>")
        return
    target_id = int(parts[1])
    if target_id == ADMIN_ID:
        await message.answer("⚠️ Нельзя заблокировать администратора.")
        return
    ok = db.ban_user(target_id)
    if ok:
        await message.answer(f"🚫 Пользователь <code>{target_id}</code> заблокирован.")
        try:
            await message.bot.send_message(target_id, "⛔ Вы были заблокированы администратором.")
        except Exception:
            pass
    else:
        await message.answer(f"⚠️ Пользователь <code>{target_id}</code> не найден в базе.")


@router.message(Command("unban"))
async def unban_command(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("⚠️ Использование: /unban <user_id>")
        return
    target_id = int(parts[1])
    ok = db.unban_user(target_id)
    if ok:
        await message.answer(f"✅ Пользователь <code>{target_id}</code> разблокирован.")
        try:
            await message.bot.send_message(target_id, "✅ Вы были разблокированы администратором.")
        except Exception:
            pass
    else:
        await message.answer(f"⚠️ Пользователь <code>{target_id}</code> не найден в базе.")


# ─── /cancel — universal ──────────────────────────────────────────────────────

@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено.")


# ─── Catch-all: old-style admin broadcast (plain message without state) ───────

@router.message()
async def handle_any_message(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        return  # already handled by FSM

    if db.is_banned(message.from_user.id):
        return

    if not is_admin(message.from_user.id):
        return

    if message.text and message.text.startswith('/'):
        return
