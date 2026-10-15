from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from typing import List, Dict, Any, Optional

def phone_register_mandatory_kb() -> ReplyKeyboardMarkup:
    """Botdan foydalanish uchun majburiy telefon raqam yuborish tugmasi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamimni yuborish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def main_menu_kb(staff_info: Optional[Dict[str, Any]] = None) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📋 Bo'sh vakansiyalar")],
        [KeyboardButton(text="ℹ️ Maktab va talablar haqida"), KeyboardButton(text="✍️ Murojaat yo'llash")]
    ]
    if staff_info:
        role = staff_info.get("role", "")
        if role == "direktor":
            buttons.append([KeyboardButton(text="🏛 Direktor Boshqaruv Paneli")])
        elif role == "admin":
            buttons.append([KeyboardButton(text="👨‍💻 Administrator Paneli")])
        elif role == "menejer":
            buttons.append([KeyboardButton(text="📋 Kadrlar Menejeri Paneli")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def vacancies_inline_kb(vacancies: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    keyboard = []
    for v in vacancies:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📌 {v['title']}",
                callback_data=f"vac_view_{v['id']}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def vacancy_action_kb(vacancy_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Hujjat topshirish",
                    callback_data=f"apply_{vacancy_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Vakansiyalar ro'yxatiga qaytish",
                    callback_data="back_to_vacancies"
                )
            ]
        ]
    )

def phone_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamimni ulashish", request_contact=True)],
            [KeyboardButton(text="❌ Ariza topshirishni bekor qilish")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def cancel_reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Ariza topshirishni bekor qilish")]
        ],
        resize_keyboard=True
    )

def category_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏆 Oliy toifa", callback_data="cat_Oliy toifa"),
                InlineKeyboardButton(text="🥇 1-toifa", callback_data="cat_1-toifa")
            ],
            [
                InlineKeyboardButton(text="🥈 2-toifa", callback_data="cat_2-toifa"),
                InlineKeyboardButton(text="🎓 Mutaxassis", callback_data="cat_Mutaxassis")
            ],
            [
                InlineKeyboardButton(text="🌱 Toifasiz (yosh mutaxassis)", callback_data="cat_Toifasiz")
            ]
        ]
    )

def skip_doc_kb(step_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏭ O'tkazib yuborish (mavjud emas)",
                    callback_data=f"skip_{step_name}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Arizani bekor qilish",
                    callback_data="cancel_application"
                )
            ]
        ]
    )

def confirm_application_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Ha, ma'lumotlar to'g'ri (Arizani yuborish)",
                    callback_data="confirm_final_submit"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish (O'chirish)",
                    callback_data="cancel_application"
                )
            ]
        ]
    )
