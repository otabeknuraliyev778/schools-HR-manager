from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext

from config import get_staff_info_by_id, normalize_phone_number
from keyboards.candidate import main_menu_kb, phone_register_mandatory_kb
from keyboards.admin import admin_main_kb
from database import (
    cancel_candidate_draft,
    get_user_by_id,
    save_or_update_user,
    get_staff_by_user_id,
    get_all_staff_user_ids,
    create_appeal
)
from states import AuthStates, FeedbackStates

router = Router()

@router.message(F.text.in_({"/id", "/myid", "id", "ID"}))
async def cmd_my_id(message: Message):
    user_id = message.from_user.id
    staff_info = get_staff_info_by_id(user_id)
    if staff_info:
        role_title = staff_info.get("title", "Xodim")
        icon = staff_info.get("icon", "👔")
    else:
        user = await get_user_by_id(user_id)
        role_title = user.get("title", "Nomzod (Foydalanuvchi)") if user else "Nomzod (Foydalanuvchi)"
        icon = "👤"

    text = (
        f"🆔 <b>Sizning Telegram ma'lumotlaringiz:</b>\n\n"
        f"🔢 <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"👤 <b>Ism:</b> {message.from_user.full_name}\n"
        f"{icon} <b>Tizimdagi rol:</b> {role_title}\n\n"
        "<i>Eslatma: Ushbu ID raqam orqali bot sozlamalarida (.env faylida) Direktor, Admin yoki Menejer vakolatlari belgilanadi.</i>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    user = await get_user_by_id(user_id)

    # 1. Agar foydalanuvchi hali telefon raqamini tasdiqlamagan bo'lsa - majburiy so'raymiz (hamma uchun majburiy)
    if not user or not user.get("phone"):
        await state.set_state(AuthStates.waiting_mandatory_phone)
        welcome_text = (
            f"Assalomu alaykum, hurmatli <b>{message.from_user.full_name}</b>!\n\n"
            "🏛 <b>Ixtisoslashgan maktabning Kadrlar tizimi yordamchi botiga xush kelibsiz!</b>\n\n"
            "Botdan to'liq foydalanish, vakansiyalar bilan tanishish yoki boshqaruv paneliga kirish uchun, "
            "iltimos, pastdagi <b>«📱 Telefon raqamimni yuborish»</b> tugmasini bosing:"
        )
        await message.answer(
            welcome_text,
            reply_markup=phone_register_mandatory_kb(),
            parse_mode="HTML"
        )
        return

    # 2. Agar foydalanuvchi allaqachon telefon kiritgan bo'lsa:
    # Telegram ID bo'yicha xodim (Direktor, Admin, Menejer) ekanligini tekshiramiz
    staff_info = get_staff_info_by_id(user_id)
    if staff_info:
        role = staff_info["role"]
        title = staff_info["title"]
        icon = staff_info.get("icon", "👔")

        # Agar bazadagi roli o'zgargan bo'lsa yangilab qo'yamiz
        if user.get("role") != role or user.get("title") != title:
            await save_or_update_user(
                user_id=user_id,
                phone=user["phone"],
                role=role,
                title=title,
                full_name=message.from_user.full_name
            )

        await message.answer(
            f"Assalomu alaykum, {icon} <b>{title}</b>!\n"
            "Sizga boshqaruv paneli yuklandi:",
            reply_markup=admin_main_kb(role=role),
            parse_mode="HTML"
        )
        return

    # 3. Agar bazada ro'yxatdan o'tgan bo'lsa
    role = user.get("role", "candidate")
    title = user.get("title", "Foydalanuvchi")

    if role in ("admin", "menejer", "direktor"):
        await message.answer(
            f"Assalomu alaykum, <b>{title}</b>!\n"
            "Sizga boshqaruv paneli yuklandi:",
            reply_markup=admin_main_kb(role=role),
            parse_mode="HTML"
        )
    else:
        # Nomzod uchun
        welcome_text = (
            f"Assalomu alaykum, hurmatli <b>{message.from_user.full_name}</b>!\n\n"
            "🏛 <b>Ixtisoslashgan maktab kadrlar tanloviga xush kelibsiz!</b>\n\n"
            "Ushbu bot orqali siz:\n"
            "• Mavjud bo'sh ish o'rinlari (vakansiyalar) bilan tanishishingiz;\n"
            "• O'z arizangiz va tegishli hujjatlarni onlayn topshirishingiz mumkin.\n\n"
            "⚠️ <b>MUHIM QOIDA:</b>\n"
            "<i>Arizangiz kadrlar bo'limi menejeriga ko'rinishi va rasmiy ko'rib chiqilishi uchun "
            "barcha bosqichlarni to'liq yakunlab, so'nggi <b>«Tasdiqlash va yuborish»</b> tugmasini bosishingiz shart! "
            "Aks holda, ariza qoralama (draft) sifatida qoladi va topshirilmagan hisoblanadi.</i>"
        )
        await message.answer(
            welcome_text,
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )

# --- MAJBURIY TELEFON RAQAM QABUL QILISH VA TELEGRAM ID ORQALI ROL BELGILASH ---

@router.message(AuthStates.waiting_mandatory_phone, F.contact | F.text)
async def process_mandatory_phone(message: Message, state: FSMContext):
    raw_phone = ""
    if message.contact:
        raw_phone = message.contact.phone_number
    elif message.text:
        raw_phone = message.text.strip()

    normalized_phone = normalize_phone_number(raw_phone)

    if not normalized_phone or len(normalized_phone) < 9:
        await message.answer(
            "⚠️ Iltimos, haqiqiy telefon raqamingizni pastdagi <b>«📱 Telefon raqamimni yuborish»</b> "
            "tugmasi orqali yuboring yoki to'liq formatda yozing (+998XXXXXXXXX):",
            reply_markup=phone_register_mandatory_kb(),
            parse_mode="HTML"
        )
        return

    # AVTOMATIK TEKSHIRUV: TELEGRAM ID ORQALI (Direktor, Admin, Menejer yoki Nomzod)
    staff_info = get_staff_info_by_id(message.from_user.id)
    if staff_info:
        role = staff_info["role"]
        title = staff_info["title"]
        icon = staff_info.get("icon", "👔")

        await save_or_update_user(
            user_id=message.from_user.id,
            phone=normalized_phone,
            role=role,
            title=title,
            full_name=message.from_user.full_name
        )
        await state.clear()

        success_text = (
            f"{icon} <b>Xush kelibsiz, {title}!</b>\n\n"
            f"Sizning Telegram ID raqamingiz (<code>{message.from_user.id}</code>) tizim tomonidan tanildi.\n"
            f"Telefon raqamingiz (<code>{normalized_phone}</code>) muvaffaqiyatli saqlandi.\n"
            "Sizga to'liq boshqaruv paneli avtomatik faollashtirildi!"
        )
        await message.answer(
            success_text,
            reply_markup=admin_main_kb(role=role),
            parse_mode="HTML"
        )
    else:
        # Oddiy nomzod (talabgor)
        role = "candidate"
        title = "Nomzod"

        await save_or_update_user(
            user_id=message.from_user.id,
            phone=normalized_phone,
            role=role,
            title=title,
            full_name=message.from_user.full_name
        )
        await state.clear()

        welcome_text = (
            f"✅ <b>Raqamingiz qabul qilindi:</b> <code>{normalized_phone}</code>\n\n"
            "🏛 <b>Ixtisoslashgan maktab kadrlar tanloviga xush kelibsiz!</b>\n\n"
            "Quyidagi bo'limlardan birini tanlang:"
        )
        await message.answer(
            welcome_text,
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )

# --- UMUMIY MA'LUMOT VA BEKOR QILISH ---

@router.message(F.text == "ℹ️ Maktab va talablar haqida")
async def about_school(message: Message):
    text = (
        "🏫 <b>Ixtisoslashgan maktab haqida ma'lumot:</b>\n\n"
        "Maktabimiz iqtidorli o'quvchilarga aniq, tabiiy fanlar hamda xorijiy tillar bo'yicha "
        "chuqurlashtirilgan ta'lim berishga ixtisoslashtirilgan nufuzli ta'lim dargohidir.\n\n"
        "🎯 <b>Nomzodlarga qo'yiladigan umumiy talablar:</b>\n"
        "• Tegishli fan yoki soha bo'yicha oliy pedagogik/kasbiy ma'lumot;\n"
        "• Kamida 1-toifa yoki Oliy toifa (yoki xalqaro/milliy sertifikatlar: IELTS, CEFR C1, Fan sertifikati ballari);\n"
        "• Zamonaviy interfaol va axborot-kommunikatsiya texnologiyalaridan erkin foydalana olish;\n"
        "• O'quvchilarni olimpiadalar va nufuzli tanlovlarga tayyorlash tajribasi (ustunlik beradi).\n\n"
        "<i>Bo'sh ish o'rinlari bo'limiga o'tib, o'zingizga mos vakansiyani tanlashingiz mumkin.</i>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "✍️ Murojaat yo'llash")
async def start_feedback(message: Message, state: FSMContext):
    user = await get_user_by_id(message.from_user.id)
    if not user or not user.get("phone"):
        await state.set_state(AuthStates.waiting_mandatory_phone)
        await message.answer(
            "Murojaat yo'llashdan oldin, iltimos, telefon raqamingizni tasdiqlang:",
            reply_markup=phone_register_mandatory_kb()
        )
        return

    await state.set_state(FeedbackStates.waiting_feedback_text)
    cancel_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Murojaatni bekor qilish")]],
        resize_keyboard=True
    )
    text = (
        "✍️ <b>Maktab ma'muriyatiga murojaat yo'llash:</b>\n\n"
        "Savolingiz, taklifingiz yoki arizangiz bo'yicha murojaat matnini yozing.\n"
        "Murojaatingiz to'g'ridan-to'g'ri maktab rahbariyati (Direktor, Menejerlar)ga yetkaziladi.\n\n"
        "<i>Bekor qilish uchun pastdagi tugmani bosing.</i>"
    )
    await message.answer(text, reply_markup=cancel_kb, parse_mode="HTML")

@router.message(FeedbackStates.waiting_feedback_text)
async def process_feedback_text(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Murojaatni bekor qilish":
        await state.clear()
        staff = await get_staff_by_user_id(message.from_user.id)
        await message.answer("Murojaat bekor qilindi.", reply_markup=main_menu_kb(staff_info=staff))
        return

    feedback_text = message.text.strip() if message.text else ""
    if not feedback_text:
        await message.answer("Iltimos, murojaatingiz matnini matn ko'rinishida yozing:")
        return

    user = await get_user_by_id(message.from_user.id)
    full_name = message.from_user.full_name
    phone = user.get("phone", "Ko'rsatilmagan") if user else "Ko'rsatilmagan"

    # Bazaga saqlaymiz
    appeal_id = await create_appeal(
        user_id=message.from_user.id,
        full_name=full_name,
        phone=phone,
        message_text=feedback_text
    )

    await state.clear()
    staff = await get_staff_by_user_id(message.from_user.id)
    await message.answer(
        "✅ <b>Murojaatingiz qabul qilindi!</b>\n\n"
        f"Murojaat raqami: <b>#{appeal_id}</b>\n"
        "Murojaatingiz maktab rahbariyati va kadrlar bo'limiga yetkazildi. Tez orada ko'rib chiqiladi.",
        reply_markup=main_menu_kb(staff_info=staff),
        parse_mode="HTML"
    )

    # Barcha rahbarlar (Direktor, Admin, Menejer)ga xabarnoma yuboramiz
    staff_user_ids = await get_all_staff_user_ids()
    appeal_alert = (
        "📩 <b>YANGI MUROJAAT KELIB TUSHDI!</b>\n\n"
        f"Murojaat raqami: <b>#{appeal_id}</b>\n"
        f"👤 <b>Yuboruvchi:</b> {full_name}\n"
        f"📱 <b>Telefon:</b> {phone}\n"
        f"🆔 <b>Telegram ID:</b> <code>{message.from_user.id}</code>\n"
        f"🕒 <b>Vaqt:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"💬 <b>Murojaat matni:</b>\n{feedback_text}"
    )

    reply_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Javob berish", callback_data=f"reply_appeal_{appeal_id}_{message.from_user.id}")]
    ])

    for s_id in staff_user_ids:
        try:
            await bot.send_message(
                chat_id=s_id,
                text=appeal_alert,
                reply_markup=reply_kb,
                parse_mode="HTML"
            )
        except Exception:
            pass

@router.message(F.text == "❌ Ariza topshirishni bekor qilish")
async def cancel_anytime(message: Message, state: FSMContext):
    data = await state.get_data()
    candidate_id = data.get("candidate_id")
    if candidate_id:
        await cancel_candidate_draft(candidate_id)
    await state.clear()
    
    user = await get_user_by_id(message.from_user.id)
    role = user.get("role", "candidate") if user else "candidate"
    
    if role in ("admin", "menejer", "direktor"):
        kb = admin_main_kb(role=role)
    else:
        kb = main_menu_kb()

    await message.answer(
        "❌ Ariza topshirish jarayoni bekor qilindi. Barcha kiritilgan ma'lumotlar o'chirildi.",
        reply_markup=kb
    )
