import logging
import sqlite3
import jdatetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# آیدی تلگرام شما به عنوان مدیر
ADMIN_ID = 5967882845

GET_INVOICE_DATE, SELLER, LIGHTER, QTY, PRICE, DESCRIPTION, CONFIRM = range(7)
GET_DATE, GET_CARTON, GET_INVENTORY_DESC, CONFIRM_ENTRY = range(7, 11)
GET_RECEIPT_PHOTO, GET_RECEIPT_DESC = range(11, 13)
CHOOSING = 13

CANCEL_BTN = '❌ لغو و بازگشت به منوی اصلی'

# راه‌اندازی پایگاه داده
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            seller TEXT,
            lighter TEXT,
            qty INTEGER,
            price INTEGER,
            total INTEGER,
            description TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def save_invoice_to_db(data):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO invoices (date, seller, lighter, qty, price, total, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (data['invoice_date'], data['seller'], data['lighter'], data['qty'], data['price'], data['total'], data['description']))
    conn.commit()
    conn.close()

def get_today_sales_report():
    today = jdatetime.date.today()
    today_str = f"{today.year}/{today.month:02d}/{today.day:02d}"
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT sum(total), count(*) FROM invoices WHERE date = ?', (today_str,))
    result = cursor.fetchone()
    
    cursor.execute('SELECT seller, sum(total), sum(qty) FROM invoices WHERE date = ? GROUP BY seller', (today_str,))
    sellers_data = cursor.fetchall()
    conn.close()
    
    total_sales = result[0] if result[0] else 0
    total_invoices = result[1] if result[1] else 0
    
    report = f"📊 *گزارش فروش امروز ({today_str}):*\n\n"
    report += f"💵 *مجموع کل فروش:* {total_sales:,} تومان\n"
    report += f"📝 *تعداد فاکتورهای ثبت شده:* {total_invoices}\n\n"
    
    if sellers_data:
        report += "👤 *فروش به تفکیک فروشنده:*\n"
        for row in sellers_data:
            report += f"- {row[0]}: {row[1]:,} تومان ({row[2]:,} عدد)\n"
    else:
        report += "هنوز فاکتوری برای امروز ثبت نشده است."
        
    return report

def get_today_jalali():
    today = jdatetime.date.today()
    return f"{today.year}/{today.month:02d}/{today.day:02d}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user_id = update.effective_user.id
    
    if user_id == ADMIN_ID:
        menu_keyboard = [['📝 ثبت فاکتور', '📦 ورودی کالا'], ['📷 ارسال رسید', '📊 گزارش فروش امروز']]
    else:
        menu_keyboard = [['📝 ثبت فاکتور', '📦 ورودی کالا'], ['📷 ارسال رسید']]
        
    reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)
    await update.message.reply_text('سلام! لطفاً یکی از گزینه‌های زیر را انتخاب کنید:', reply_markup=reply_markup)
    return CHOOSING

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user_id = update.effective_user.id
    
    if user_id == ADMIN_ID:
        menu_keyboard = [['📝 ثبت فاکتور', '📦 ورودی کالا'], ['📷 ارسال رسید', '📊 گزارش فروش امروز']]
    else:
        menu_keyboard = [['📝 ثبت فاکتور', '📦 ورودی کالا'], ['📷 ارسال رسید']]
        
    reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)
    await update.message.reply_text('❌ عملیات لغو شد. یکی از گزینه‌های زیر را انتخاب کنید:', reply_markup=reply_markup)
    return CHOOSING

async def main_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == CANCEL_BTN:
        return await cancel(update, context)
    elif text == '📝 ثبت فاکتور':
        kb = [['📅 امروز'], [CANCEL_BTN]]
        reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
        await update.message.reply_text('لطفاً تاریخ فاکتور را انتخاب کنید یا بنویسید:', reply_markup=reply_markup)
        return GET_INVOICE_DATE
    elif text == '📦 ورودی کالا':
        kb = [['📅 امروز'], [CANCEL_BTN]]
        reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
        await update.message.reply_text('لطفاً تاریخ ورودی کالا را انتخاب کنید یا بنویسید:', reply_markup=reply_markup)
        return GET_DATE
    elif text == '📷 ارسال رسید':
        kb = [[CANCEL_BTN]]
        reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
        await update.message.reply_text('لطفاً عکس رسید یا فاکتور را ارسال کنید:', reply_markup=reply_markup)
        return GET_RECEIPT_PHOTO
    elif text == '📊 گزارش فروش امروز' and user_id == ADMIN_ID:
        report = get_today_sales_report()
        await update.message.reply_text(report, parse_mode='Markdown')
        return CHOOSING
    else:
        await update.message.reply_text('لطفاً از دکمه‌های زیر استفاده کنید.')
        return CHOOSING

async def get_invoice_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_BTN: return await cancel(update, context)
    text = update.message.text
    if text == '📅 امروز':
        context.user_data['invoice_date'] = get_today_jalali()
    else:
        context.user_data['invoice_date'] = text
    sellers = [['تهران', 'شیراز'], [CANCEL_BTN]]
    reply_markup = ReplyKeyboardMarkup(sellers, resize_keyboard=True)
    await update.message.reply_text('لطفاً نام فروشنده را انتخاب یا وارد کنید:', reply_markup=reply_markup)
    return SELLER

async def get_seller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_BTN: return await cancel(update, context)
    context.user_data['seller'] = update.message.text
    lighters = [['فندک شفاف', 'فندک اتمی'], [CANCEL_BTN]]
    reply_markup = ReplyKeyboardMarkup(lighters, resize_keyboard=True)
    await update.message.reply_text('لطفاً نوع فندک را انتخاب یا وارد کنید:', reply_markup=reply_markup)
    return LIGHTER

async def get_lighter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_BTN: return await cancel(update, context)
    context.user_data['lighter'] = update.message.text
    kb = [[CANCEL_BTN]]
    reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    await update.message.reply_text('لطفاً تعداد را وارد کنید (فقط عدد):', reply_markup=reply_markup)
    return QTY

async def get_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_BTN: return await cancel(update, context)
    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text('لطفاً یک عدد معتبر وارد کنید:')
        return QTY
    context.user_data['qty'] = int(text)
    kb = [[CANCEL_BTN]]
    reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    await update.message.reply_text('لطفاً قیمت واحد را وارد کنید (تومان - فقط عدد):', reply_markup=reply_markup)
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_BTN: return await cancel(update, context)
    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text('لطفاً یک عدد معتبر وارد کنید:')
        return PRICE
    context.user_data['price'] = int(text)
    kb = [[CANCEL_BTN]]
    reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    await update.message.reply_text('در صورت نیاز توضیحات را وارد کنید:', reply_markup=reply_markup)
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_BTN: return await cancel(update, context)
    desc_text = update.message.text
    if desc_text == '0':
        desc_text = 'ندارد'
    context.user_data['description'] = desc_text
    total = context.user_data['qty'] * context.user_data['price']
    context.user_data['total'] = total
    summary = f"📋 *خلاصه فاکتور ثبت شده:*\n\n📅 *تاریخ:* {context.user_data['invoice_date']}\n👤 *فروشنده:* {context.user_data['seller']}\n🔥 *نوع فندک:* {context.user_data['lighter']}\n🔢 *تعداد:* {context.user_data['qty']:,}\n💰 *قیمت واحد:* {context.user_data['price']:,} تومان\n💵 *مبلغ کل:* {total:,} تومان\n📝 *توضیحات:* {context.user_data['description']}\n\nآیا اطلاعات مورد تأیید است?"
    confirm_buttons = [['تأیید و ارسال فاکتور', CANCEL_BTN]]
    reply_markup = ReplyKeyboardMarkup(confirm_buttons, resize_keyboard=True)
    await update.message.reply_text(summary, parse_mode='Markdown', reply_markup=reply_markup)
    return CONFIRM

async def confirm_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_BTN: return await cancel(update, context)
    text = update.message.text
    user_id = update.effective_user.id
    if text == 'تأیید و ارسال فاکتور':
        save_invoice_to_db(context.user_data)
        
        total = context.user_data['total']
        admin_msg = f"🔔 *فاکتور جدید ثبت شد:*\n\n📅 *تاریخ:* {context.user_data['invoice_date']}\n👤 *فروشنده:* {context.user_data['seller']}\n🔥 *نوع فندک:* {context.user_data['lighter']}\n🔢 *تعداد:* {context.user_data['qty']:,}\n💰 *قیمت واحد:* {context.user_data['price']:,} تومان\n💵 *مبلغ کل:* {total:,} تومان\n📝 *توضیحات:* {context.user_data['description']}"
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode='Markdown')
            
            if user_id == ADMIN_ID:
                menu_keyboard = [['📝 ثبت فاکتور', '📦 ورودی کالا'], ['📷 ارسال رسید', '📊 گزارش فروش امروز']]
            else:
                menu_keyboard = [['📝 ثبت فاکتور', '📦 ورودی کالا'], ['📷 ارسال رسید']]
                
            reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)
            await update.message.reply_text('✅ فاکتور با موفقیت ثبت شد.\n\nیکی از گزینه‌های زیر را انتخاب کنید:', reply_markup=reply_markup)
        except Exception as e:
            await update.message.reply_text(f'❌ خطا در ارسال فاکتور: {e}')
    else:
        await update.message.reply_text('عملیات لغو شد.')
    return CHOOSING

async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_BTN: return await cancel(update, context)
    text = update.message.text
    if text == '📅 امروز':
        context.user_data['entry_date'] = get_today_jalali()
    else:
        context.user_data['entry_date'] = text
    kb = [[CANCEL_BTN]]
    reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    await update.message.reply_text('لطفاً تعداد جنس به کارتن را وارد کنید (فقط عدد):', reply_markup=reply_markup)
    return GET_CARTON

async def get_carton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_BTN: return await cancel(update, context)
    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text('لطفاً یک عدد معتبر وارد کنید:')
        return GET_CARTON
    context.user_data['carton_qty'] = int(text)
    kb = [[CANCEL_BTN]]
    reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    await update.message.reply_text('لطفاً توضیحات ورودی کالا را وارد کنید:', reply_markup=reply_markup)
    return GET_INVENTORY_DESC

async def get_inventory_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_BTN: return await cancel(update, context)
    desc_text = update.message.text
    if desc_text == '0':
        desc_text = 'ندارد'
    context.user_data['inventory_desc'] = desc_text
    summary = f"📦 *خلاصه ورودی کالا:*\n\n📅 *تاریخ:* {context.user_data['entry_date']}\n📦 *تعداد به کارتن:* {context.user_data['carton_qty']:,}\n📝 *توضیحات:* {context.user_data['inventory_desc']}\n\nآیا اطلاعات مورد تأیید است?"
    confirm_buttons = [['تأیید و ارسال ورودی کالا', CANCEL_BTN]]
    reply_markup = ReplyKeyboardMarkup(confirm_buttons, resize_keyboard=True)
    await update.message.reply_text(summary, parse_mode='Markdown', reply_markup=reply_markup)
    return CONFIRM_ENTRY

async def confirm_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_BTN: return await cancel(update, context)
    text = update.message.text
    user_id = update.effective_user.id
    if text == 'تأیید و ارسال ورودی کالا':
        admin_msg = f"📦 *ورودی کالای جدید ثبت شد:*\n\n📅 *تاریخ:* {context.user_data['entry_date']}\n📦 *تعداد به کارتن:* {context.user_data['carton_qty']:,}\n📝 *توضیحات:* {context.user_data['inventory_desc']}"
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode='Markdown')
            
            if user_id == ADMIN_ID:
                menu_keyboard = [['📝 ثبت فاکتور', '📦 ورودی کالا'], ['📷 ارسال رسید', '📊 گزارش فروش امروز']]
            else:
                menu_keyboard = [['📝 ثبت فاکتور', '📦 ورودی کالا'], ['📷 ارسال رسید']]
                
            reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)
            await update.message.reply_text('✅ ورودی کالا با موفقیت ثبت شد.\n\nیکی از گزینه‌های زیر را انتخاب کنید:', reply_markup=reply_markup)
        except Exception as e:
            await update.message.reply_text(f'❌ خطا در ارسال: {e}')
    else:
        await update.message.reply_text('عملیات لغو شد.')
    return CHOOSING

async def get_receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_BTN: return await cancel(update, context)
    if not update.message.photo:
        await update.message.reply_text('لطفاً حتماً یک **عکس** از رسید ارسال کنید یا دکمه لغو را بزنید:')
        return GET_RECEIPT_PHOTO
    
    context.user_data['photo_file_id'] = update.message.photo[-1].file_id
    kb = [[CANCEL_BTN]]
    reply_markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    await update.message.reply_text('توضیحات مربوط به این رسید را وارد کنید (یا عدد 0 را بفرستید):', reply_markup=reply_markup)
    return GET_RECEIPT_DESC

async def get_receipt_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_BTN: return await cancel(update, context)
    desc = update.message.text
    if desc == '0':
        desc = 'ندارد'
    
    photo_id = context.user_data.get('photo_file_id')
    user_info = update.effective_user
    user_name = user_info.full_name or "کاربر"
    user_id = user_info.id
    
    admin_caption = f"📷 *رسید جدید دریافت شد!*\n👤 *ارسال‌کننده:* {user_name}\n📝 *توضیحات:* {desc}"
    
    try:
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_caption, parse_mode='Markdown')
        
        if user_id == ADMIN_ID:
            menu_keyboard = [['📝 ثبت فاکتور', '📦 ورودی کالا'], ['📷 ارسال رسید', '📊 گزارش فروش امروز']]
        else:
            menu_keyboard = [['📝 ثبت فاکتور', '📦 ورودی کالا'], ['📷 ارسال رسید']]
            
        reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)
        await update.message.reply_text('✅ عکس رسید با موفقیت ارسال شد.\n\nیکی از گزینه‌های زیر را انتخاب کنید:', reply_markup=reply_markup)
    except Exception as e:
        await update.message.reply_text(f'❌ خطا در ارسال عکس: {e}')
        
    return CHOOSING

if __name__ == '__main__':
    BOT_TOKEN = '8381801162:AAFw3opCNQ7YyhEDtia2nm-zCyLgJOC3GaY'
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_choice)],
            GET_INVOICE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_invoice_date)],
            SELLER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_seller)],
            LIGHTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_lighter)],
            QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_qty)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_invoice)],
            GET_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            GET_CARTON: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_carton)],
            GET_INVENTORY_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_inventory_desc)],
            CONFIRM_ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_entry)],
            GET_RECEIPT_PHOTO: [MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, get_receipt_photo)],
            GET_RECEIPT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_receipt_desc)]
        },
        fallbacks=[CommandHandler('cancel', cancel), MessageHandler(filters.Regex('^❌ لغو و بازگشت به منوی اصلی$'), cancel)]
    )
    app.add_handler(conv_handler)
    print('ربات با موفقیت به‌روزرسانی شد...')
    from flask import Flask
import threading
import os

app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)
# اجرای وب‌سرور در پس‌زمینه برای رندر
threading.Thread(target=run_web).daemon = True
app.run_polling()
