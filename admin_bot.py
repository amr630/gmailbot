import io
import sqlite3
import logging
from telegram import (
    Update,
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= الإعدادات الأساسية =================
ADMIN_BOT_TOKEN = "8825481644:AAEzHDhl3fhyLSvRcZVY15MSZzXZUCFwg0A"
USER_BOT_TOKEN = "8977875138:AAFxDinrDqlelIaspVux1iGcZAhlzSS_Rx8"
ADMIN_ID = 6503090203
ADMIN_PASSWORD = "admin123"
DB_NAME = "system.db"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

user_bot = Bot(token=USER_BOT_TOKEN)

# جلسات الأدمن المصرح لها بعد إدخال كلمة السر
AUTHENTICATED_ADMINS = set()


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


def set_setting(key: str, value: str):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )
        conn.commit()


def get_base_email_price() -> float:
    try:
        return float(get_setting("base_email_price", "12"))
    except ValueError:
        return 12.0


def set_user_ban_status(user_id: int, banned: int):
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.execute(
            "UPDATE users SET is_banned = ? WHERE user_id = ?", (banned, user_id)
        )
        conn.commit()


def get_oldest_pending_task():
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, user_id, email, password, created_at FROM tasks WHERE status = 'pending' ORDER BY id ASC LIMIT 1"
        )
        return c.fetchone()


def get_oldest_pending_withdrawal():
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            """SELECT w.id, w.user_id, w.type, w.details, w.amount, u.balance
               FROM withdrawals w
               LEFT JOIN users u ON w.user_id = u.user_id
               WHERE w.status = 'pending'
               ORDER BY w.id ASC LIMIT 1"""
        )
        return c.fetchone()


# ================= لوحة تحكم الأدمن (عربي 100%) =================
def admin_reply_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        ["📦 جلب الطلبات المعلقة", "💸 جلب طلبات السحب"],
        ["💰 تغيير سعر الإيميل"],
        ["🚫 حظر مستخدم", "✅ فك حظر مستخدم"],
        ["⏸️ إيقاف إنشاء المهام", "▶️ تفعيل إنشاء المهام"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def is_authorized(user_id: int) -> bool:
    return user_id in AUTHENTICATED_ADMINS


# ================= الأوامر ومعالجة الأزرار =================
async def start_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data.clear()

    if is_authorized(user_id):
        await update.message.reply_text(
            "👨‍💻 أهلاً بك مجدداً في لوحة تحكم الإدارة:",
            reply_markup=admin_reply_keyboard(),
        )
        return

    context.user_data["admin_state"] = "WAIT_PASSWORD"
    await update.message.reply_text("🔒 أهلاً بك في بوت الإدارة.\nيرجى إدخال كلمة المرور للمتابعة:")


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    state = context.user_data.get("admin_state")

    # 1. التحقق من كلمة المرور
    if not is_authorized(user_id):
        if text == ADMIN_PASSWORD:
            AUTHENTICATED_ADMINS.add(user_id)
            context.user_data["admin_state"] = None
            await update.message.reply_text(
                "✅ تم تسجيل الدخول بنجاح! اختر من لوحة التحكم أدناه:",
                reply_markup=admin_reply_keyboard(),
            )
        else:
            await update.message.reply_text("❌ كلمة المرور غير صحيحة! حاول مرة أخرى:")
        return

    # 2. فحص أزرار القائمة الرئيسية أولاً (لإلغاء أي حالة معلقة عند الضغط على زر جديد)
    if text == "📦 جلب الطلبات المعلقة":
        context.user_data["admin_state"] = None
        task = get_oldest_pending_task()
        if not task:
            await update.message.reply_text("✅ لا توجد أي طلبات إيميلات معلقة حالياً.")
            return

        t_id, u_id, email, password, created_at = task
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ موافقة", callback_data=f"approve_task_{t_id}"),
                    InlineKeyboardButton("❌ رفض", callback_data=f"reject_task_{t_id}"),
                ]
            ]
        )
        await update.message.reply_text(
            f"📦 **طلب مراجعة إيميل #{t_id}**\n\n"
            f"- **المعرف (User ID):** `{u_id}`\n"
            f"- **الإيميل:** `{email}`\n"
            f"- **كلمة المرور:** `{password}`\n"
            f"- **التاريخ:** `{created_at}`",
            reply_markup=kb,
            parse_mode="Markdown",
        )
        return

    elif text == "💸 جلب طلبات السحب":
        context.user_data["admin_state"] = None
        w_req = get_oldest_pending_withdrawal()
        if not w_req:
            await update.message.reply_text("✅ لا توجد أي طلبات سحب معلقة حالياً.")
            return

        w_id, u_id, w_type, details, amount, total_balance = w_req
        total_balance = round(total_balance or 0.0, 2)
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ موافقة", callback_data=f"approve_with_{w_id}"),
                    InlineKeyboardButton("❌ رفض", callback_data=f"reject_with_{w_id}"),
                ]
            ]
        )
        await update.message.reply_text(
            f"💸 **طلب سحب معلق #{w_id}**\n\n"
            f"- **المعرف (User ID):** `{u_id}`\n"
            f"- **إجمالي المحفظة الحالي:** `{total_balance}`\n"
            f"- **المبلغ المطلوب سحبه:** `{amount}`\n"
            f"- **طريقة السحب:** {w_type}\n"
            f"- **بيانات السحب:** `{details}`",
            reply_markup=kb,
            parse_mode="Markdown",
        )
        return

    elif text == "💰 تغيير سعر الإيميل":
        context.user_data["admin_state"] = "WAIT_NEW_PRICE"
        curr_price = get_base_email_price()
        await update.message.reply_text(
            f"💵 السعر الأساسي الحالي للإيميل هو: `{curr_price}`\n\n"
            "أرسل الآن **السعر الجديد** بالأرقام:",
            parse_mode="Markdown",
        )
        return

    elif text == "🚫 حظر مستخدم":
        context.user_data["admin_state"] = "WAIT_BAN_ID"
        await update.message.reply_text(
            "🚫 أرسل الآن **المعرف (User ID)** الخاص بالمستخدم المراد حظره:"
        )
        return

    elif text == "✅ فك حظر مستخدم":
        context.user_data["admin_state"] = "WAIT_UNBAN_ID"
        await update.message.reply_text(
            "✅ أرسل الآن **المعرف (User ID)** الخاص بالمستخدم المراد فك حظره:"
        )
        return

    elif text == "⏸️ إيقاف إنشاء المهام":
        context.user_data["admin_state"] = None
        set_setting("tasks_paused", "true")
        await update.message.reply_text(
            "⏸️ تم **إيقاف إنشاء المهام** بنجاح (عمليات السحب لا تزال متاحة للمستخدمين).",
            reply_markup=admin_reply_keyboard(),
            parse_mode="Markdown",
        )
        return

    elif text == "▶️ تفعيل إنشاء المهام":
        context.user_data["admin_state"] = None
        set_setting("tasks_paused", "false")
        await update.message.reply_text(
            "▶️ تم **تفعيل إنشاء المهام** بنجاح ويمكن للمستخدمين إرسال الإيميلات الآن.",
            reply_markup=admin_reply_keyboard(),
            parse_mode="Markdown",
        )
        return

    # 3. معالجة المدخلات النصية حسب الحالة (State)
    if state == "WAIT_NEW_PRICE":
        try:
            new_price = float(text)
            if new_price <= 0:
                raise ValueError
            set_setting("base_email_price", str(new_price))
            context.user_data["admin_state"] = None
            await update.message.reply_text(
                f"✅ تم تحديث سعر الإيميل الأساسي إلى: **{new_price}**",
                reply_markup=admin_reply_keyboard(),
                parse_mode="Markdown",
            )
        except ValueError:
            await update.message.reply_text("⚠️ يرجى إدخال رقم صحيح أكبر من الصفر:")

    elif state == "WAIT_BAN_ID":
        try:
            target_id = int(text)
            set_user_ban_status(target_id, 1)
            context.user_data["admin_state"] = None
            await update.message.reply_text(
                f"🚫 تم حظر المستخدم `{target_id}` بنجاح.",
                reply_markup=admin_reply_keyboard(),
                parse_mode="Markdown",
            )
            try:
                await user_bot.send_message(
                    chat_id=target_id, text="🚫 حسابك محظور من استخدام البوت."
                )
            except Exception:
                pass
        except ValueError:
            await update.message.reply_text("⚠️ يرجى إدخال معرف (User ID) صحيح بالأرقام فقط:")

    elif state == "WAIT_UNBAN_ID":
        try:
            target_id = int(text)
            set_user_ban_status(target_id, 0)
            context.user_data["admin_state"] = None
            await update.message.reply_text(
                f"✅ تم فك الحظر عن المستخدم `{target_id}` بنجاح.",
                reply_markup=admin_reply_keyboard(),
                parse_mode="Markdown",
            )
            try:
                await user_bot.send_message(
                    chat_id=target_id,
                    text="✅ تم فك الحظر عن حسابك! يمكنك الآن استخدام البوت بشكل طبيعي عبر إرسال /start.",
                )
            except Exception:
                pass
        except ValueError:
            await update.message.reply_text("⚠️ يرجى إدخال معرف (User ID) صحيح بالأرقام فقط:")

    elif state in ("WAIT_TASK_REJECT_PHOTO", "WAIT_WITH_REJECT_PHOTO", "WAIT_WITH_APPROVE_PHOTO"):
        await update.message.reply_text("⚠️ يرجى إرسال **صورة (Screenshot / إيصال)** لإتمام العملية:")


# ================= معالجة أزرار الموافقة والرفض (Inline Callbacks) =================
async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_authorized(user_id):
        await query.answer("🔒 يرجى تسجيل الدخول أولاً عبر إرسال /start", show_alert=True)
        return

    data = query.data

    # 1. الموافقة على مهمة جيميل
    if data.startswith("approve_task_"):
        t_id = int(data.split("_")[2])
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT user_id, email, status FROM tasks WHERE id = ?", (t_id,))
            row = c.fetchone()
            if not row or row[2] != "pending":
                await query.answer("⚠️ تم التعامل مع هذا الطلب مسبقاً.", show_alert=True)
                return

            u_id, email, _ = row
            reward = get_base_email_price()
            c.execute("UPDATE tasks SET status = 'approved' WHERE id = ?", (t_id,))
            c.execute(
                "INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0.0)", (u_id,)
            )
            c.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (reward, u_id),
            )
            conn.commit()

        await query.answer("✅ تمت الموافقة!")
        await query.edit_message_text(
            f"✅ **تمت الموافقة على الإيميل #{t_id}**\n"
            f"- المستخدم: `{u_id}`\n"
            f"- الإيميل: `{email}`\n"
            f"- المبلغ المضاف: `{reward}`",
            parse_mode="Markdown",
        )
        try:
            await user_bot.send_message(
                chat_id=u_id,
                text=f"✅ تمت الموافقة على حساب الجيميل (`{email}`) وتمت إضافة **{reward}** إلى رصيدك!",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Failed to notify user {u_id}: {e}")

    # 2. رفض مهمة جيميل (يطلب سكرين شوت السبب)
    elif data.startswith("reject_task_"):
        t_id = int(data.split("_")[2])
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT user_id, email, status FROM tasks WHERE id = ?", (t_id,))
            row = c.fetchone()
            if not row or row[2] != "pending":
                await query.answer("⚠️ تم التعامل مع هذا الطلب مسبقاً.", show_alert=True)
                return

        context.user_data["admin_state"] = "WAIT_TASK_REJECT_PHOTO"
        context.user_data["target_task_id"] = t_id
        await query.answer()
        await query.message.reply_text(
            f"📸 أرسل الآن **صورة (Screenshot)** توضح سبب رفض الإيميل #{t_id} ليتم إرسالها للمستخدم:"
        )

    # 3. الموافقة على طلب سحب (يطلب صورة إيصال التحويل)
    elif data.startswith("approve_with_"):
        w_id = int(data.split("_")[2])
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT user_id, amount, status FROM withdrawals WHERE id = ?", (w_id,)
            )
            row = c.fetchone()
            if not row or row[2] != "pending":
                await query.answer("⚠️ تم التعامل مع طلب السحب هذا مسبقاً.", show_alert=True)
                return

        context.user_data["admin_state"] = "WAIT_WITH_APPROVE_PHOTO"
        context.user_data["target_with_id"] = w_id
        await query.answer()
        await query.message.reply_text(
            f"🧾 أرسل الآن **صورة إيصال الدفع** لتأكيد طلب السحب #{w_id} وخصم المبلغ من رصيد المستخدم:"
        )

    # 4. رفض طلب سحب (يطلب سكرين شوت السبب)
    elif data.startswith("reject_with_"):
        w_id = int(data.split("_")[2])
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT user_id, amount, status FROM withdrawals WHERE id = ?", (w_id,)
            )
            row = c.fetchone()
            if not row or row[2] != "pending":
                await query.answer("⚠️ تم التعامل مع طلب السحب هذا مسبقاً.", show_alert=True)
                return

        context.user_data["admin_state"] = "WAIT_WITH_REJECT_PHOTO"
        context.user_data["target_with_id"] = w_id
        await query.answer()
        await query.message.reply_text(
            f"📸 أرسل الآن **صورة (Screenshot)** توضح سبب رفض طلب السحب #{w_id} ليتم إرسالها للمستخدم:"
        )


# ================= معالجة الصور المرسلة من الأدمن (الإيصالات والرفض) =================
async def handle_admin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    state = context.user_data.get("admin_state")
    if state not in (
        "WAIT_TASK_REJECT_PHOTO",
        "WAIT_WITH_REJECT_PHOTO",
        "WAIT_WITH_APPROVE_PHOTO",
    ):
        return

    # تحميل الصورة في الذاكرة لإرسالها عبر بوت المستخدم بنجاح
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = io.BytesIO()
    await photo_file.download_to_memory(out=photo_bytes)
    photo_bytes.seek(0)

    # حالة 1: رفض مهمة جيميل مع صورة
    if state == "WAIT_TASK_REJECT_PHOTO":
        t_id = context.user_data.get("target_task_id")
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT user_id, email, status FROM tasks WHERE id = ?", (t_id,))
            row = c.fetchone()
            if not row or row[2] != "pending":
                await update.message.reply_text("⚠️ تم التعامل مع هذا الطلب مسبقاً.")
                context.user_data["admin_state"] = None
                return

            u_id, email, _ = row
            c.execute("UPDATE tasks SET status = 'rejected' WHERE id = ?", (t_id,))
            conn.commit()

        context.user_data["admin_state"] = None
        try:
            await user_bot.send_photo(
                chat_id=u_id,
                photo=photo_bytes,
                caption=f"❌ **تم رفض حساب الجيميل:** `{email}`\nمرفق بالصورة سبب الرفض.",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Failed to send rejection photo to user {u_id}: {e}")

        await update.message.reply_text(
            f"❌ تم رفض المهمة #{t_id} وإرسال صورة السبب للمستخدم `{u_id}` بنجاح.",
            reply_markup=admin_reply_keyboard(),
            parse_mode="Markdown",
        )

    # حالة 2: الموافقة على طلب سحب مع إيصال الدفع
    elif state == "WAIT_WITH_APPROVE_PHOTO":
        w_id = context.user_data.get("target_with_id")
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT user_id, amount, type, details, status FROM withdrawals WHERE id = ?",
                (w_id,),
            )
            row = c.fetchone()
            if not row or row[4] != "pending":
                await update.message.reply_text("⚠️ تم التعامل مع طلب السحب هذا مسبقاً.")
                context.user_data["admin_state"] = None
                return

            u_id, amount, w_type, details, _ = row
            c.execute(
                "UPDATE withdrawals SET status = 'approved' WHERE id = ?", (w_id,)
            )
            c.execute(
                "UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ?",
                (amount, u_id),
            )
            conn.commit()

        context.user_data["admin_state"] = None
        try:
            await user_bot.send_photo(
                chat_id=u_id,
                photo=photo_bytes,
                caption=(
                    f"✅ **تم تنفيذ طلب السحب الخاص بك بنجاح!**\n\n"
                    f"💰 **المبلغ المحول:** `{amount}`\n"
                    f"💳 **الوسيلة:** {w_type}\n"
                    f"📋 **البيانات:** `{details}`\n\n"
                    f"مرفق صورة إيصال التحويل."
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Failed to send receipt photo to user {u_id}: {e}")

        await update.message.reply_text(
            f"✅ تم تأكيد طلب السحب #{w_id}، وخصم `{amount}` من رصيد المستخدم `{u_id}`، وإرسال الإيصال له.",
            reply_markup=admin_reply_keyboard(),
            parse_mode="Markdown",
        )

    # حالة 3: رفض طلب سحب مع صورة السبب
    elif state == "WAIT_WITH_REJECT_PHOTO":
        w_id = context.user_data.get("target_with_id")
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT user_id, amount, status FROM withdrawals WHERE id = ?", (w_id,)
            )
            row = c.fetchone()
            if not row or row[2] != "pending":
                await update.message.reply_text("⚠️ تم التعامل مع طلب السحب هذا مسبقاً.")
                context.user_data["admin_state"] = None
                return

            u_id, amount, _ = row
            c.execute(
                "UPDATE withdrawals SET status = 'rejected' WHERE id = ?", (w_id,)
            )
            conn.commit()

        context.user_data["admin_state"] = None
        try:
            await user_bot.send_photo(
                chat_id=u_id,
                photo=photo_bytes,
                caption=f"❌ **تم رفض طلب السحب بقيمة `{amount}`**\nمرفق بالصورة سبب الرفض.",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Failed to send withdrawal rejection photo to user {u_id}: {e}")

        await update.message.reply_text(
            f"❌ تم رفض طلب السحب #{w_id} وإرسال صورة السبب للمستخدم `{u_id}`.",
            reply_markup=admin_reply_keyboard(),
            parse_mode="Markdown",
        )


# ================= تشغيل بوت الإدارة =================
def main():
    init_db()
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_admin))
    app.add_handler(CallbackQueryHandler(handle_admin_callbacks))
    app.add_handler(MessageHandler(filters.PHOTO, handle_admin_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_text))

    print("Admin Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()