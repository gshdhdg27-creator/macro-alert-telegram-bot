from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select, desc

from bot.config import get_settings
from bot.models.db import AlertHistory, UserSettings, async_session
from bot.utils.i18n import t

router = Router(name="history")
settings = get_settings()


@router.message(F.text.func(lambda t: t and ("история" in t.lower() or "history" in t.lower() or "🗂" in t)))
async def show_history(message: Message):
    if message.from_user.id != settings.admin_id:
        return

    async with async_session() as session:
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        lang = user.language if user else "ru"

        result = await session.execute(
            select(AlertHistory)
            .where(AlertHistory.user_id == message.from_user.id)
            .order_by(desc(AlertHistory.created_at))
            .limit(15)
        )
        rows = result.scalars().all()

    if not rows:
        await message.answer("История алертов пока пуста." if lang == "ru" else "Alert history is empty.")
        return

    lines = []
    for r in rows:
        dt = r.created_at.strftime("%d.%m %H:%M") if r.created_at else ""
        lines.append(f"• <b>{dt}</b> [{r.importance}] {r.title[:80]}")

    text = ("🗂 <b>Последние алерты</b>\n\n" if lang == "ru" else "🗂 <b>Recent alerts</b>\n\n") + "\n".join(lines)
    await message.answer(text, parse_mode="HTML")
