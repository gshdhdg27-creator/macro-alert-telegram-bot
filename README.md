# 📊 Macro Alert Telegram Bot

Персональный Telegram-бот для мониторинга макроэкономических новостей, экономического календаря (ФРС, CPI, NFP, ЕЦБ и др.) и срочных инфоповодов по ключевым активам с AI-фильтрацией и мгновенными алертами.

**Стек:** Python 3.11 · aiogram 3.x · SQLite · APScheduler · OpenAI · Docker

---

## Возможности

- 13 активов + системные разделы (календарь, настройки)
- Авто-алерты за 15 мин до High Impact событий
- Мгновенный Actual vs Forecast
- Breaking news с AI-фильтрацией (важность + теги + summary на RU/EN)
- Гибкие подписки, только High Impact, тихий режим
- История алертов
- Двуязычный интерфейс (RU / EN)
- Легко расширяется новыми активами (просто конфиг)

---

## Быстрый старт (на Mac Station)

### 1. Клонировать
```bash
git clone https://github.com/gshdhdg27-creator/macro-alert-telegram-bot.git
cd macro-alert-telegram-bot
```

### 2. Создать `.env`
```bash
cp .env.example .env
```

Заполни:
```env
BOT_TOKEN=123456:ABC-DEF...          # от @BotFather
ADMIN_ID=123456789                   # твой Telegram ID (@userinfobot)
OPENAI_API_KEY=sk-...                # для AI-фильтрации (рекомендуется)
FMP_API_KEY=                         # опционально (FinancialModelingPrep)
DEFAULT_TIMEZONE=Europe/Moscow
```

### 3. Запуск через Docker (рекомендуется)
```bash
docker compose up -d --build
```

Логи:
```bash
docker compose logs -f bot
```

### 4. Или без Docker
```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
python -m bot.main
```

---

## Структура проекта

```
bot/
├── main.py                 # Точка входа + scheduler
├── config.py               # Настройки + ASSETS (легко добавлять новые)
├── handlers/               # Команды и кнопки
├── keyboards/              # Reply + Inline клавиатуры
├── models/                 # SQLAlchemy (UserSettings, AlertHistory)
├── services/               # Календарь, новости, AI, алерты
└── utils/i18n.py           # Переводы
```

---

## Как добавить новый актив

Открой `bot/config.py` → словарь `ASSETS` и добавь новый ключ:

```python
"new_asset": {
    "emoji": "🔥",
    "name_ru": "Новый актив",
    "name_en": "New Asset",
    "tags": ["NEW", "TAG"],
    "keywords": ["keyword1", "keyword2"],
},
```

Готово — меню и фильтрация подхватят автоматически.

---

## Источники данных

- **Календарь**: FinancialModelingPrep (если ключ) + fallback
- **Новости**: Reuters, Bloomberg, CoinDesk, Fed RSS + AI-фильтр
- **AI**: GPT-4o-mini (можно заменить на другой)

Задержки алертов: 5–10 секунд (зависит от источника).

---

## Деплой

Основной режим — **Docker на твоём Mac Station** (или любом сервере).

Vercel подключён к репозиторию для возможного будущего webhook-режима / админ-панели, но текущий бот использует long-polling + scheduler, поэтому основной запуск — локально/на Mac.

---

## Лицензия

Private — только для владельца репозитория.
