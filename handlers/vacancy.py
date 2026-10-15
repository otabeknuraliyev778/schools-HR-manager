from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import get_active_vacancies, get_vacancy_by_id
from keyboards.candidate import vacancies_inline_kb, vacancy_action_kb

router = Router()

@router.message(F.text == "📋 Bo'sh vakansiyalar")
async def show_vacancies(message: Message):
    vacancies = await get_active_vacancies()
    if not vacancies:
        await message.answer(
            "😔 Hozirda maktabimizda ochiq vakansiyalar mavjud emas.\n"
            "Yangi tanlovlar e'lon qilinganda bot orqali xabar beriladi.",
            parse_mode="HTML"
        )
        return

    text = (
        "📋 <b>Hozirda mavjud bo'sh ish o'rinlari (Vakansiyalar):</b>\n\n"
        "Batafsil talablar bilan tanishish va ariza topshirish uchun quyidagi yo'nalishlardan birini tanlang:"
    )
    await message.answer(
        text,
        reply_markup=vacancies_inline_kb(vacancies),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("vac_view_"))
async def view_vacancy_detail(callback: CallbackQuery):
    vacancy_id = int(callback.data.split("_")[2])
    vacancy = await get_vacancy_by_id(vacancy_id)
    if not vacancy:
        await callback.answer("Vakansiya topilmadi!", show_alert=True)
        return

    is_cert_mandatory = vacancy.get("is_cert_mandatory", 0)
    cert_req_text = "🔴 Majburiy (Sertifikatsiz ariza qabul qilinmaydi)" if is_cert_mandatory == 1 else "🟢 Ixtiyoriy"

    text = (
        f"📌 <b>Vakansiya:</b> {vacancy['title']}\n\n"
        f"📋 <b>Ish tavsifi:</b>\n{vacancy['description']}\n\n"
        f"🎯 <b>Nomzodga qo'yiladigan talablar:</b>\n{vacancy['requirements']}\n\n"
        f"📜 <b>Sertifikat talabi:</b> {cert_req_text}\n\n"
        f"<i>Agar ushbu talablarga mos kelsangiz, «Hujjat topshirish» tugmasini bosing.</i>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=vacancy_action_kb(vacancy_id),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_vacancies")
async def back_to_vacancies_list(callback: CallbackQuery):
    vacancies = await get_active_vacancies()
    if not vacancies:
        await callback.message.edit_text("Hozirda ochiq vakansiyalar mavjud emas.")
        await callback.answer()
        return

    text = "📋 <b>Mavjud bo'sh ish o'rinlari:</b>\nIltimos, kerakli vakansiyani tanlang:"
    await callback.message.edit_text(
        text,
        reply_markup=vacancies_inline_kb(vacancies),
        parse_mode="HTML"
    )
    await callback.answer()
