import os
import sys
from datetime import datetime
from html import escape

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

BOT_TOKEN = "8314361205:AAFHRavPe3COjAlstChP84F9BH2db934k7c"
WEBHOOK_HOST = "https://mjr-zg8b.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = "WEBHOOK_SECRET", "major-s9ejd-qUj6w-jEvO4-cK03Q"
ADMIN_ID = ["6025818386"]
CHAT_ID = -1004415936222
PORT = ("PORT", 8080)

WELCOME_TEXT = (
    '<tg-emoji emoji-id="5251203410396458957">🛡</tg-emoji>'
    "<i> Добро пожаловать в <b>Major Spam Bot</b>\n"
    '<tg-emoji emoji-id="5443038326535759644">💬</tg-emoji> '
    "Бот создан для автоматизации чата @chatmjr</i>"
)

ASK_TEXT = (
    '<tg-emoji emoji-id="5143349926826083602">🚗</tg-emoji>'
    "<i> Для подтверждения спам блока, отправьте скриншот от @SpamBot</i>"
)

ACCEPTED_TEXT = (
    '<tg-emoji emoji-id="5251203410396458957">🛡</tg-emoji>'
    "<b> Заявка будет принята и обработана в ближайшее время!</b>"
)

STATUSES = {
    "pending": "На рассмотрении",
    "approved": "Одобрена",
    "rejected": "Отклонена",
}

requests_db = {}
counter = {"id": 0}


class Form(StatesGroup):
    waiting_photo = State()


router = Router()


def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="получить сб",
                    callback_data="get_sb",
                    style="success",
                    icon_custom_emoji_id="5416081784641168838",
                ),
                InlineKeyboardButton(
                    text="Иной вопрос",
                    callback_data="other",
                    style="danger",
                    icon_custom_emoji_id="5436113877181941026",
                ),
            ]
        ]
    )


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back", style="primary")]
        ]
    )


def my_requests_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="мои обращения",
                    callback_data="my_requests",
                    style="primary",
                    icon_custom_emoji_id="5197269100878907942",
                )
            ]
        ]
    )


def admin_kb(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="да", callback_data=f"dec:yes:{req_id}"),
                InlineKeyboardButton(text="нет", callback_data=f"dec:no:{req_id}"),
            ]
        ]
    )


def who(user) -> str:
    if user.username:
        return f"@{user.username}"
    return f'<a href="tg://user?id={user.id}">{user.id}</a>'


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer('<tg-emoji emoji-id="5424972470023104089">🔥</tg-emoji>')
    await message.answer(WELCOME_TEXT, reply_markup=main_kb())


@router.callback_query(F.data == "get_sb")
async def get_sb(call: CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_photo)
    await call.message.edit_text(ASK_TEXT, reply_markup=back_kb())
    await call.answer()


@router.callback_query(F.data == "back")
async def back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(WELCOME_TEXT, reply_markup=main_kb())
    await call.answer()


@router.callback_query(F.data == "other")
async def other(call: CallbackQuery):
    await call.answer("Раздел в разработке", show_alert=True)


@router.message(Form.waiting_photo, F.photo)
async def got_photo(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    counter["id"] += 1
    req_id = counter["id"]
    date = datetime.now().strftime("%d.%m.%Y %H:%M")
    requests_db[req_id] = {
        "user_id": message.from_user.id,
        "date": date,
        "status": "pending",
    }
    await message.answer(ACCEPTED_TEXT, reply_markup=my_requests_kb())
    caption = (
        "<b>Новая заявка!</b>\n"
        f"Кто: {who(message.from_user)}\n"
        f"Дата: {date}"
    )
    await bot.send_photo(
        ADMIN_ID,
        photo=message.photo[-1].file_id,
        caption=caption,
        reply_markup=admin_kb(req_id),
    )


@router.message(Form.waiting_photo)
async def not_photo(message: Message):
    await message.answer("Отправьте скриншот фото-сообщением.", reply_markup=back_kb())


@router.callback_query(F.data == "my_requests")
async def my_requests(call: CallbackQuery):
    items = [
        (rid, r) for rid, r in requests_db.items() if r["user_id"] == call.from_user.id
    ]
    if not items:
        text = "<b>Мои обращения</b>\n\nУ вас пока нет обращений."
    else:
        lines = [
            f"№{rid} • {r['date']} • {STATUSES[r['status']]}" for rid, r in items[-10:]
        ]
        text = "<b>Мои обращения</b>\n\n" + "\n".join(lines)
    await call.message.answer(text, reply_markup=back_kb())
    await call.answer()


@router.callback_query(F.data.startswith("dec:"))
async def decision(call: CallbackQuery, bot: Bot):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Нет доступа", show_alert=True)
        return
    _, action, rid = call.data.split(":")
    req = requests_db.get(int(rid))
    if not req:
        await call.answer("Заявка не найдена", show_alert=True)
        return
    if req["status"] != "pending":
        await call.answer("Уже обработана", show_alert=True)
        return

    user_id = req["user_id"]

    if action == "yes":
        try:
            await bot.promote_chat_member(
                chat_id=CHAT_ID,
                user_id=user_id,
                is_anonymous=False,
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=True,
                can_post_messages=False,
                can_edit_messages=False,
                can_pin_messages=False,
                can_manage_topics=False,
            )
            await bot.set_chat_administrator_custom_title(
                chat_id=CHAT_ID, user_id=user_id, custom_title="сб"
            )
        except Exception as e:
            await call.answer(f"Ошибка: {str(e)[:150]}", show_alert=True)
            return
        req["status"] = "approved"
        result = "✅ Одобрено"
        user_text = (
            '<tg-emoji emoji-id="5251203410396458957">🛡</tg-emoji>'
            "<b> Ваша заявка одобрена, тег «сб» выдан в чате!</b>"
        )
    else:
        req["status"] = "rejected"
        result = "❌ Отклонено"
        user_text = (
            '<tg-emoji emoji-id="5251203410396458957">🛡</tg-emoji>'
            "<b> Ваша заявка отклонена.</b>"
        )

    await call.message.edit_caption(
        caption=f"{call.message.html_text}\n\n<b>{result}</b>", reply_markup=None
    )
    try:
        await bot.send_message(user_id, user_text, reply_markup=my_requests_kb())
    except Exception:
        pass
    await call.answer(result)



async def on_startup(bot: Bot):
    await bot.set_webhook(
        f"{WEBHOOK_HOST}{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET,
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()


bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(router)
dp.startup.register(on_startup)
dp.shutdown.register(on_shutdown)

app = web.Application()
SimpleRequestHandler(
    dispatcher=dp, bot=bot, secret_token=WEBHOOK_SECRET
).register(app, path=WEBHOOK_PATH)
setup_application(app, dp, bot=bot)


if __name__ == "__main__":
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "gunicorn",
            "main:app",
            "-k",
            "aiohttp.GunicornWebWorker",
            "-b",
            f"0.0.0.0:{PORT}",
            "-w",
            "1",
            "--timeout",
            "60",
            "--access-logfile",
            "-",
        ],
    )
