from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler, ConversationHandler
)
import urllib3
import logging
import requests
import pandas as pd

Token = "8886339057:AAFn5MI96NuNSXMIFEfHzkSyMloVi0DAsB4"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

SYMBOL, CATEGORY, AUDITED, DATE_START, DATE_END = range(5)

async def codal_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["codal_params"] = {}  

    await query.edit_message_text("نام نماد را وارد کنید (برای مثال وبملت):")
    return SYMBOL

async def get_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["codal_params"]["l18"] = text        

    await update.message.reply_text("دسته‌بندی مورد نظر را وارد کنید (عددی بین ۱ تا ۱۰):")
    return CATEGORY

async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["codal_params"]["category"] = text   
    keyboard = [
        [InlineKeyboardButton("بله", callback_data="true"),
         InlineKeyboardButton("خیر", callback_data="false")]
    ]
    await update.message.reply_text(
        "آیا گزارش حسابرسی‌شده باشد؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return AUDITED

async def get_audited(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["codal_params"]["audited"] = query.data

    await query.edit_message_text("تاریخ شروع را وارد کنید (مثلا 1403-01-01):")
    return DATE_START

async def get_date_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["codal_params"]["date_start"] = text  
    await update.message.reply_text("تاریخ پایان را وارد کنید:")
    return DATE_END

async def get_date_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["codal_params"]["date_end"] = text   

    # All data collected 
    params = context.user_data["codal_params"]

    url = (
        f"https://Api.BrsApi.ir/Codal/Announcement.php?"
        f"key=BJVE8WJwRMVX7RvpkUnE7q1mrEkv93Qh"
        f"&l18={params['l18']}"
        f"&category={params['category']}"
        f"&audited={params['audited']}"
        f"&date_start={params['date_start']}"
        f"&date_end={params['date_end']}"
        f"&page=1"
    )

    logger.info(f"Codal URL: {url}")
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        print(data)
        if not data:
            await update.message.reply_text("!هیچ اطلاعیه ای  پیدا نشد")
            return ConversationHandler.END
        
        keyboard=[]
        for item in data[:10]:
            title = item.get("title", "گزارش")
            link = item.get("url")
            keyboard.append([InlineKeyboardButton(f"{title}",url=link)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"✅ {len(data)} اطلاعیه پیدا شد:",
            reply_markup=reply_markup
        )

        await update.message.reply_text(f"✅ اطلاعات دریافت شد!\n\n{response.text[:500]}")

    else:
        logger.error(f"❌ Codal error: {response.status_code}")
        await update.message.reply_text("❌ خطا در دریافت اطلاعات")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات لغو شد.")
    return ConversationHandler.END


codal_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(codal_start, pattern="^codal$")],
    states={
        SYMBOL:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_symbol)],
        CATEGORY:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_category)],
        AUDITED:    [CallbackQueryHandler(get_audited)],
        DATE_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date_start)],
        DATE_END:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date_end)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],   # ✅ always have an escape
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 تمام نماد های بورس", callback_data="download")],
        [InlineKeyboardButton("📋 اطلاعیه‌های کدال", callback_data="codal")],
        [InlineKeyboardButton("نماد های برتر", callback_data="thebest")]   
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    user = update.effective_chat
    logger.info(f"User {user.first_name}, id:{user.id} started chatting...")
    await update.message.reply_text("یک گزینه را انتخاب کنید:", reply_markup=reply_markup)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()   

    if query.data == "download":
        url = "https://Api.BrsApi.ir/Tsetmc/AllSymbols.php?key=BJVE8WJwRMVX7RvpkUnE7q1mrEkv93Qh"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/106.0.0.0",
            "Accept": "application/json, text/plain, */*"
        }
        response = requests.get(url, headers=headers , verify=False)

        if response.status_code == 200:
            data = response.json()
            filtered = [
                {
                    "زمان آخرین اطلاعات": item.get("time"),
                    "نماد": item.get("l18"),
                    "نام شرکت": item.get("l30"),
                    "تعداد سهم": item.get("z"),
                    "حجم مبنا": item.get("bvol"),
                    "EPS": item.get("eps"),
                    "P/E": item.get("pe"),
                    "کمترین قیمت": item.get("tmin"),
                    "بیشترین قیمت": item.get("tmax"),
                    "اولین قیمت": item.get("pf"),
                    "آخرین قیمت": item.get("pl"),
                    "درصد تغییر آخرین قیمت": item.get("plp"),
                    "قیمت پایانی": item.get("pc"),
                    "درصد تغییر قیمت پایانی": item.get("pcp"),
                    "حجم معاملات": item.get("tvol"),
                    "ارزش معاملات": item.get("tval"),
                    "تعداد معاملات": item.get("tno"),
                    "تعداد خریدار حقیقی": item.get("Buy_CountI"),
                    "تعداد خریدار حقوقی": item.get("Buy_CountN"),
                    "تعداد فروشنده حقیقی": item.get("Sell_CountI"),
                    "تعداد فروشنده حقوقی": item.get("Sell_CountN"),
                }
                for item in data
            ]
            df = pd.DataFrame(filtered)
            df.to_excel("symbols.xlsx", index=False)
            logger.info("symbols.xlsx saved!")

            with open("symbols.xlsx", "rb") as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename="symbols.xlsx",
                    caption="خدمت شما"
                )
            logger.info(f"Excel sent to user {query.from_user.first_name}")
        else:
            logger.error(f"❌ Error: {response.status_code}")
            await query.edit_message_text("❌ خطا در دریافت اطلاعات")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_chat
    text = update.message.text
    logger.info(f"User {user.first_name} sent: {text}")
    await update.message.reply_text(text)

app = ApplicationBuilder().token(Token).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(codal_conv)                                   
app.add_handler(CallbackQueryHandler(handle_message))         
app.add_handler(MessageHandler(filters.TEXT, echo))         

app.run_polling()