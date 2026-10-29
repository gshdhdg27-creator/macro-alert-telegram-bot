from typing import Dict

TEXTS: Dict[str, Dict[str, str]] = {
    "ru": {
        "welcome": (
            "👋 Привет! Я твой персональный бот макроэкономических алертов.\n\n"
            "Я слежу за экономическим календарём (ФРС, CPI, NFP, ЕЦБ…) "
            "и срочными новостями по выбранным активам.\n\n"
            "Выбери раздел в меню ниже."
        ),
        "main_menu": "📋 Главное меню",
        "calendar": "📅 Экономический календарь",
        "settings": "⚙️ Настройки алертов",
        "history": "🗂 История алертов",
        "quiet_on": "🔇 Тихий режим ВКЛ",
        "quiet_off": "🔔 Тихий режим ВЫКЛ",
        "lang_switched": "Язык переключён на Русский",
        "choose_asset": "Выбери актив для просмотра / подписки:",
        "subscribed": "✅ Подписка на {asset} включена",
        "unsubscribed": "❌ Подписка на {asset} отключена",
        "only_high": "Только High Impact",
        "timezone": "Часовой пояс",
        "back": "◀️ Назад",
        "today": "Сегодня",
        "tomorrow": "Завтра",
        "week": "Неделя",
        "no_events": "На выбранный период важных событий нет.",
        "loading": "⏳ Загружаю…",
        "error": "Произошла ошибка. Попробуй позже.",
        "quiet_enabled": "🔇 Тихий режим включён. Уведомления приостановлены.",
        "quiet_disabled": "🔔 Тихий режим выключен. Уведомления снова активны.",
    },
    "en": {
        "welcome": (
            "👋 Hi! I'm your personal macro alert bot.\n\n"
            "I monitor the economic calendar (Fed, CPI, NFP, ECB…) "
            "and breaking news on selected assets.\n\n"
            "Choose a section from the menu below."
        ),
        "main_menu": "📋 Main menu",
        "calendar": "📅 Economic Calendar",
        "settings": "⚙️ Alert Settings",
        "history": "🗂 Alert History",
        "quiet_on": "🔇 Quiet Mode ON",
        "quiet_off": "🔔 Quiet Mode OFF",
        "lang_switched": "Language switched to English",
        "choose_asset": "Choose an asset to view / subscribe:",
        "subscribed": "✅ Subscribed to {asset}",
        "unsubscribed": "❌ Unsubscribed from {asset}",
        "only_high": "High Impact only",
        "timezone": "Timezone",
        "back": "◀️ Back",
        "today": "Today",
        "tomorrow": "Tomorrow",
        "week": "Week",
        "no_events": "No important events for the selected period.",
        "loading": "⏳ Loading…",
        "error": "An error occurred. Please try again later.",
        "quiet_enabled": "🔇 Quiet mode enabled. Notifications paused.",
        "quiet_disabled": "🔔 Quiet mode disabled. Notifications active again.",
    },
}


def t(key: str, lang: str = "ru", **kwargs) -> str:
    text = TEXTS.get(lang, TEXTS["ru"]).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
