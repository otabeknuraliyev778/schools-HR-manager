from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from typing import List, Dict, Any

def admin_main_kb(role: str = "menejer") -> ReplyKeyboardMarkup:
    if role == "direktor":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📥 Yangi kelgan arizalar"), KeyboardButton(text="📊 Barcha arizalar")],
                [KeyboardButton(text="📈 Monitoring & Statistika"), KeyboardButton(text="📑 Excel hisobot yuklash")],
                [KeyboardButton(text="⚙️ Vakansiyalar holati"), KeyboardButton(text="👤 Nomzod rejimiga o'tish")],
                [KeyboardButton(text="🚪 Tizimdan chiqish")]
            ],
            resize_keyboard=True
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 Yangi kelgan arizalar"), KeyboardButton(text="📊 Barcha arizalar")],
            [KeyboardButton(text="⚙️ Vakansiyalarni boshqarish"), KeyboardButton(text="📑 Excel hisobot yuklash")],
            [KeyboardButton(text="👤 Nomzod rejimiga o'tish"), KeyboardButton(text="🚪 Tizimdan chiqish")]
        ],
        resize_keyboard=True
    )

def candidates_list_inline_kb(candidates: List[Dict[str, Any]], title_prefix: str = "Ariza") -> InlineKeyboardMarkup:
    keyboard = []
    status_icons = {
        "submitted": "🟡 Yangi",
        "interview": "🟢 Suhbatda",
        "reserve": "🟠 Zaxirada",
        "rejected": "🔴 Rad etilgan"
    }
    for c in candidates:
        icon = status_icons.get(c.get("status", ""), "📄")
        btn_text = f"{icon} #{c['id']} {c.get('full_name', 'Nomsiz')} ({c.get('vacancy_title', 'Vakansiya')})"
        keyboard.append([
            InlineKeyboardButton(text=btn_text[:50], callback_data=f"adm_cand_{c['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Menyuga qaytish", callback_data="adm_back_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def candidate_action_kb(candidate_id: int, current_status: str, role: str = "menejer") -> InlineKeyboardMarkup:
    buttons = []
    
    # Hujjatlarni ko'rish va yuklab olish tugmasi (Direktor va barcha xodimlar uchun birinchi navbatda chiqadi)
    buttons.append([
        InlineKeyboardButton(
            text="📁 Hujjatlarni ko'rish / yuklab olish",
            callback_data=f"adm_docs_{candidate_id}"
        )
    ])

    # Holatni o'zgartirish tugmalari
    action_row = []
    if current_status != "interview":
        action_row.append(InlineKeyboardButton(text="🟢 Suhbatga chaqirish", callback_data=f"adm_action_interview_{candidate_id}"))
    if current_status != "reserve":
        action_row.append(InlineKeyboardButton(text="🟡 Zaxiraga olish", callback_data=f"adm_action_reserve_{candidate_id}"))
    if action_row:
        buttons.append(action_row)
        
    if current_status != "rejected":
        buttons.append([InlineKeyboardButton(text="🔴 Rad etish", callback_data=f"adm_action_reject_{candidate_id}")])
        
    buttons.append([InlineKeyboardButton(text="⬅️ Ro'yxatga qaytish", callback_data="adm_back_candidates")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def vacancies_manage_kb(vacancies: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    keyboard = []
    for v in vacancies:
        status_text = "🟢 Faol" if v["is_active"] == 1 else "🔴 Nofaol"
        keyboard.append([
            InlineKeyboardButton(text=f"{v['title']} ({status_text})", callback_data=f"adm_vac_toggle_{v['id']}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"adm_vac_del_{v['id']}")
        ])
    keyboard.append([InlineKeyboardButton(text="➕ Yangi vakansiya qo'shish", callback_data="adm_vac_add")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Menyuga qaytish", callback_data="adm_back_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def admin_cancel_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="adm_cancel_action")]
        ]
    )
