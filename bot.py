from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from hh_api import search_hh
from superjob_api import search_superjob
from config import TELEGRAM_TOKEN
from storage import save_sent_links, get_sent_links

subscribers = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Найти вакансию", callback_data='search')],
        [InlineKeyboardButton("⚙ Настроить поиск", callback_data='settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Выберите действие:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'search':
        context.user_data['page'] = 0
        await start_search(query, context)
    elif query.data == 'next_page':
        context.user_data['page'] += 1
        await start_search(query, context)
    elif query.data == 'settings':
        await show_city_menu(query, context)
    elif query.data.startswith('city_'):
        city_id = int(query.data.split('_')[1])
        context.user_data['city'] = city_id
        await query.edit_message_text(f"Выбран город: {'Москва' if city_id == 1 else 'Санкт-Петербург'}")
        await show_salary_menu(query, context)
    elif query.data.startswith('salary_'):
        salary = int(query.data.split('_')[1])
        context.user_data['salary'] = salary
        await query.edit_message_text(f"Выбрана минимальная зарплата: от {salary}₽")
        await show_schedule_menu(query, context)
    elif query.data.startswith('schedule_'):
        schedule = query.data.split('_')[1]
        context.user_data['schedule'] = schedule
        await query.edit_message_text(f"Выбран тип работы: {schedule.capitalize()}")
        await ask_keyword(query, context)
    elif query.data.startswith('period_'):
        period_days = int(query.data.split('_')[1])
        context.user_data['period'] = period_days
        await query.edit_message_text(f"Выбран период размещения: последние {period_days} дней")
        await query.message.reply_text("✅ Настройки сохранены. Теперь напишите /start для поиска.")

async def show_city_menu(query, context):
    keyboard = [
        [InlineKeyboardButton("📍 Москва", callback_data='city_1')],
        [InlineKeyboardButton("📍 Санкт-Петербург", callback_data='city_2')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите город:", reply_markup=reply_markup)

async def show_salary_menu(query, context):
    keyboard = [
        [InlineKeyboardButton("💵 От 50000₽", callback_data='salary_50000')],
        [InlineKeyboardButton("💵 От 100000₽", callback_data='salary_100000')],
        [InlineKeyboardButton("💵 От 150000₽", callback_data='salary_150000')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Выберите минимальную зарплату:", reply_markup=reply_markup)

async def show_schedule_menu(query, context):
    keyboard = [
        [InlineKeyboardButton("🏡 Удалёнка", callback_data='schedule_remote')],
        [InlineKeyboardButton("🏢 Офис", callback_data='schedule_office')],
        [InlineKeyboardButton("🕐 Гибкий график", callback_data='schedule_flexible')],
        [InlineKeyboardButton("❓ Любой", callback_data='schedule_any')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Выберите формат работы:", reply_markup=reply_markup)

async def ask_keyword(query, context):
    await query.message.reply_text("Введите ключевое слово для поиска (например, Python разработчик):")
    context.user_data['awaiting_keyword'] = True

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_keyword'):
        keyword = update.message.text.strip()
        context.user_data['keyword'] = keyword
        context.user_data['awaiting_keyword'] = False
        keyboard = [
            [InlineKeyboardButton("1 день", callback_data='period_1'), InlineKeyboardButton("3 дня", callback_data='period_3')],
            [InlineKeyboardButton("7 дней", callback_data='period_7'), InlineKeyboardButton("30 дней", callback_data='period_30')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Выберите период размещения вакансий:", reply_markup=reply_markup)

async def start_search(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    city = context.user_data.get('city', 1)
    salary = context.user_data.get('salary', 0)
    keyword = context.user_data.get('keyword', '')
    period = context.user_data.get('period', 30)
    schedule = context.user_data.get('schedule', 'any')
    page = context.user_data.get('page', 0)

    hh_results = search_hh(keyword, city, salary, period, schedule, page)
    sj_results = search_superjob(keyword, city, salary, schedule)

    all_results = hh_results + sj_results
    if all_results:
        response = "\n\n".join(all_results)
        keyboard = [[InlineKeyboardButton("➡ Показать ещё", callback_data='next_page')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update_or_query.message.reply_text(response[:4096], reply_markup=reply_markup)
    else:
        await update_or_query.message.reply_text("Ничего не найдено. Попробуйте изменить параметры поиска.")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    subscribers[user_id] = context.user_data.copy()
    await update.message.reply_text("✅ Вы подписались на рассылку свежих вакансий каждые 2 часа!")

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    subscribers.pop(user_id, None)
    await update.message.reply_text("🚫 Вы отписались от рассылки.")

async def send_updates(context: ContextTypes.DEFAULT_TYPE):
    for user_id, filters in subscribers.items():
        last_sent = get_sent_links(user_id)
        new_results = []
        
        hh_results = search_hh(filters['keyword'], filters['city'], filters['salary'], filters['period'], filters['schedule'], 0)
        sj_results = search_superjob(filters['keyword'], filters['city'], filters['salary'], filters['schedule'])
        
        all_results = hh_results + sj_results
        
        for result in all_results:
            link = result.split(" - ")[-1]
            if link not in last_sent:
                new_results.append(result)
                last_sent.add(link)
        
        save_sent_links(user_id, last_sent)
        
        if new_results:
            response = "\n\n".join(new_results)
            await context.bot.send_message(chat_id=user_id, text=f"Новые вакансии:\n\n{response[:4096]}")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("subscribe", subscribe))
app.add_handler(CommandHandler("unsubscribe", unsubscribe))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

scheduler = BackgroundScheduler()
scheduler.add_job(send_updates, 'interval', hours=2, args=[app])
scheduler.start()

app.run_polling()
