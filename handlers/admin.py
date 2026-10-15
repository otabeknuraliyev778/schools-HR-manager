import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS, BASE_DIR
from states import AdminStates
from database import (
    get_submitted_candidates,
    get_candidate_by_id,
    get_candidate_documents,
    update_candidate_status,
    get_all_vacancies,
    toggle_vacancy_status,
    delete_vacancy,
    add_vacancy,
    get_staff_by_user_id,
    reply_to_appeal
)
from keyboards.admin import (
    admin_main_kb,
    candidates_list_inline_kb,
    candidate_action_kb,
    vacancies_manage_kb,
    admin_cancel_inline_kb
)
from keyboards.candidate import main_menu_kb
from services.excel import generate_candidates_excel

router = Router()

async def get_current_staff(user_id: int) -> Optional[Dict[str, Any]]:
    return await get_staff_by_user_id(user_id)

# --- 1. BOSHQARUV PANELIGA KIRISH ---

@router.message(F.text.in_({"🔐 Kadrlar Menejeri Paneli", "👨‍💻 Administrator Paneli", "🏛 Direktor Boshqaruv Paneli", "📋 Kadrlar Menejeri Paneli"}))
async def open_staff_panel(message: Message):
    staff = await get_current_staff(message.from_user.id)
    if not staff:
        await message.answer("Sizda boshqaruv paneliga kirish huquqi mavjud emas. Iltimos, avval ro'yxatdan o'ting.")
        return

    title = staff.get("title", "Boshqaruv")
    await message.answer(
        f"🔐 <b>{title} boshqaruv paneli:</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang:",
        reply_markup=admin_main_kb(role=staff.get("role", "menejer")),
        parse_mode="HTML"
    )

@router.message(F.text == "👤 Nomzod rejimiga o'tish")
async def switch_to_candidate_mode(message: Message):
    staff = await get_current_staff(message.from_user.id)
    await message.answer(
        "Asosiy foydalanuvchi menyusiga qaytdingiz.",
        reply_markup=main_menu_kb(staff_info=staff)
    )

@router.message(F.text == "🚪 Tizimdan chiqish")
async def logout_staff(message: Message, state: FSMContext):
    await state.clear()
    staff = await get_current_staff(message.from_user.id)
    await message.answer(
        "Siz boshqaruv panelidan chiqdingiz.\n"
        "Qayta kirish uchun /start buyrug'ini yuboring.",
        reply_markup=main_menu_kb(staff_info=staff)
    )

# --- 2. MONITORING VA STATISTIKA (DIREKTOR VA MA'MURIYAT UCHUN) ---

@router.message(F.text == "📈 Monitoring & Statistika")
async def view_statistics(message: Message):
    staff = await get_current_staff(message.from_user.id)
    if not staff:
        return

    all_cand = await get_submitted_candidates()
    vacancies = await get_all_vacancies()

    total = len(all_cand)
    new_c = sum(1 for c in all_cand if c["status"] == "submitted")
    inter_c = sum(1 for c in all_cand if c["status"] == "interview")
    res_c = sum(1 for c in all_cand if c["status"] == "reserve")
    rej_c = sum(1 for c in all_cand if c["status"] == "rejected")

    active_vac_count = sum(1 for v in vacancies if v["is_active"] == 1)

    text = (
        "📈 <b>Ixtisoslashgan maktab kadrlar monitoringi va statistikasi:</b>\n\n"
        f"📊 <b>Jami kelib tushgan arizalar:</b> {total} ta\n"
        f"🟡 <b>Yangi (ko'rib chiqilmoqda):</b> {new_c} ta\n"
        f"🟢 <b>Suhbatga chaqirilganlar:</b> {inter_c} ta\n"
        f"🟠 <b>Kadrlar zaxirasida:</b> {res_c} ta\n"
        f"🔴 <b>Rad etilganlar:</b> {rej_c} ta\n\n"
        f"📌 <b>Ochiq (faol) vakansiyalar:</b> {active_vac_count} ta\n\n"
        "<i>To'liq tafsilotlar uchun «Excel hisobot yuklash» tugmasidan foydalanishingiz mumkin.</i>"
    )
    await message.answer(text, parse_mode="HTML")

# --- 3. ARIZALARNI KO'RISH ---

@router.message(F.text == "📥 Yangi kelgan arizalar")
async def view_new_candidates(message: Message):
    staff = await get_current_staff(message.from_user.id)
    if not staff:
        return

    candidates = await get_submitted_candidates(status="submitted")
    if not candidates:
        await message.answer("📥 Hozirda yangi (ko'rib chiqilmagan) arizalar mavjud emas.")
        return

    await message.answer(
        f"📥 <b>Yangi topshirilgan arizalar soni: {len(candidates)} ta</b>\n"
        "Nomzod ma'lumotlarini batafsil ko'rish uchun tanlang:",
        reply_markup=candidates_list_inline_kb(candidates),
        parse_mode="HTML"
    )

@router.message(F.text == "📊 Barcha arizalar")
async def view_all_candidates(message: Message):
    staff = await get_current_staff(message.from_user.id)
    if not staff:
        return

    candidates = await get_submitted_candidates()
    if not candidates:
        await message.answer("📊 Hozircha topshirilgan rasmiy arizalar mavjud emas.")
        return

    await message.answer(
        f"📊 <b>Barcha topshirilgan arizalar soni: {len(candidates)} ta</b>\n"
        "Batafsil ko'rish uchun arizani tanlang:",
        reply_markup=candidates_list_inline_kb(candidates),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("adm_cand_"))
async def show_candidate_details(callback: CallbackQuery):
    staff = await get_current_staff(callback.from_user.id)
    if not staff:
        await callback.answer("Kirish huquqi yo'q!", show_alert=True)
        return

    candidate_id = int(callback.data.split("_")[2])
    cand = await get_candidate_by_id(candidate_id)
    if not cand:
        await callback.answer("Ariza topilmadi!", show_alert=True)
        return

    status_labels = {
        "submitted": "🟡 Yangi (ko'rib chiqilmoqda)",
        "interview": "🟢 Suhbatga chaqirilgan",
        "reserve": "🟠 Kadrlar zaxirasida",
        "rejected": "🔴 Rad etilgan"
    }

    docs = await get_candidate_documents(candidate_id)
    doc_titles = {
        "passport": "Pasport / ID-karta",
        "diploma": "Diplom va baholar ilovasi",
        "resume": "Rezyume / CV",
        "certificate": "Sertifikat",
        "academic_degree": "Ilmiy daraja hujjati"
    }

    docs_lines = []
    for d in docs:
        dtype = d.get("doc_type", "")
        title = doc_titles.get(dtype, dtype)
        fname = d.get("file_name", "Fayl biriktirilgan")
        docs_lines.append(f"• <b>{title}:</b> <code>{fname}</code> ✅")

    if docs_lines:
        docs_text = f"\n📁 <b>Nomzodning yuklangan hujjatlari ({len(docs)} ta):</b>\n" + "\n".join(docs_lines) + "\n"
    else:
        docs_text = "\n📁 <b>Nomzodning yuklangan hujjatlari:</b> <i>Hujjatlar biriktirilmagan</i>\n"

    text = (
        f"📋 <b>NOMZOD MA'LUMOTLARI (#ID: {cand['id']})</b>\n\n"
        f"👤 <b>F.I.SH:</b> {cand.get('full_name')}\n"
        f"📌 <b>Vakansiya:</b> {cand.get('vacancy_title')}\n"
        f"📱 <b>Telefon:</b> {cand.get('phone')}\n"
        f"🎂 <b>Tug'ilgan sana:</b> {cand.get('birth_date')}\n"
        f"🎓 <b>OTM va ma'lumoti:</b> {cand.get('education')}\n"
        f"🏆 <b>Toifasi:</b> {cand.get('category')}\n"
        f"⏳ <b>Ish staji:</b> {cand.get('experience')}\n"
        f"📜 <b>Sertifikatlar:</b> {cand.get('cert_info', 'Mavjud emas')} ({'🔴 Majburiy' if cand.get('is_cert_mandatory') == 1 else '🟢 Ixtiyoriy'})\n"
        f"🏛 <b>Ilmiy daraja:</b> {cand.get('academic_degree_info', 'Mavjud emas')}\n"
        f"🚦 <b>Hozirgi holati:</b> {status_labels.get(cand.get('status'), cand.get('status'))}\n"
        f"🕒 <b>Topshirilgan vaqt:</b> {cand.get('submitted_at')}\n"
        f"{docs_text}"
    )
    if cand.get("action_by_name"):
        text += (
            f"\n⚡ <b>Oxirgi amalni bajargan:</b> {cand['action_by_name']}\n"
            f"🕒 <b>Amal bajarilgan vaqt:</b> {cand.get('action_at', '-')}\n"
        )
    if cand.get("admin_notes"):
        text += f"📝 <b>Izoh / Xulosa:</b> {cand['admin_notes']}\n"

    await callback.message.edit_text(
        text,
        reply_markup=candidate_action_kb(candidate_id, cand.get("status", "submitted"), role=staff.get("role", "menejer")),
        parse_mode="HTML"
    )
    await callback.answer()

# --- 4. HUJJATLARNI KO'RISH VA YUKLAB BERISH ---

@router.callback_query(F.data.startswith("adm_docs_"))
async def send_candidate_docs(callback: CallbackQuery, bot: Bot):
    staff = await get_current_staff(callback.from_user.id)
    if not staff:
        await callback.answer("Kirish huquqi mavjud emas!", show_alert=True)
        return

    candidate_id = int(callback.data.split("_")[2])
    cand = await get_candidate_by_id(candidate_id)
    docs = await get_candidate_documents(candidate_id)

    if not docs:
        await callback.answer("Ushbu nomzodga tegishli hujjatlar topilmadi!", show_alert=True)
        return

    await callback.answer("Hujjatlar yuborilmoqda...")
    await callback.message.answer(
        f"📁 <b>Nomzod {cand.get('full_name')} ning yuklangan hujjatlari ({len(docs)} ta):</b>",
        parse_mode="HTML"
    )

    doc_titles = {
        "passport": "Pasport / ID-karta nusxasi",
        "diploma": "Diplom va baholar ilovasi",
        "resume": "Rezyume / CV",
        "certificate": "Sertifikat",
        "academic_degree": "Ilmiy daraja hujjati"
    }

    for d in docs:
        caption = f"📄 <b>{doc_titles.get(d['doc_type'], d['doc_type'])}</b>\nNomzod: {cand.get('full_name')}"
        file_path_str = d.get("file_path", "")
        file_path = Path(file_path_str) if file_path_str else None
        
        sent = False
        # 1. Agar lokal fayl diskda mavjud bo'lsa
        if file_path and file_path.is_file():
            try:
                input_file = FSInputFile(str(file_path), filename=d.get("file_name"))
                await bot.send_document(
                    chat_id=callback.from_user.id,
                    document=input_file,
                    caption=caption,
                    parse_mode="HTML"
                )
                sent = True
            except Exception:
                pass
        
        # 2. Telegram file_id orqali yuborish
        if not sent and d.get("file_id"):
            try:
                await bot.send_document(
                    chat_id=callback.from_user.id,
                    document=d["file_id"],
                    caption=caption,
                    parse_mode="HTML"
                )
                sent = True
            except Exception:
                try:
                    await bot.send_photo(
                        chat_id=callback.from_user.id,
                        photo=d["file_id"],
                        caption=caption,
                        parse_mode="HTML"
                    )
                    sent = True
                except Exception:
                    pass

        if not sent:
            await callback.message.answer(
                f"⚠️ <b>{doc_titles.get(d['doc_type'], d['doc_type'])}</b> faylini yuklashda xatolik yuz berdi.",
                parse_mode="HTML"
            )

# --- 5. SUHBATGA CHAQIRISH ---

@router.callback_query(F.data.startswith("adm_action_interview_"))
async def start_interview_action(callback: CallbackQuery, state: FSMContext):
    staff = await get_current_staff(callback.from_user.id)
    if not staff:
        return

    candidate_id = int(callback.data.split("_")[3])
    await state.update_data(target_candidate_id=candidate_id)
    await state.set_state(AdminStates.waiting_interview_details)

    await callback.message.answer(
        f"📅 <b>Nomzodni (#ID: {candidate_id}) suhbatga chaqirish:</b>\n\n"
        "Nomzodga yuboriladigan xabarni (suhbat sanasi, soati, xona yoki havola) yozing:\n"
        "<i>(Masalan: 15-oktabr kuni soat 10:00 da maktabimizning 204-xonasiga shaxsingizni tasdiqlovchi hujjat bilan kelishingiz so'raladi.)</i>",
        reply_markup=admin_cancel_inline_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_interview_details)
async def process_interview_details(message: Message, state: FSMContext, bot: Bot):
    staff = await get_current_staff(message.from_user.id)
    if not staff:
        return

    details = message.text.strip()
    data = await state.get_data()
    candidate_id = data["target_candidate_id"]
    cand = await get_candidate_by_id(candidate_id)

    staff_title = staff.get("title", "Menejer")
    action_by_name = f"{staff_title} ({message.from_user.full_name})"
    action_by_role = staff.get("role", "menejer")

    await update_candidate_status(
        candidate_id,
        "interview",
        admin_notes=f"Suhbat: {details}",
        action_by_name=action_by_name,
        action_by_role=action_by_role
    )
    await state.clear()

    await message.answer(
        f"✅ Nomzod #{candidate_id} suhbatga chaqirildi va holati yangilandi.",
        reply_markup=admin_main_kb(role=staff.get("role", "menejer"))
    )

    try:
        user_msg = (
            "🎉 <b>XUSHXABAR! SIZ SUHBATGA TAKLIF ETILDINGIZ!</b>\n\n"
            f"Hurmatli <b>{cand.get('full_name')}</b>,\n"
            f"Sizning <b>«{cand.get('vacancy_title')}»</b> lavozimi bo'yicha topshirgan arizangiz "
            "maktabimiz kadrlar komissiyasi tomonidan ijobiy baholandi!\n\n"
            f"📍 <b>Suhbat ma'lumotlari:</b>\n{details}\n\n"
            "<i>Sizga saralash bosqichida muvaffaqiyat tilaymiz!</i>"
        )
        await bot.send_message(chat_id=cand["user_id"], text=user_msg, parse_mode="HTML")
    except Exception:
        await message.answer("⚠️ Nomzodga Telegram orqali xabar yetkazilmadi.")

# --- 6. ZAXIRAGA OLISH ---

@router.callback_query(F.data.startswith("adm_action_reserve_"))
async def process_reserve_action(callback: CallbackQuery, bot: Bot):
    staff = await get_current_staff(callback.from_user.id)
    if not staff:
        return

    candidate_id = int(callback.data.split("_")[3])
    cand = await get_candidate_by_id(candidate_id)

    staff_title = staff.get("title", "Menejer")
    action_by_name = f"{staff_title} ({callback.from_user.full_name})"
    action_by_role = staff.get("role", "menejer")

    await update_candidate_status(
        candidate_id,
        "reserve",
        admin_notes="Kadrlar zaxirasiga olindi",
        action_by_name=action_by_name,
        action_by_role=action_by_role
    )

    await callback.message.edit_text(
        f"🟡 Nomzod #{candidate_id} ({cand.get('full_name')}) kadrlar zaxirasiga olindi."
    )
    await callback.answer("Zaxiraga olindi")

    try:
        user_msg = (
            f"Hurmatli <b>{cand.get('full_name')}</b>,\n\n"
            f"Sizning <b>«{cand.get('vacancy_title')}»</b> bo'yicha arizangiz o'rganib chiqildi. "
            "Hujjatlaringiz maktabimizning iqtidorli <b>Kadrlar Zaxirasi</b>ga kiritildi.\n"
            "Qo'shimcha dars soatlari yoki yangi o'rinlar ochilganda siz bilan darhol bog'lanamiz."
        )
        await bot.send_message(chat_id=cand["user_id"], text=user_msg, parse_mode="HTML")
    except Exception:
        pass

# --- 7. RAD ETISH ---

@router.callback_query(F.data.startswith("adm_action_reject_"))
async def start_reject_action(callback: CallbackQuery, state: FSMContext):
    staff = await get_current_staff(callback.from_user.id)
    if not staff:
        return

    candidate_id = int(callback.data.split("_")[3])
    await state.update_data(target_candidate_id=candidate_id)
    await state.set_state(AdminStates.waiting_reject_reason)

    await callback.message.answer(
        f"🔴 <b>Nomzodni (#ID: {candidate_id}) rad etish:</b>\n\n"
        "Rad etish sababini kiriting (yoki standart javob uchun 'standart' deb yozing):",
        reply_markup=admin_cancel_inline_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_reject_reason)
async def process_reject_reason(message: Message, state: FSMContext, bot: Bot):
    staff = await get_current_staff(message.from_user.id)
    if not staff:
        return

    reason_text = message.text.strip()
    data = await state.get_data()
    candidate_id = data["target_candidate_id"]
    cand = await get_candidate_by_id(candidate_id)

    if reason_text.lower() == "standart":
        reason_explanation = "Afsuski, sizning ma'lumotlaringiz ushbu bo'sh ish o'rni uchun qo'yilgan mezonlarga to'liq mos kelmadi."
    else:
        reason_explanation = reason_text

    staff_title = staff.get("title", "Menejer")
    action_by_name = f"{staff_title} ({message.from_user.full_name})"
    action_by_role = staff.get("role", "menejer")

    await update_candidate_status(
        candidate_id,
        "rejected",
        admin_notes=f"Rad etildi: {reason_explanation}",
        action_by_name=action_by_name,
        action_by_role=action_by_role
    )
    await state.clear()

    await message.answer(f"🔴 Nomzod #{candidate_id} arizasi rad etildi.", reply_markup=admin_main_kb(role=staff.get("role", "menejer")))

    try:
        user_msg = (
            f"Hurmatli <b>{cand.get('full_name')}</b>,\n\n"
            f"Sizning <b>«{cand.get('vacancy_title')}»</b> lavozimi bo'yicha arizangiz ko'rib chiqildi.\n"
            f"<b>Xulosa:</b> {reason_explanation}\n\n"
            "Kelgusi pedagogik faoliyatingizda muvaffaqiyatlar tilaymiz!"
        )
        await bot.send_message(chat_id=cand["user_id"], text=user_msg, parse_mode="HTML")
    except Exception:
        pass

# --- 8. EXCEL HISOBOT YUKLAB OLISH ---

@router.message(F.text == "📑 Excel hisobot yuklash")
async def export_excel_report(message: Message):
    staff = await get_current_staff(message.from_user.id)
    if not staff:
        return

    candidates = await get_submitted_candidates()
    if not candidates:
        await message.answer("Excel eksport qilish uchun hali rasmiy arizalar mavjud emas.")
        return

    filename = f"nomzodlar_hisoboti_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    export_path = BASE_DIR / "uploads" / filename

    try:
        generate_candidates_excel(candidates, export_path)
        excel_file = FSInputFile(str(export_path), filename=filename)
        await message.answer_document(
            document=excel_file,
            caption=f"📊 <b>Ixtisoslashgan maktab nomzodlarining rasmiy hisoboti</b>\n\nJami nomzodlar soni: {len(candidates)} ta",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e}")

# --- 9. VAKANSIYALARNI BOSHQARISH (ADMIN VA MENEYER) ---

@router.message(F.text.in_({"⚙️ Vakansiyalarni boshqarish", "⚙️ Vakansiyalar holati"}))
async def manage_vacancies(message: Message):
    staff = await get_current_staff(message.from_user.id)
    if not staff:
        return

    vacancies = await get_all_vacancies()
    await message.answer(
        "⚙️ <b>Vakansiyalar bo'limi:</b>\n\n"
        "Mavjud barcha vakansiyalar holati (faol/nofaol):",
        reply_markup=vacancies_manage_kb(vacancies),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("adm_vac_toggle_"))
async def toggle_vacancy_handler(callback: CallbackQuery):
    staff = await get_current_staff(callback.from_user.id)
    if not staff:
        return

    vacancy_id = int(callback.data.split("_")[3])
    vacancies = await get_all_vacancies()
    target_vac = next((v for v in vacancies if v["id"] == vacancy_id), None)
    if target_vac:
        new_status = 0 if target_vac["is_active"] == 1 else 1
        await toggle_vacancy_status(vacancy_id, new_status)

    updated_vacancies = await get_all_vacancies()
    await callback.message.edit_reply_markup(reply_markup=vacancies_manage_kb(updated_vacancies))
    await callback.answer("Vakansiya holati yangilandi!")

@router.callback_query(F.data.startswith("adm_vac_del_"))
async def delete_vacancy_handler(callback: CallbackQuery):
    staff = await get_current_staff(callback.from_user.id)
    if not staff:
        return

    vacancy_id = int(callback.data.split("_")[3])
    await delete_vacancy(vacancy_id)
    updated_vacancies = await get_all_vacancies()
    await callback.message.edit_reply_markup(reply_markup=vacancies_manage_kb(updated_vacancies))
    await callback.answer("Vakansiya o'chirildi!")

@router.callback_query(F.data == "adm_vac_add")
async def add_new_vacancy_start(callback: CallbackQuery, state: FSMContext):
    staff = await get_current_staff(callback.from_user.id)
    if not staff:
        return

    await state.set_state(AdminStates.waiting_new_vacancy_title)
    await callback.message.answer(
        "➕ <b>Yangi vakansiya qo'shish:</b>\n\n"
        "1. Lavozim / Fan nomini kiriting:\n<i>(Masalan: Kimyo fani o'qituvchisi)</i>",
        reply_markup=admin_cancel_inline_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_new_vacancy_title)
async def process_new_vac_title(message: Message, state: FSMContext):
    await state.update_data(vac_title=message.text.strip())
    await state.set_state(AdminStates.waiting_new_vacancy_desc)
    await message.answer(
        "2. Ish tavsifi va sharoitlarini kiriting:\n<i>(Dars soati, sinflar, stavka va h.k.)</i>",
        parse_mode="HTML"
    )

@router.message(AdminStates.waiting_new_vacancy_desc)
async def process_new_vac_desc(message: Message, state: FSMContext):
    await state.update_data(vac_desc=message.text.strip())
    await state.set_state(AdminStates.waiting_new_vacancy_reqs)
    await message.answer(
        "3. Nomzodga qo'yiladigan talablarni kiriting:\n<i>(Ma'lumot, toifa, til sertifikatlari, staj...)</i>",
        parse_mode="HTML"
    )

@router.message(AdminStates.waiting_new_vacancy_reqs)
async def process_new_vac_reqs(message: Message, state: FSMContext):
    await state.update_data(vac_reqs=message.text.strip())
    await state.set_state(AdminStates.waiting_new_vacancy_cert_type)

    cert_choice_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Ha, sertifikat MAJBURIY", callback_data="vac_cert_mandatory_1")],
        [InlineKeyboardButton(text="🟢 Yo'q, sertifikat IXTIYORIY", callback_data="vac_cert_mandatory_0")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="adm_cancel_action")]
    ])

    await message.answer(
        "4. <b>Nomzod uchun malaka / til sertifikati talabi qanday bo'lsin?</b>\n\n"
        "• <b>🔴 Majburiy</b>: Nomzod sertifikat yuklamasdan arizani yakunlay olmaydi.\n"
        "• <b>🟢 Ixtiyoriy</b>: Agar sertifikati bo'lmasa, «O'tkazib yuborish» imkoniyati bo'ladi.",
        reply_markup=cert_choice_kb,
        parse_mode="HTML"
    )

@router.callback_query(AdminStates.waiting_new_vacancy_cert_type, F.data.startswith("vac_cert_mandatory_"))
async def process_new_vac_cert_type(callback: CallbackQuery, state: FSMContext):
    staff = await get_current_staff(callback.from_user.id)
    is_cert_mandatory = int(callback.data.split("_")[-1])
    data = await state.get_data()
    title = data["vac_title"]
    desc = data["vac_desc"]
    reqs = data["vac_reqs"]

    await add_vacancy(title, desc, reqs, is_cert_mandatory=is_cert_mandatory)
    await state.clear()

    role = staff.get("role", "menejer") if staff else "menejer"
    cert_status_text = "🔴 Majburiy" if is_cert_mandatory == 1 else "🟢 Ixtiyoriy"
    await callback.message.edit_text(
        f"✅ <b>«{title}»</b> vakansiyasi muvaffaqiyatli qo'shildi va botda e'lon qilindi!\n\n"
        f"📜 Sertifikat talabi: <b>{cert_status_text}</b>",
        parse_mode="HTML"
    )
    await callback.message.answer("Boshqaruv menyusi:", reply_markup=admin_main_kb(role=role))
    await callback.answer("Vakansiya qo'shildi!")

# --- 10. ADMIN BEKOR QILISH ---

@router.callback_query(F.data == "adm_cancel_action")
async def cancel_admin_state(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Amal bekor qilindi.")
    await callback.answer()

@router.callback_query(F.data == "adm_back_menu")
async def back_to_admin_menu(callback: CallbackQuery):
    staff = await get_current_staff(callback.from_user.id)
    role = staff.get("role", "menejer") if staff else "menejer"
    await callback.message.delete()
    await callback.message.answer("Boshqaruv menyusi:", reply_markup=admin_main_kb(role=role))
    await callback.answer()

@router.callback_query(F.data == "adm_back_candidates")
async def back_to_candidates_list(callback: CallbackQuery):
    candidates = await get_submitted_candidates()
    await callback.message.edit_text(
        f"📊 <b>Arizalar ro'yxati ({len(candidates)} ta):</b>",
        reply_markup=candidates_list_inline_kb(candidates),
        parse_mode="HTML"
    )
    await callback.answer()

# --- 11. MUROJAATLARGA JAVOB BERISH ---

@router.callback_query(F.data.startswith("reply_appeal_"))
async def start_reply_appeal(callback: CallbackQuery, state: FSMContext):
    staff = await get_current_staff(callback.from_user.id)
    if not staff:
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return

    parts = callback.data.split("_")
    appeal_id = int(parts[2])
    target_user_id = int(parts[3])

    await state.update_data(reply_appeal_id=appeal_id, reply_target_user_id=target_user_id)
    await state.set_state(AdminStates.waiting_reply_appeal)

    await callback.message.answer(
        f"✉️ <b>#{appeal_id}-sonli murojaatga javob yozish:</b>\n\n"
        "Foydalanuvchiga yuboriladigan javob matnini yozib yuboring:",
        reply_markup=admin_cancel_inline_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_reply_appeal)
async def process_reply_appeal(message: Message, state: FSMContext, bot: Bot):
    staff = await get_current_staff(message.from_user.id)
    if not staff:
        return

    data = await state.get_data()
    appeal_id = data.get("reply_appeal_id")
    target_user_id = data.get("reply_target_user_id")
    reply_text = message.text.strip()

    staff_title = staff.get("title", "Rahbariyat")
    replied_by = f"{staff_title} ({message.from_user.full_name})"

    await reply_to_appeal(appeal_id, reply_text, replied_by)
    await state.clear()

    try:
        user_msg = (
            f"📩 <b>Sizning #{appeal_id}-sonli murojaatingizga javob keldi:</b>\n\n"
            f"💬 <b>Javob:</b>\n{reply_text}\n\n"
            f"👤 <b>Javob berdi:</b> {staff_title}"
        )
        await bot.send_message(chat_id=target_user_id, text=user_msg, parse_mode="HTML")
        await message.answer(
            f"✅ <b>#{appeal_id}-sonli murojaatga javob muvaffaqiyatli yuborildi!</b>",
            reply_markup=admin_main_kb(role=staff.get("role", "menejer")),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(
            f"⚠️ Javob bazaga saqlandi, biroq foydalanuvchiga yetkazishda xatolik yuz berdi: {e}",
            reply_markup=admin_main_kb(role=staff.get("role", "menejer"))
        )
