import asyncio
import logging
import secrets
import string

import aiosqlite
from aiohttp import web

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery,
)
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

BOT_TOKEN = "8861223578:AAEPy9SNIVtHHTiOvWJqjRbnkm4g_q_oLsg"
CHANNEL_ID = "@mjrstars"
CHANNEL_URL = "https://t.me/mjrstars"

DB_PATH = "bot.db"
HASH_ALPHABET = string.ascii_lowercase + string.digits

WEBHOOK_HOST = "https://mjrstar.n.onjrnm.vip"
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = "замени-на-случайную-строку"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = 443

router = Router()


def generate_payload() -> str:
    return "".join(secrets.choice(HASH_ALPHABET) for _ in range(8))


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS balances ("
            "user_id INTEGER PRIMARY KEY, "
            "amount INTEGER NOT NULL DEFAULT 0"
            ")"
        )
        await db.commit()


async def get_balance(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT amount FROM balances WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def add_balance(user_id: int, amount: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO balances (user_id, amount) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET amount = amount + ?",
            (user_id, amount, amount),
        )
        await db.commit()
        async with db.execute(
            "SELECT amount FROM balances WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else amount


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status not in (
            ChatMemberStatus.LEFT,
            ChatMemberStatus.KICKED,
        )
    except Exception:
        return False


def user_link(user) -> str:
    return f'<a href="tg://user?id={user.id}">{user.full_name}</a>'


def check_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Канал",
                    url=CHANNEL_URL,
                    icon_custom_emoji_id="5271604874419647061",
                    style="primary",
                ),
                InlineKeyboardButton(
                    text="Проверить",
                    callback_data="check_sub",
                    icon_custom_emoji_id="5416081784641168838",
                    style="success",
                ),
            ]
        ]
    )


def balance_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Пополнить",
                    callback_data="balance_topup",
                    icon_custom_emoji_id="4988289890769699938",
                    style="success",
                ),
                InlineKeyboardButton(
                    text="Вывод",
                    callback_data="balance_withdraw",
                    icon_custom_emoji_id="4983748881977181112",
                    style="success",
                ),
            ]
        ]
    )


def topup_markup() -> InlineKeyboardMarkup:
    amounts = ["5", "10", "15", "25", "50", "100", "250", "500", "1000", "2000", "10000"]
    rows = [amounts[i:i + 3] for i in range(0, len(amounts), 3)]
    keyboard = [
        [
            InlineKeyboardButton(
                text=amt,
                callback_data=f"topup_{amt}",
                icon_custom_emoji_id="5954135079662916434",
            )
            for amt in row
        ]
        for row in rows
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def soon_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Channel",
                    url=CHANNEL_URL,
                    icon_custom_emoji_id="5008457489528652800",
                    style="primary",
                ),
            ]
        ]
    )


def soon_text() -> str:
    return (
        '<tg-emoji emoji-id="5051114649445991756">🔠</tg-emoji>'
        '<tg-emoji emoji-id="5050987303665665245">🔠</tg-emoji>'
        '<tg-emoji emoji-id="5053271642151584876">🔠</tg-emoji>'
        '<tg-emoji emoji-id="5051108567772300271">🔠</tg-emoji>'
        '<tg-emoji emoji-id="5053572629164721435">🔠</tg-emoji>'
        '<tg-emoji emoji-id="5019824691708167395">⭐️</tg-emoji>\n\n'
        '<b><tg-emoji emoji-id="5210956306952758910">👀</tg-emoji> Soon! Follow the news in the channel</b>'
    )


@router.message(F.text == "б")
async def cmd_balance(message: Message) -> None:
    if message.chat.type != "private":
        return
    balance = await get_balance(message.from_user.id)
    await message.answer(
        f"<b>Ваш баланс:</b> <blockquote>{balance}⭐️</blockquote>",
        reply_markup=balance_markup(),
    )


@router.callback_query(F.data == "balance_topup")
async def on_topup(call: CallbackQuery) -> None:
    await call.message.edit_text(
        '<b><tg-emoji emoji-id="5053473385355412667">⭐️</tg-emoji> Пополнение</b>\n\n'
        '<i><b>Выберите</b> или <b>введите</b> сумму пополнения в '
        '<tg-emoji emoji-id="5030538831225422917">⬆️</tg-emoji></i>',
        reply_markup=topup_markup(),
    )
    await call.answer()


@router.callback_query(F.data == "balance_withdraw")
async def on_withdraw(call: CallbackQuery) -> None:
    await call.message.edit_text("Soon...")
    await call.answer()


@router.callback_query(F.data.startswith("topup_"))
async def on_topup_amount(call: CallbackQuery) -> None:
    amount = int(call.data.split("_", 1)[1])
    payload = generate_payload()
    await call.message.answer_invoice(
        title=f"Пополнение #{payload}",
        description=f"Пополнение баланса на {amount}⭐️",
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Пополнение баланса", amount=amount)],
    )
    await call.answer()


@router.message(F.text.regexp(r"^\d+$"))
async def on_topup_custom(message: Message) -> None:
    amount = int(message.text)
    if amount <= 0:
        return
    payload = generate_payload()
    await message.answer_invoice(
        title=f"Пополнение #{payload}",
        description=f"Пополнение баланса на {amount}⭐️",
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Пополнение баланса", amount=amount)],
    )


@router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message) -> None:
    amount = message.successful_payment.total_amount
    await add_balance(message.from_user.id, amount)
    await message.answer(
        f'<i><tg-emoji emoji-id="4976909296882156783">🪙</tg-emoji>'
        f'{user_link(message.from_user)}, вы <b>успешно</b> пополнили баланс на {amount}'
        f'<tg-emoji emoji-id="5954135079662916434">⭐️</tg-emoji></i>'
    )


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot) -> None:
    if await is_subscribed(bot, message.from_user.id):
        await message.answer(soon_text(), reply_markup=soon_markup())
        return

    await message.answer(
        '<tg-emoji emoji-id="5228947933545635555">😫</tg-emoji>'
        f'<b>{user_link(message.from_user)}, вы не подписаны на обязательные каналы!</b>',
        reply_markup=check_markup(),
    )


@router.callback_query(F.data == "check_sub")
async def on_check_sub(call: CallbackQuery, bot: Bot) -> None:
    if await is_subscribed(bot, call.from_user.id):
        await call.message.delete()
        await call.answer()
        return

    await call.message.edit_text(
        '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji>'
        f'<b>{user_link(call.from_user)}, вы всё ещё не подписаны!</b>',
        reply_markup=check_markup(),
    )
    await call.answer()


@router.message()
async def any_message(message: Message) -> None:
    await message.answer(soon_text(), reply_markup=soon_markup())


async def on_startup(bot: Bot) -> None:
    await init_db()
    await bot.set_webhook(
        url=f"{WEBHOOK_HOST}{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True,
    )


async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook()


def main() -> None:
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    webhook_handler.register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()