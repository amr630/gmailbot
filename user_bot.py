import os
import sqlite3
import logging
from telegram import (
    Update,
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ================= الإعدادات الأساسية =================
USER_BOT_TOKEN = "8977875138:AAFxDinrDqlelIaspVux1iGcZAhlzSS_Rx8"
ADMIN_BOT_TOKEN = "8825481644:AAEzHDhl3fhyLSvRcZVY15MSZzXZUCFwg0A"
ADMIN_ID = 6503090203
SUPPORT_URL = "https://t.me/Gmail_store_unlimited"
BOT_LOGO = "1.jpg"
DB_NAME = "system.db"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, BOT_LOGO)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

admin_bot = Bot(token=ADMIN_BOT_TOKEN)

# حالات المحادثة (Conversation States)
ASK_EMAIL, ASK_PASSWORD = range(2)
CHOOSE_WITHDRAW_METHOD, ASK_WITHDRAW_DETAILS, ASK_WITHDRAW_AMOUNT = range(2, 5)
ASK_PHONE = 5

# ================= قاموس اللغات (9 لغات) =================
LANGUAGES = {
    "ar": {
        "name": "🇪🇬 العربية",
        "currency": "ج.م",
        "rate": 1.0,
        "min_with": 12.0,
        "welcome": (
            "👋 أهلاً بك في بوت مهام الجيميل!\n\n"
            "يمكنك الربح بسهولة من خلال إنشاء حسابات جيميل جديدة.\n"
            "اختر لغتك أو استخدم القائمة أدناه للبدء:"
        ),
        "btn_create": "➕ إنشاء إيميل جيميل",
        "btn_balance": "💰 الرصيد",
        "btn_withdraw": "🏧 سحب الرصيد",
        "btn_pending": "⏳ الصناديق المعلقة",
        "btn_wallet": "👛 المحفظة",
        "btn_settings": "⚙️ تغيير اللغة",
        "btn_referral": "👥 الإحالات",
        "btn_support": "🎧 الدعم الفني",
        "btn_back": "🔙 رجوع",
        "btn_cancel": "❌ إلغاء",
        "create_instr": (
            "⚠️ **تعليمات أنشئ الإيميل:**\n"
            "1. أنشئ الإيميل باسم أجنبي.\n"
            "2. لا تقم بربطه بأي رقم هاتف أو بريد إلكتروني لاسترداد الحساب.\n\n"
            "💵 سعر الإيميل الواحد: **{price} {currency}**\n\n"
            "📧 أرسل الآن عنوان البريد الإلكتروني الذي أنشأته (ينتهي بـ `@gmail.com`):"
        ),
        "invalid_email": "⚠️ صيغة الإيميل غير صحيحة! يجب أن ينتهي بـ `@gmail.com` وبدون مسافات. أعد المحاولة:",
        "ask_pass": "🔑 ممتاز! الآن أرسل **كلمة المرور** الخاصة بهذا الحساب:",
        "task_submitted": "✅ تم استلام الحساب بنجاح وهو الآن قيد المراجعة!\nسيتم إضافة **{price} {currency}** إلى رصيدك فور الموافقة عليه.",
        "tasks_paused": "❌ إنشاء المهام متوقف حالياً من قبل الإدارة.",
        "banned": "🚫 حسابك محظور من استخدام البوت.",
        "balance_msg": "💰 **رصيدك الحالي:** `{balance} {currency}`\n💵 **سعر الإيميل:** `{price} {currency}`",
        "pending_msg": "⏳ **الحسابات المعلقة قيد المراجعة ({count}):**\n\n{list}",
        "no_pending": "✅ لا توجد لديك أي حسابات معلقة حالياً.",
        "wallet_msg": (
            "👛 **تفاصيل محفظتك:**\n\n"
            "🆔 المعرف (ID): `{user_id}`\n"
            "📱 رقم الهاتف: `{phone}`\n"
            "💰 الرصيد المتاح: `{balance} {currency}`\n"
            "⏳ المهام المعلقة: `{pending_count}`"
        ),
        "low_balance": "⚠️ رصيدك غير كافٍ للسحب!\nالحد الأدنى للسحب: **{min_with} {currency}**\nرصيدك الحالي: **{balance} {currency}**",
        "choose_withdraw_method": "🏧 **اختر طريقة السحب المناسبة لك:**\n\n💰 رصيدك المتاح: **{balance} {currency}**\n📉 الحد الأدنى للسحب: **{min_with} {currency}**",
        "btn_with_ewallet": "📱 محافط إلكترونية (فودافون كاش / اتصالات كاش / أورنج كاش)",
        "btn_with_crypto": "🪙 كريبتو (USDT - BEP20)",
        "ask_ewallet_details": "📱 أرسل الآن **رقم المحفظة الإلكترونية** الخاصة بك (فودافون / اتصالات / أورنج):",
        "ask_crypto_details": "🌐 **شبكة السحب: BEP20**\n\n🪙 أرسل الآن **عنوان محفظة USDT (BEP20)** الخاصة بك:",
        "ask_withdraw_amount": (
            "💵 أرسل الآن **المبلغ المراد سحبه** بالأرقام:\n"
            "• الحد الأدنى: `{min_with} {currency}`\n"
            "• الحد الأقصى المتاح: `{balance} {currency}`"
        ),
        "invalid_amount": "⚠️ مبلغ غير صالح! يرجى إدخال رقم بين **{min_with}** و **{balance}**:",
        "withdraw_submitted": "✅ تم إرسال طلب السحب بقيمة **{amount} {currency}** بنجاح!\nسيتم مراجعته من قبل الإدارة وإرسال الإيصال لك قريباً.",
        "referral_msg": "👥 نظام الإحالات قيد التحديث حالياً وسيتم تفعيله قريباً.",
        "choose_lang": "🌐 اختر لغتك المفضلة / Choose your language:",
        "lang_updated": "✅ تم اختيار اللغة بنجاح!",
        "cancelled": "❌ تم إلغاء العملية.",
    },
    "en": {
        "name": "🇬🇧 English",
        "currency": "USD",
        "rate": 0.02,
        "min_with": 1.0,
        "welcome": "👋 Welcome to the Gmail Tasks Bot!\n\nEarn money easily by creating Gmail accounts.\nSelect your language or use the menu below:",
        "btn_create": "➕ Create Gmail",
        "btn_balance": "💰 Balance",
        "btn_withdraw": "🏧 Withdraw",
        "btn_pending": "⏳ Pending Tasks",
        "btn_wallet": "👛 Wallet",
        "btn_settings": "⚙️ Language",
        "btn_referral": "👥 Referrals",
        "btn_support": "🎧 Support",
        "btn_back": "🔙 Back",
        "btn_cancel": "❌ Cancel",
        "create_instr": (
            "⚠️ **تعليمات أنشئ الإيميل:**\n"
            "1. أنشئ الإيميل باسم أجنبي.\n"
            "2. لا تقم بربطه بأي رقم هاتف أو بريد إلكتروني لاسترداد الحساب.\n\n"
            "💵 Reward per email: **{price} {currency}**\n\n"
            "📧 Send the Gmail address now (must end with `@gmail.com`):"
        ),
        "invalid_email": "⚠️ Invalid email! Must end with `@gmail.com`. Try again:",
        "ask_pass": "🔑 Great! Now send the **password** for this account:",
        "task_submitted": "✅ Account submitted for review!\n**{price} {currency}** will be credited upon approval.",
        "tasks_paused": "❌ إنشاء المهام متوقف حالياً من قبل الإدارة.",
        "banned": "🚫 حسابك محظور من استخدام البوت.",
        "balance_msg": "💰 **Your Balance:** `{balance} {currency}`\n💵 **Email Price:** `{price} {currency}`",
        "pending_msg": "⏳ **Pending Accounts ({count}):**\n\n{list}",
        "no_pending": "✅ You have no pending accounts.",
        "wallet_msg": (
            "👛 **Wallet Details:**\n\n"
            "🆔 User ID: `{user_id}`\n"
            "📱 Phone: `{phone}`\n"
            "💰 Balance: `{balance} {currency}`\n"
            "⏳ Pending Tasks: `{pending_count}`"
        ),
        "low_balance": "⚠️ Insufficient balance!\nMinimum withdrawal: **{min_with} {currency}**\nYour balance: **{balance} {currency}**",
        "choose_withdraw_method": "🏧 **Choose your withdrawal method:**\n\n💰 Available Balance: **{balance} {currency}**",
        "btn_with_ewallet": "📱 محافط إلكترونية (فودافون كاش / اتصالات كاش / أورنج كاش)",
        "btn_with_crypto": "🪙 كريبتو (USDT - BEP20)",
        "ask_ewallet_details": "📱 Send your **E-Wallet phone number** (Vodafone / Etisalat / Orange):",
        "ask_crypto_details": "🌐 **شبكة السحب: BEP20**\n\n🪙 Send your **USDT (BEP20)** wallet address:",
        "ask_withdraw_amount": "💵 Enter the **amount to withdraw** (Min: `{min_with}`, Max: `{balance}`):",
        "invalid_amount": "⚠️ Invalid amount! Please enter a value between **{min_with}** and **{balance}**:",
        "withdraw_submitted": "✅ Withdrawal request of **{amount} {currency}** has been submitted!",
        "referral_msg": "👥 Referral system coming soon.",
        "choose_lang": "🌐 Choose your language:",
        "lang_updated": "✅ Language updated!",
        "cancelled": "❌ Operation cancelled.",
    },
    "fr": {
        "name": "🇫🇷 Français",
        "currency": "EUR",
        "rate": 0.02,
        "min_with": 1.0,
        "welcome": "👋 Bienvenue sur le Bot Gmail !\n\nGagnez de l'argent en créant des comptes Gmail.\nChoisissez une option ci-dessous :",
        "btn_create": "➕ Créer un Gmail",
        "btn_balance": "💰 Solde",
        "btn_withdraw": "🏧 Retrait",
        "btn_pending": "⏳ En attente",
        "btn_wallet": "👛 Portefeuille",
        "btn_settings": "⚙️ Langue",
        "btn_referral": "👥 Parrainage",
        "btn_support": "🎧 Support",
        "btn_back": "🔙 Retour",
        "btn_cancel": "❌ Annuler",
        "create_instr": (
            "⚠️ **تعليمات أنشئ الإيميل:**\n"
            "1. أنشئ الإيميل باسم أجنبي.\n"
            "2. لا تقم بربطه بأي رقم هاتف أو بريد إلكتروني لاسترداد الحساب.\n\n"
            "💵 Prix par e-mail : **{price} {currency}**\n\n"
            "📧 Envoyez l'adresse Gmail maintenant (se terminant par `@gmail.com`) :"
        ),
        "invalid_email": "⚠️ Format invalide ! Doit se terminer par `@gmail.com`.",
        "ask_pass": "🔑 Envoyez maintenant le **mot de passe** du compte :",
        "task_submitted": "✅ Compte envoyé pour vérification !\n**{price} {currency}** seront ajoutés après approbation.",
        "tasks_paused": "❌ إنشاء المهام متوقف حالياً من قبل الإدارة.",
        "banned": "🚫 حسابك محظور من استخدام البوت.",
        "balance_msg": "💰 **Votre Solde :** `{balance} {currency}`\n💵 **Prix par e-mail :** `{price} {currency}`",
        "pending_msg": "⏳ **Comptes en attente ({count}) :**\n\n{list}",
        "no_pending": "✅ Aucun compte en attente.",
        "wallet_msg": (
            "👛 **Portefeuille :**\n\n"
            "🆔 ID : `{user_id}`\n"
            "📱 Téléphone : `{phone}`\n"
            "💰 Solde : `{balance} {currency}`\n"
            "⏳ En attente : `{pending_count}`"
        ),
        "low_balance": "⚠️ Solde insuffisant ! Minimum : **{min_with} {currency}**",
        "choose_withdraw_method": "🏧 **Choisissez votre méthode de retrait :**\n\n💰 Solde : **{balance} {currency}**",
        "btn_with_ewallet": "📱 محافط إلكترونية (فودافون كاش / اتصالات كاش / أورنج كاش)",
        "btn_with_crypto": "🪙 كريبتو (USDT - BEP20)",
        "ask_ewallet_details": "📱 Envoyez votre **numéro de portefeuille électronique** :",
        "ask_crypto_details": "🌐 **شبكة السحب: BEP20**\n\n🪙 Envoyez votre adresse **USDT (BEP20)** :",
        "ask_withdraw_amount": "💵 Entrez le **montant à retirer** (Min : `{min_with}`, Max : `{balance}`) :",
        "invalid_amount": "⚠️ Montant invalide ! Entrez un nombre entre **{min_with}** et **{balance}** :",
        "withdraw_submitted": "✅ Demande de retrait de **{amount} {currency}** envoyée !",
        "referral_msg": "👥 Système de parrainage bientôt disponible.",
        "choose_lang": "🌐 Choisissez votre langue :",
        "lang_updated": "✅ Langue mise à jour !",
        "cancelled": "❌ Opération annulée.",
    },
}

# استكمال اللغات الـ 9 (الروسية، الألمانية، الإندونيسية، الصينية، الهندية، الأوزبكية)
EXTRA_LANGS = [
    ("ru", "🇷🇺 Русский", "RUB"),
    ("de", "🇩🇪 Deutsch", "EUR"),
    ("id", "🇮🇩 Indonesia", "IDR"),
    ("zh", "🇨🇳 中文", "CNY"),
    ("hi", "🇮🇳 हिन्दी", "INR"),
    ("uz", "🇺🇿 O'zbek", "UZS"),
]
for code, name, curr in EXTRA_LANGS:
    LANGUAGES[code] = {**LANGUAGES["en"], "name": name, "currency": curr}


# ================= دوال قاعدة البيانات =================
def get_db():
    return sqlite3.connect(DB_NAME, timeout=10)


def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0.0,
                lang TEXT DEFAULT 'ar',
                phone TEXT,
                is_banned INTEGER DEFAULT 0
            )"""
        )
        try:
            c.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        c.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                email TEXT,
                password TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        try:
            c.execute("ALTER TABLE tasks ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except sqlite3.OperationalError:
            pass

        c.execute(
            """CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                details TEXT,
                amount REAL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        try:
            c.execute("ALTER TABLE withdrawals ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except sqlite3.OperationalError:
            pass

        c.execute(
            """CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )"""
        )
        c.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('base_email_price', '12')"
        )
        c.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('tasks_paused', 'false')"
        )
        conn.commit()


def get_setting(key: str, default: str = "") -> str:
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = c.fetchone()
        return row[0] if row else default


def get_base_email_price() -> float:
    try:
        return float(get_setting("base_email_price", "12"))
    except ValueError:
        return 12.0


def is_tasks_paused() -> bool:
    val = get_setting("tasks_paused", "false").strip().lower()
    return val in ("true", "1", "yes")


def get_or_create_user(user_id: int):
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT user_id, balance, lang, phone, is_banned FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = c.fetchone()
        if not row:
            c.execute("INSERT INTO users (user_id, lang) VALUES (?, 'ar')", (user_id,))
            conn.commit()
            return (user_id, 0.0, "ar", None, 0)
        return row


def is_user_banned(user_id: int) -> bool:
    user = get_or_create_user(user_id)
    return bool(user[4])


def get_user_lang(user_id: int) -> dict:
    user = get_or_create_user(user_id)
    lang_code = user[2] if user[2] in LANGUAGES else "ar"
    L = dict(LANGUAGES[lang_code])
    base_price = get_base_email_price()
    L["price"] = base_price
    if lang_code == "ar":
        L["min_with"] = base_price
    return L


# ================= القوائم والأزرار =================
def languages_keyboard(include_back: bool = False, L: dict = None) -> InlineKeyboardMarkup:
    btns = []
    row = []
    for code, info in LANGUAGES.items():
        row.append(InlineKeyboardButton(info["name"], callback_data=f"setlang_{code}"))
        if len(row) == 3:
            btns.append(row)
            row = []
    if row:
        btns.append(row)
    if include_back and L:
        btns.append([InlineKeyboardButton(L["btn_back"], callback_data="menu_main")])
    return InlineKeyboardMarkup(btns)


def main_menu_keyboard(L: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(L["btn_create"], callback_data="menu_create")],
            [
                InlineKeyboardButton(L["btn_balance"], callback_data="menu_balance"),
                InlineKeyboardButton(L["btn_withdraw"], callback_data="menu_withdraw"),
            ],
            [
                InlineKeyboardButton(L["btn_pending"], callback_data="menu_pending"),
                InlineKeyboardButton(L["btn_wallet"], callback_data="menu_wallet"),
            ],
            [
                InlineKeyboardButton(L["btn_referral"], callback_data="menu_referral"),
                InlineKeyboardButton(L["btn_settings"], callback_data="menu_settings"),
            ],
            [InlineKeyboardButton(L["btn_support"], url=SUPPORT_URL)],
        ]
    )


def back_keyboard(L: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(L["btn_back"], callback_data="menu_main")]]
    )


def cancel_keyboard(L: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(L["btn_cancel"], callback_data="cancel_conv")]]
    )


async def send_or_edit(query, text: str, reply_markup: InlineKeyboardMarkup):
    """التبديل السلس بين الرسائل المصورة (1.jpg) والرسائل النصية بدون أخطاء"""
    try:
        if query.message.photo:
            await query.message.delete()
            await query.message.chat.send_message(
                text=text, reply_markup=reply_markup, parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                text=text, reply_markup=reply_markup, parse_mode="Markdown"
            )
    except Exception:
        await query.message.chat.send_message(
            text=text, reply_markup=reply_markup, parse_mode="Markdown"
        )


# ================= الأوامر والقوائم الأساسية =================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned(user_id):
        await update.message.reply_text("🚫 حسابك محظور من استخدام البوت.")
        return ConversationHandler.END

    L = get_user_lang(user_id)
    caption_text = f"{L['welcome']}\n\n{L['choose_lang']}"
    kb = languages_keyboard(include_back=False)

    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=caption_text,
                reply_markup=kb,
                parse_mode="Markdown",
            )
    else:
        await update.message.reply_text(
            text=caption_text,
            reply_markup=kb,
            parse_mode="Markdown",
        )
    return ConversationHandler.END


async def menu_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    # فحص الحظر في كل ضغطة زر
    if is_user_banned(user_id):
        await query.answer("🚫 حسابك محظور من استخدام البوت.", show_alert=True)
        return

    data = query.data
    user = get_or_create_user(user_id)
    L = get_user_lang(user_id)

    if data.startswith("setlang_"):
        new_lang = data.split("_")[1]
        if new_lang in LANGUAGES:
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET lang = ? WHERE user_id = ?", (new_lang, user_id)
                )
                conn.commit()
            L = get_user_lang(user_id)
            await query.answer(L["lang_updated"])
            if os.path.exists(LOGO_PATH):
                await query.message.delete()
                with open(LOGO_PATH, "rb") as photo:
                    await query.message.chat.send_photo(
                        photo=photo,
                        caption=L["welcome"],
                        reply_markup=main_menu_keyboard(L),
                        parse_mode="Markdown",
                    )
            else:
                await send_or_edit(query, L["welcome"], main_menu_keyboard(L))
        return

    await query.answer()

    if data == "menu_main":
        if os.path.exists(LOGO_PATH):
            await query.message.delete()
            with open(LOGO_PATH, "rb") as photo:
                await query.message.chat.send_photo(
                    photo=photo,
                    caption=L["welcome"],
                    reply_markup=main_menu_keyboard(L),
                    parse_mode="Markdown",
                )
        else:
            await send_or_edit(query, L["welcome"], main_menu_keyboard(L))

    elif data == "menu_balance":
        text = L["balance_msg"].format(
            balance=round(user[1], 2), price=L["price"], currency=L["currency"]
        )
        await send_or_edit(query, text, back_keyboard(L))

    elif data == "menu_pending":
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT email FROM tasks WHERE user_id = ? AND status = 'pending'",
                (user_id,),
            )
            rows = c.fetchall()

        if not rows:
            text = L["no_pending"]
        else:
            items = "\n".join([f"• `{r[0]}`" for r in rows])
            text = L["pending_msg"].format(count=len(rows), list=items)
        await send_or_edit(query, text, back_keyboard(L))

    elif data == "menu_wallet":
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'pending'",
                (user_id,),
            )
            pending_count = c.fetchone()[0]

        text = L["wallet_msg"].format(
            user_id=user_id,
            phone=user[3] or "---",
            balance=round(user[1], 2),
            currency=L["currency"],
            pending_count=pending_count,
        )
        await send_or_edit(query, text, back_keyboard(L))

    elif data == "menu_referral":
        await send_or_edit(query, L["referral_msg"], back_keyboard(L))

    elif data == "menu_settings":
        await send_or_edit(
            query, L["choose_lang"], languages_keyboard(include_back=True, L=L)
        )


# ================= محادثة إنشاء الإيميل =================
async def create_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if is_user_banned(user_id):
        await query.answer("🚫 حسابك محظور من استخدام البوت.", show_alert=True)
        return ConversationHandler.END

    if is_tasks_paused():
        await query.answer(
            "❌ إنشاء المهام متوقف حالياً من قبل الإدارة.", show_alert=True
        )
        return ConversationHandler.END

    await query.answer()
    L = get_user_lang(user_id)
    text = L["create_instr"].format(price=L["price"], currency=L["currency"])
    await send_or_edit(query, text, cancel_keyboard(L))
    return ASK_EMAIL


async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned(user_id):
        await update.message.reply_text("🚫 حسابك محظور من استخدام البوت.")
        return ConversationHandler.END

    L = get_user_lang(user_id)
    email = update.message.text.strip()

    if (
        not email.lower().endswith("@gmail.com")
        or " " in email
        or len(email) <= len("@gmail.com")
    ):
        await update.message.reply_text(
            L["invalid_email"], reply_markup=cancel_keyboard(L), parse_mode="Markdown"
        )
        return ASK_EMAIL

    context.user_data["task_email"] = email
    await update.message.reply_text(
        L["ask_pass"], reply_markup=cancel_keyboard(L), parse_mode="Markdown"
    )
    return ASK_PASSWORD


async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned(user_id):
        await update.message.reply_text("🚫 حسابك محظور من استخدام البوت.")
        return ConversationHandler.END

    L = get_user_lang(user_id)
    password = update.message.text.strip()
    email = context.user_data.get("task_email")

    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO tasks (user_id, email, password, status) VALUES (?, ?, ?, 'pending')",
            (user_id, email, password),
        )
        task_id = c.lastrowid
        conn.commit()

    # إشعار فوري للأدمن بوجود إيميل جديد
    try:
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ موافقة", callback_data=f"approve_task_{task_id}"
                    ),
                    InlineKeyboardButton(
                        "❌ رفض", callback_data=f"reject_task_{task_id}"
                    ),
                ]
            ]
        )
        await admin_bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"📧 **مهمة جيميل جديدة #{task_id}**\n\n"
                f"👤 **المعرف (User ID):** `{user_id}`\n"
                f"📨 **الإيميل:** `{email}`\n"
                f"🔑 **كلمة المرور:** `{password}`"
            ),
            reply_markup=kb,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"Could not alert admin about new task: {e}")

    text = L["task_submitted"].format(price=L["price"], currency=L["currency"])
    await update.message.reply_text(
        text, reply_markup=main_menu_keyboard(L), parse_mode="Markdown"
    )
    return ConversationHandler.END


# ================= محادثة سحب الرصيد (خيارين) =================
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if is_user_banned(user_id):
        await query.answer("🚫 حسابك محظور من استخدام البوت.", show_alert=True)
        return ConversationHandler.END

    user = get_or_create_user(user_id)
    balance = round(user[1], 2)
    L = get_user_lang(user_id)

    if balance < L["min_with"]:
        await query.answer()
        text = L["low_balance"].format(
            min_with=L["min_with"], balance=balance, currency=L["currency"]
        )
        await send_or_edit(query, text, back_keyboard(L))
        return ConversationHandler.END

    await query.answer()
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    L["btn_with_ewallet"], callback_data="with_opt_ewallet"
                )
            ],
            [
                InlineKeyboardButton(
                    L["btn_with_crypto"], callback_data="with_opt_crypto"
                )
            ],
            [InlineKeyboardButton(L["btn_cancel"], callback_data="cancel_conv")],
        ]
    )
    text = L["choose_withdraw_method"].format(
        balance=balance, min_with=L["min_with"], currency=L["currency"]
    )
    await send_or_edit(query, text, kb)
    return CHOOSE_WITHDRAW_METHOD


async def withdraw_method_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if is_user_banned(user_id):
        await query.answer("🚫 حسابك محظور من استخدام البوت.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    L = get_user_lang(user_id)

    if query.data == "with_opt_ewallet":
        context.user_data["withdraw_method"] = (
            "📱 محافط إلكترونية (فودافون كاش / اتصالات كاش / أورنج كاش)"
        )
        prompt = L["ask_ewallet_details"]
    else:
        context.user_data["withdraw_method"] = "🪙 كريبتو (USDT - BEP20)"
        prompt = L["ask_crypto_details"]

    await send_or_edit(query, prompt, cancel_keyboard(L))
    return ASK_WITHDRAW_DETAILS


async def receive_withdraw_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned(user_id):
        await update.message.reply_text("🚫 حسابك محظور من استخدام البوت.")
        return ConversationHandler.END

    L = get_user_lang(user_id)
    details = update.message.text.strip()
    context.user_data["withdraw_details"] = details

    user = get_or_create_user(user_id)
    balance = round(user[1], 2)

    await update.message.reply_text(
        L["ask_withdraw_amount"].format(
            min_with=L["min_with"], balance=balance, currency=L["currency"]
        ),
        reply_markup=cancel_keyboard(L),
        parse_mode="Markdown",
    )
    return ASK_WITHDRAW_AMOUNT


async def receive_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned(user_id):
        await update.message.reply_text("🚫 حسابك محظور من استخدام البوت.")
        return ConversationHandler.END

    L = get_user_lang(user_id)
    user = get_or_create_user(user_id)
    total_balance = round(user[1], 2)

    try:
        requested_amount = round(float(update.message.text.strip()), 2)
    except ValueError:
        await update.message.reply_text(
            L["invalid_amount"].format(min_with=L["min_with"], balance=total_balance),
            reply_markup=cancel_keyboard(L),
            parse_mode="Markdown",
        )
        return ASK_WITHDRAW_AMOUNT

    if requested_amount < L["min_with"] or requested_amount > total_balance:
        await update.message.reply_text(
            L["invalid_amount"].format(min_with=L["min_with"], balance=total_balance),
            reply_markup=cancel_keyboard(L),
            parse_mode="Markdown",
        )
        return ASK_WITHDRAW_AMOUNT

    method = context.user_data.get("withdraw_method", "غير محدد")
    details = context.user_data.get("withdraw_details", "غير محدد")

    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO withdrawals (user_id, type, details, amount, status) VALUES (?, ?, ?, ?, 'pending')",
            (user_id, method, details, requested_amount),
        )
        withdrawal_id = c.lastrowid
        conn.commit()

    # إرسال إشعار منسق لبوت الإدارة
    alert_text = (
        f"🚨 **طلب سحب جديد #{withdrawal_id}**\n\n"
        f"- **المعرف (User ID):** `{user_id}`\n"
        f"- **إجمالي المحفظة الحالي:** `{total_balance} {L['currency']}`\n"
        f"- **المبلغ المطلوب سحبه:** `{requested_amount} {L['currency']}`\n"
        f"- **طريقة السحب:** {method}\n"
        f"- **بيانات السحب:** `{details}`"
    )
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ موافقة", callback_data=f"approve_with_{withdrawal_id}"
                ),
                InlineKeyboardButton(
                    "❌ رفض", callback_data=f"reject_with_{withdrawal_id}"
                ),
            ]
        ]
    )
    try:
        await admin_bot.send_message(
            chat_id=ADMIN_ID,
            text=alert_text,
            reply_markup=kb,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"Failed to send withdrawal alert to admin: {e}")

    await update.message.reply_text(
        L["withdraw_submitted"].format(
            amount=requested_amount, currency=L["currency"]
        ),
        reply_markup=main_menu_keyboard(L),
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    L = get_user_lang(user_id)
    if update.callback_query:
        await update.callback_query.answer()
        await send_or_edit(update.callback_query, L["cancelled"], main_menu_keyboard(L))
    else:
        await update.message.reply_text(
            L["cancelled"], reply_markup=main_menu_keyboard(L)
        )
    return ConversationHandler.END


async def general_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned(user_id):
        await update.message.reply_text("🚫 حسابك محظور من استخدام البوت.")
        return
    L = get_user_lang(user_id)
    await update.message.reply_text(L["welcome"], reply_markup=main_menu_keyboard(L))


# ================= تشغيل البوت =================
def main():
    init_db()
    app = Application.builder().token(USER_BOT_TOKEN).build()

    create_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_task_start, pattern="^menu_create$")],
        states={
            ASK_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)
            ],
            ASK_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_conv, pattern="^cancel_conv$"),
            CommandHandler("start", start_command),
        ],
        allow_reentry=True,
    )

    withdraw_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(withdraw_start, pattern="^menu_withdraw$")],
        states={
            CHOOSE_WITHDRAW_METHOD: [
                CallbackQueryHandler(withdraw_method_chosen, pattern="^with_opt_")
            ],
            ASK_WITHDRAW_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_withdraw_details)
            ],
            ASK_WITHDRAW_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_withdraw_amount)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_conv, pattern="^cancel_conv$"),
            CommandHandler("start", start_command),
        ],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(create_conv)
    app.add_handler(withdraw_conv)
    app.add_handler(CallbackQueryHandler(menu_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, general_text_handler))

    print("User Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()