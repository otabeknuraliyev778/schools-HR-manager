import os
from pathlib import Path
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS, UPLOAD_DIR
from states import ApplicationStates
from database import (
    get_vacancy_by_id,
    get_or_create_draft_candidate,
    update_candidate_field,
    finalize_candidate_submission,
    cancel_candidate_draft,
    add_candidate_document,
    get_candidate_by_id,
    get_candidate_documents,
    get_all_staff_user_ids,
    get_staff_by_user_id,
    get_user_by_id
)
from keyboards.candidate import (
    phone_request_kb,
    category_inline_kb,
    skip_doc_kb,
    confirm_application_kb,
    main_menu_kb,
    cancel_reply_kb
)
from keyboards.admin import candidate_action_kb
from services.sheets import sync_candidate_to_google_sheet

router = Router()

# --- 1. ARIZA TOPSHIRISHNI BOSHLASH ---

@router.callback_query(F.data.startswith("apply_"))
async def start_application(callback: CallbackQuery, state: FSMContext):
    vacancy_id = int(callback.data.split("_")[1])
    vacancy = await get_vacancy_by_id(vacancy_id)
    if not vacancy:
        await callback.answer("Vakansiya topilmadi!", show_alert=True)
        return

    # Draft yaratamiz yoki mavjudini olamiz
    candidate_id = await get_or_create_draft_candidate(callback.from_user.id)
    await update_candidate_field(candidate_id, "vacancy_id", vacancy_id)
    
    # Foydalanuvchining avval kiritgan telefon raqamini olamiz
    user = await get_user_by_id(callback.from_user.id)
    phone = user.get("phone", "") if user else ""
    if phone:
        await update_candidate_field(candidate_id, "phone", phone)

    await state.update_data(
        candidate_id=candidate_id,
        vacancy_id=vacancy_id,
        vacancy_title=vacancy["title"],
        phone=phone
    )
    await state.set_state(ApplicationStates.waiting_full_name)

    alert_text = (
        f"📝 <b>«{vacancy['title']}»</b> lavozimi bo'yicha ariza topshirish boshlandi.\n\n"
        "⚠️ <b>DIQQAT:</b>\n"
        "<i>Siz har bir bosqichda so'ralgan ma'lumot va hujjatlarni to'liq taqdim etishingiz kerak. "
        "Eng so'nggi bosqichda <b>«Tasdiqlash va yuborish»</b> tugmasi bosilmaguncha, arizangiz kadrlar bo'limiga "
        "YUBORILMAYDI va ko'rib chiqilmaydi!</i>\n\n"
        "1️⃣-qadam: <b>Familiyangiz, Ismingiz va Sharifingizni (F.I.SH)</b> to'liq kiriting:\n"
        "<i>(Masalan: Karimov Jasur Akmalovich)</i>"
    )
    await callback.message.delete()
    await callback.message.answer(alert_text, reply_markup=cancel_reply_kb(), parse_mode="HTML")
    await callback.answer()

# --- 2. F.I.SH ---

@router.message(ApplicationStates.waiting_full_name)
async def process_full_name(message: Message, state: FSMContext):
    if message.text == "❌ Ariza topshirishni bekor qilish":
        data = await state.get_data()
        await cancel_candidate_draft(data.get("candidate_id"))
        await state.clear()
        user = await get_user_by_id(message.from_user.id)
        role = user.get("role", "candidate") if user else "candidate"
        kb = admin_main_kb(role=role) if role in ("admin", "menejer", "direktor") else main_menu_kb()
        await message.answer("Ariza bekor qilindi.", reply_markup=kb)
        return

    full_name = message.text.strip()
    if len(full_name.split()) < 2:
        await message.answer("Iltimos, ism va familiyangizni to'liq kiriting (kamida 2 ta so'z):")
        return

    data = await state.get_data()
    candidate_id = data["candidate_id"]
    await update_candidate_field(candidate_id, "full_name", full_name)
    await state.update_data(full_name=full_name)

    phone = data.get("phone", "")
    if phone:
        # Telefon allaqachon ma'lum - to'g'ridan-to'g'ri tug'ilgan sanaga o'tamiz
        await state.set_state(ApplicationStates.waiting_birth_date)
        await message.answer(
            f"✅ Telefon raqamingiz: <b>{phone}</b>\n\n"
            "2️⃣-qadam: <b>Tug'ilgan sanangizni kiriting:</b>\n"
            "<i>(Masalan: 14.05.1992)</i>",
            reply_markup=cancel_reply_kb(),
            parse_mode="HTML"
        )
    else:
        # Agar telefon mavjud bo'lmasa, so'raymiz
        await state.set_state(ApplicationStates.waiting_phone)
        await message.answer(
            "2️⃣-qadam: <b>Telefon raqamingizni yuboring:</b>\n"
            "Quyidagi <b>«📱 Telefon raqamimni ulashish»</b> tugmasini bosing:",
            reply_markup=phone_request_kb(),
            parse_mode="HTML"
        )

# --- 3. TELEFON RAQAM ---

@router.message(ApplicationStates.waiting_phone, F.contact)
@router.message(ApplicationStates.waiting_phone, F.text)
async def process_phone(message: Message, state: FSMContext):
    if message.text == "❌ Ariza topshirishni bekor qilish":
        data = await state.get_data()
        await cancel_candidate_draft(data.get("candidate_id"))
        await state.clear()
        staff = await get_staff_by_user_id(message.from_user.id)
        await message.answer("Ariza bekor qilindi.", reply_markup=main_menu_kb(staff_info=staff))
        return

    phone = ""
    if message.contact:
        phone = message.contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone
    else:
        phone = message.text.strip()
        if len(phone) < 9:
            await message.answer("Iltimos, haqiqiy telefon raqamingizni kiriting:")
            return

    data = await state.get_data()
    candidate_id = data["candidate_id"]
    await update_candidate_field(candidate_id, "phone", phone)
    await state.update_data(phone=phone)

    await state.set_state(ApplicationStates.waiting_birth_date)
    await message.answer(
        "3️⃣-qadam: <b>Tug'ilgan sanangizni kiriting:</b>\n"
        "<i>(Masalan: 14.05.1992)</i>",
        reply_markup=cancel_reply_kb(),
        parse_mode="HTML"
    )

# --- 4. TUG'ILGAN SANA ---

@router.message(ApplicationStates.waiting_birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    birth_date = message.text.strip()
    data = await state.get_data()
    candidate_id = data["candidate_id"]
    await update_candidate_field(candidate_id, "birth_date", birth_date)
    await state.update_data(birth_date=birth_date)

    await state.set_state(ApplicationStates.waiting_education)
    await message.answer(
        "4️⃣-qadam: <b>Ma'lumotingiz va tamomlagan oliy ta'lim muassasasi (OTM):</b>\n"
        "<i>(Masalan: Oliy, Toshkent davlat pedagogika universiteti, Matematika-informatika yo'nalishi)</i>",
        parse_mode="HTML"
    )

# --- 5. OTM VA MA'LUMOT ---

@router.message(ApplicationStates.waiting_education)
async def process_education(message: Message, state: FSMContext):
    education = message.text.strip()
    data = await state.get_data()
    candidate_id = data["candidate_id"]
    await update_candidate_field(candidate_id, "education", education)
    await state.update_data(education=education)

    await state.set_state(ApplicationStates.waiting_category)
    await message.answer(
        "5️⃣-qadam: <b>Malaka toifangizni tanlang:</b>",
        reply_markup=category_inline_kb(),
        parse_mode="HTML"
    )

# --- 6. TOIFA ---

@router.callback_query(ApplicationStates.waiting_category, F.data.startswith("cat_"))
async def process_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("_")[1]
    data = await state.get_data()
    candidate_id = data["candidate_id"]
    await update_candidate_field(candidate_id, "category", category)
    await state.update_data(category=category)

    await state.set_state(ApplicationStates.waiting_experience)
    await callback.message.edit_text(
        f"Tanlangan toifa: <b>{category}</b>\n\n"
        "6️⃣-qadam: <b>Pedagogik (yoki umumiy) ish stajingiz necha yil?</b>\n"
        "<i>(Masalan: 3 yil yoki 7 yil)</i>",
        parse_mode="HTML"
    )
    await callback.answer()

# --- 7. ISH STAJI ---

@router.message(ApplicationStates.waiting_experience)
async def process_experience(message: Message, state: FSMContext):
    experience = message.text.strip()
    data = await state.get_data()
    candidate_id = data["candidate_id"]
    await update_candidate_field(candidate_id, "experience", experience)
    await state.update_data(experience=experience)

    await state.set_state(ApplicationStates.waiting_passport)
    await message.answer(
        "📁 <b>HUJJATLARNI YUKLASH BOSQICHI:</b>\n\n"
        "7️⃣-qadam: <b>Pasport yoki ID-kartangiz nusxasini yuboring (Majburiy):</b>\n"
        "<i>(Hujjatni PDF yoki sifatli rasm ko'rinishida yuboring)</i>",
        parse_mode="HTML"
    )

# --- YORDAMCHI: FAYL SAQLASH FUNKSIYASI ---

async def save_telegram_file(bot: Bot, message: Message, candidate_id: int, doc_type: str) -> tuple[str, str, str]:
    cand_dir = UPLOAD_DIR / f"candidate_{candidate_id}"
    cand_dir.mkdir(parents=True, exist_ok=True)
    
    file_id = ""
    file_unique_id = ""
    file_name = ""
    
    if message.document:
        file_id = message.document.file_id
        file_unique_id = message.document.file_unique_id
        file_name = message.document.file_name or f"{doc_type}_{file_unique_id}.pdf"
    elif message.photo:
        photo = message.photo[-1]
        file_id = photo.file_id
        file_unique_id = photo.file_unique_id
        file_name = f"{doc_type}_{file_unique_id}.jpg"
        
    local_path = cand_dir / file_name
    try:
        file_info = await bot.get_file(file_id)
        await bot.download_file(file_info.file_path, destination=local_path)
    except Exception as e:
        # Faylni yuklab ololmasa ham file_id saqlanadi
        local_path = Path("")
        
    await add_candidate_document(
        candidate_id=candidate_id,
        doc_type=doc_type,
        file_id=file_id,
        file_unique_id=file_unique_id,
        file_name=file_name,
        file_path=str(local_path)
    )
    return file_id, file_name, str(local_path)

# --- 8. PASPORT (MAJBURIY) ---

@router.message(ApplicationStates.waiting_passport, F.document | F.photo)
async def process_passport(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    candidate_id = data["candidate_id"]
    await save_telegram_file(bot, message, candidate_id, "passport")

    await state.set_state(ApplicationStates.waiting_diploma)
    await message.answer(
        "✅ Pasport nusxasi qabul qilindi.\n\n"
        "8️⃣-qadam: <b>Diplom va uning baholar ilovasi (Majburiy):</b>\n"
        "<i>(Diplom va ilovasini PDF yoki sifatli rasm sifatida yuboring)</i>",
        parse_mode="HTML"
    )

@router.message(ApplicationStates.waiting_passport)
async def invalid_passport(message: Message):
    await message.answer("⚠️ Iltimos, pasport yoki ID-kartangizni rasm yoki PDF fayl ko'rinishida yuboring.")

# --- 9. DIPLOM (MAJBURIY) ---

@router.message(ApplicationStates.waiting_diploma, F.document | F.photo)
async def process_diploma(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    candidate_id = data["candidate_id"]
    await save_telegram_file(bot, message, candidate_id, "diploma")

    await state.set_state(ApplicationStates.waiting_resume)
    await message.answer(
        "✅ Diplom nusxasi qabul qilindi.\n\n"
        "9️⃣-qadam: <b>Rezyume / Obyektivka (CV) (Majburiy):</b>\n"
        "<i>(PDF, Word yoki rasm ko'rinishida yuboring)</i>",
        parse_mode="HTML"
    )

@router.message(ApplicationStates.waiting_diploma)
async def invalid_diploma(message: Message):
    await message.answer("⚠️ Iltimos, diplom nusxasini rasm yoki PDF fayl ko'rinishida yuboring.")

# --- 10. REZYUME (MAJBURIY) ---

@router.message(ApplicationStates.waiting_resume, F.document | F.photo)
async def process_resume(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    candidate_id = data["candidate_id"]
    await save_telegram_file(bot, message, candidate_id, "resume")

    cand = await get_candidate_by_id(candidate_id)
    is_cert_mandatory = cand.get("is_cert_mandatory", 0) if cand else 0

    await state.set_state(ApplicationStates.waiting_cert_file)
    if is_cert_mandatory == 1:
        await message.answer(
            "✅ Rezyume qabul qilindi.\n\n"
            "🔟-qadam: <b>Til yoki Fan sertifikatlari (🔴 MAJBURIY):</b>\n"
            "<i>(Ushbu vakansiya uchun sertifikat talabi majburiy etib belgilangan. "
            "Iltimos, sertifikatingizni rasm yoki PDF hujjat shaklida yuboring)</i>",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "✅ Rezyume qabul qilindi.\n\n"
            "🔟-qadam: <b>Til yoki Fan sertifikatlari (🟢 Ixtiyoriy):</b>\n"
            "<i>(IELTS, CEFR, Milliy sertifikat kabilarni rasm yoki PDF sifatida yuboring. Agar mavjud bo'lmasa, quyidagi tugmani bosing)</i>",
            reply_markup=skip_doc_kb("cert"),
            parse_mode="HTML"
        )

@router.message(ApplicationStates.waiting_resume)
async def invalid_resume(message: Message):
    await message.answer("⚠️ Iltimos, rezyumengizni fayl yoki rasm ko'rinishida yuboring.")

# --- 11. SERTIFIKAT (MAJBURIY YOKI IXTIYORIY) ---

@router.message(ApplicationStates.waiting_cert_file, F.document | F.photo)
async def process_cert_file(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    candidate_id = data["candidate_id"]
    caption = message.caption or "Sertifikat mavjud"
    await save_telegram_file(bot, message, candidate_id, "certificate")
    await update_candidate_field(candidate_id, "cert_info", caption)

    await state.set_state(ApplicationStates.waiting_degree_file)
    await message.answer(
        "✅ Sertifikat qabul qilindi.\n\n"
        "1️⃣1️⃣-qadam: <b>Ilmiy daraja hujjati (PhD, DSc, Magistr) (Ixtiyoriy):</b>\n"
        "<i>(Mavjud bo'lsa yuboring, bo'lmasa o'tkazib yuboring)</i>",
        reply_markup=skip_doc_kb("degree"),
        parse_mode="HTML"
    )

@router.callback_query(ApplicationStates.waiting_cert_file, F.data == "skip_cert")
async def skip_cert_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    candidate_id = data["candidate_id"]
    cand = await get_candidate_by_id(candidate_id)
    is_cert_mandatory = cand.get("is_cert_mandatory", 0) if cand else 0

    if is_cert_mandatory == 1:
        await callback.answer("⚠️ Ushbu vakansiya uchun sertifikat yuklash majburiy! Uni o'tkazib yubora olmaysiz.", show_alert=True)
        return

    await update_candidate_field(candidate_id, "cert_info", "Mavjud emas")

    await state.set_state(ApplicationStates.waiting_degree_file)
    await callback.message.edit_text(
        "1️⃣1️⃣-qadam: <b>Ilmiy daraja hujjati (PhD, DSc, Magistr) (Ixtiyoriy):</b>\n"
        "<i>(Mavjud bo'lsa yuboring, bo'lmasa o'tkazib yuboring)</i>",
        reply_markup=skip_doc_kb("degree"),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(ApplicationStates.waiting_cert_file)
async def invalid_cert(message: Message, state: FSMContext):
    data = await state.get_data()
    candidate_id = data.get("candidate_id")
    cand = await get_candidate_by_id(candidate_id) if candidate_id else None
    is_cert_mandatory = cand.get("is_cert_mandatory", 0) if cand else 0

    if is_cert_mandatory == 1:
        await message.answer(
            "⚠️ <b>Ushbu vakansiya uchun sertifikat yuklash MAJBURIY!</b>\n"
            "Iltimos, sertifikatingizni rasm yoki PDF fayl ko'rinishida yuboring.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "⚠️ Iltimos, sertifikatni rasm yoki PDF fayl ko'rinishida yuboring yoki quyidagi tugma orqali o'tkazib yuboring:",
            reply_markup=skip_doc_kb("cert")
        )

# --- 12. ILMIY DARAJA (IXTIYORIY) ---

@router.message(ApplicationStates.waiting_degree_file, F.document | F.photo)
async def process_degree_file(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    candidate_id = data["candidate_id"]
    caption = message.caption or "Ilmiy daraja mavjud"
    await save_telegram_file(bot, message, candidate_id, "academic_degree")
    await update_candidate_field(candidate_id, "academic_degree_info", caption)
    await show_final_confirmation(message, state, candidate_id)

@router.callback_query(ApplicationStates.waiting_degree_file, F.data == "skip_degree")
async def skip_degree_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    candidate_id = data["candidate_id"]
    await update_candidate_field(candidate_id, "academic_degree_info", "Mavjud emas")
    await show_final_confirmation(callback.message, state, candidate_id)
    await callback.answer()

# --- 13. YAKUNIY KO'RIB CHIQISH VA TASDIQLASH ---

async def show_final_confirmation(message_or_event, state: FSMContext, candidate_id: int):
    cand = await get_candidate_by_id(candidate_id)
    docs = await get_candidate_documents(candidate_id)
    doc_types = [d["doc_type"] for d in docs]
    passport_status = "✅ Yuklandi" if "passport" in doc_types else "❌ Yuklanmagan"
    diploma_status = "✅ Yuklandi" if "diploma" in doc_types else "❌ Yuklanmagan"
    resume_status = "✅ Yuklandi" if "resume" in doc_types else "❌ Yuklanmagan"
    cert_status = "✅ Yuklandi" if "certificate" in doc_types else "—"
    degree_status = "✅ Yuklandi" if "academic_degree" in doc_types else "—"

    cert_info = cand.get("cert_info") or "Mavjud emas"
    degree_info = cand.get("academic_degree_info") or "Mavjud emas"

    summary_text = (
        "📋 <b>ARIZANGIZ MA'LUMOTLARI BILAN TANISHING:</b>\n\n"
        f"👤 <b>F.I.SH:</b> {cand.get('full_name')}\n"
        f"📱 <b>Telefon raqam:</b> {cand.get('phone')}\n"
        f"🎂 <b>Tug'ilgan sana:</b> {cand.get('birth_date')}\n"
        f"📌 <b>Tanlangan vakansiya:</b> {cand.get('vacancy_title')}\n"
        f"🎓 <b>Ma'lumoti / OTM:</b> {cand.get('education')}\n"
        f"🏆 <b>Toifasi:</b> {cand.get('category')}\n"
        f"⏳ <b>Ish staji:</b> {cand.get('experience')}\n"
        f"📜 <b>Sertifikatlar:</b> {cert_info}\n"
        f"🏛 <b>Ilmiy daraja:</b> {degree_info}\n\n"
        "<b>Yuklangan hujjatlar:</b>\n"
        f"• Pasport / ID-karta: {passport_status}\n"
        f"• Diplom va ilovasi: {diploma_status}\n"
        f"• Rezyume / CV: {resume_status}\n"
        f"• Sertifikat fayli: {cert_status}\n"
        f"• Ilmiy daraja hujjati: {degree_status}\n\n"
        "⚠️ <b>DIQQAT:</b> <i>Barcha ma'lumotlar to'g'riligini tasdiqlaysizmi? "
        "«Tasdiqlash va yuborish» tugmasini bossangizgina arizangiz kadrlar bo'limi menejeriga yuboriladi!</i>"
    )

    await state.set_state(ApplicationStates.confirm_submission)
    if isinstance(message_or_event, Message):
        await message_or_event.answer(summary_text, reply_markup=confirm_application_kb(), parse_mode="HTML")
    else:
        await message_or_event.edit_text(summary_text, reply_markup=confirm_application_kb(), parse_mode="HTML")

# --- 14. TASDIQLASH VA YUBORISH ---

@router.callback_query(ApplicationStates.confirm_submission, F.data == "confirm_final_submit")
async def confirm_submission_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    candidate_id = data["candidate_id"]
    
    # Arizani bazada rasmiylashtiramiz (status = 'submitted')
    await finalize_candidate_submission(candidate_id)
    cand = await get_candidate_by_id(candidate_id)

    # 1. Nomzodga xushxabar
    congrats_text = (
        f"🎉 <b>Arizangiz muvaffaqiyatli qabul qilindi!</b>\n\n"
        f"Sizning ariza raqamingiz: <b>#{candidate_id}</b>\n\n"
        "Hujjatlaringiz maktabimiz Kadrlar bo'limi menejeriga ko'rib chiqish uchun yuborildi.\n"
        "Arizangiz ko'rib chiqilgach, suhbat sanasi va natijasi haqida ushbu bot orqali "
        "sizga avtomatik xabar yetkaziladi.\n\n"
        "<i>E'tiboringiz va qiziqishingiz uchun tashakkur!</i>"
    )
    await callback.message.edit_text(congrats_text, parse_mode="HTML")
    await state.clear()
    await callback.answer()

    # 2. Xodimlar, Menejer va Direktorga darhol xabarnoma yuborish
    docs = await get_candidate_documents(candidate_id)
    doc_titles = {
        "passport": "Pasport",
        "diploma": "Diplom",
        "resume": "Rezyume",
        "certificate": "Sertifikat",
        "academic_degree": "Ilmiy daraja"
    }
    docs_summary = [doc_titles.get(d["doc_type"], d["doc_type"]) for d in docs]
    docs_str = ", ".join(docs_summary) if docs_summary else "Hujjatlar biriktirilmagan"

    admin_alert_text = (
        "🔔 <b>YANGI NOMZOD HUJJAT TOPSHIRDI!</b>\n\n"
        f"Ariza ID: <b>#{cand['id']}</b>\n"
        f"📌 Vakansiya: <b>{cand['vacancy_title']}</b>\n"
        f"👤 F.I.SH: <b>{cand['full_name']}</b>\n"
        f"📱 Telefon: <b>{cand['phone']}</b>\n"
        f"🎂 Tug'ilgan sana: {cand['birth_date']}\n"
        f"🎓 Ma'lumoti: {cand['education']}\n"
        f"🏆 Toifasi: <b>{cand['category']}</b>\n"
        f"⏳ Staji: {cand['experience']}\n"
        f"📜 Sertifikat: {cand.get('cert_info', '-')}\n"
        f"📁 Yuklangan hujjatlar: {docs_str}\n"
        f"🕒 Topshirilgan vaqt: {cand['submitted_at']}"
    )

    staff_user_ids = await get_all_staff_user_ids()
    recipient_ids = set(staff_user_ids)

    for r_id in recipient_ids:
        try:
            await bot.send_message(
                chat_id=r_id,
                text=admin_alert_text,
                reply_markup=candidate_action_kb(candidate_id, "submitted"),
                parse_mode="HTML"
            )
        except Exception:
            pass

    # 3. Google Sheets bilan sinxronlash
    try:
        await sync_candidate_to_google_sheet(cand)
    except Exception as e:
        pass

# --- 15. BEKOR QILISH ---

@router.callback_query(F.data == "cancel_application")
async def cancel_callback_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    candidate_id = data.get("candidate_id")
    if candidate_id:
        await cancel_candidate_draft(candidate_id)
    await state.clear()

    await callback.message.edit_text(
        "❌ Ariza topshirish bekor qilindi. Barcha kiritilgan ma'lumotlar o'chirildi."
    )
    await callback.answer()
