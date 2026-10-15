import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

BOT_TOKEN = os.getenv("BOT_TOKEN", "8548746200:AAEWR-IbsFuCkbCu5-7_98QEm1GsphJK58c")

# 1. Admin ID lar (Telegram ID lar, vergul bilan ajratilgan)
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "1017600630")
ADMIN_IDS = [
    int(admin_id.strip())
    for admin_id in ADMIN_IDS_RAW.split(",")
    if admin_id.strip().isdigit()
]

# 2. Direktor ID lar (Telegram ID lar, vergul bilan ajratilgan)
DIRECTOR_IDS_RAW = os.getenv("DIRECTOR_IDS", "1053384968")
DIRECTOR_IDS = [
    int(d_id.strip())
    for d_id in DIRECTOR_IDS_RAW.split(",")
    if d_id.strip().isdigit()
]

# 3. Kadrlar Menejeri ID lar (Telegram ID lar, vergul bilan ajratilgan)
MANAGER_IDS_RAW = os.getenv("MANAGER_IDS", "7023277036")
MANAGER_IDS = [
    int(m_id.strip())
    for m_id in MANAGER_IDS_RAW.split(",")
    if m_id.strip().isdigit()
]

# 4. Telegram ID orqali qo'shimcha xodimlar lug'ati
STAFF_ROLES = {
    # 1017600630: {
    #     "role": "admin",
    #     "title": "Tizim Administratori",
    #     "icon": "👨‍💻"
    # },
}

def get_staff_info_by_id(user_id: int):
    """Telegram user_id bo'yicha xodim roliga egaligini tekshiradi (direktor, admin, menejer)."""
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return None

    # 1. STAFF_ROLES lug'atidan tekshirish
    if uid in STAFF_ROLES:
        return STAFF_ROLES[uid]
    if str(uid) in STAFF_ROLES:
        return STAFF_ROLES[str(uid)]

    # 2. Direktor ID lari
    if uid in DIRECTOR_IDS:
        return {
            "role": "direktor",
            "title": "Maktab Direktori",
            "icon": "🏛"
        }

    # 3. Administrator ID lari
    if uid in ADMIN_IDS:
        return {
            "role": "admin",
            "title": "Tizim Administratori",
            "icon": "👨‍💻"
        }

    # 4. Kadrlar Menejeri ID lari
    if uid in MANAGER_IDS:
        return {
            "role": "menejer",
            "title": "Kadrlar Bo'limi Menejeri",
            "icon": "📋"
        }

    return None

def get_all_configured_staff_ids():
    """Barcha sozlangan xodimlarning Telegram ID lari ro'yxati"""
    ids = set(ADMIN_IDS + DIRECTOR_IDS + MANAGER_IDS)
    for k in STAFF_ROLES.keys():
        try:
            ids.add(int(k))
        except (ValueError, TypeError):
            pass
    return list(ids)

def normalize_phone_number(raw_phone: str) -> str:
    """Telefon raqamini yagona +998XXXXXXXXX formatiga keltiradi"""
    if not raw_phone:
        return ""
    digits = re.sub(r"\D", "", raw_phone)
    if digits.startswith("998") and len(digits) == 12:
        return f"+{digits}"
    elif len(digits) == 9:
        return f"+998{digits}"
    elif digits.startswith("8") and len(digits) == 10:
        return f"+998{digits[1:]}"
    return f"+{digits}" if digits else ""

# Baza va fayllar yo'li
DB_NAME = os.getenv("DB_NAME", "school_hr.db")
DB_PATH = BASE_DIR / DB_NAME
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Google Sheets integratsiyasi (ixtiyoriy)
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "service_account.json")
