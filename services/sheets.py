import logging
import asyncio
from typing import Dict, Any
from pathlib import Path
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_FILE, BASE_DIR

logger = logging.getLogger(__name__)

async def sync_candidate_to_google_sheet(candidate: Dict[str, Any]):
    """Yangi tasdiqlangan arizani Google Sheets jadvaliga qo'shish (agar sozlangan bo'lsa)"""
    if not GOOGLE_SHEET_ID:
        logger.info("Google Sheet ID belgilanmagan, sinxronizatsiya o'tkazib yuborildi.")
        return

    creds_path = BASE_DIR / GOOGLE_CREDENTIALS_FILE
    if not creds_path.exists():
        logger.warning(f"Google Sheets hisobga olish fayli ({GOOGLE_CREDENTIALS_FILE}) topilmadi.")
        return

    # Asinxron jarayonda blokirovka qilmaslik uchun thread poolda ishlatamiz
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _append_row_sync, creds_path, GOOGLE_SHEET_ID, candidate)

def _append_row_sync(creds_path: Path, sheet_id: str, candidate: Dict[str, Any]):
    try:
        import gspread
        gc = gspread.service_account(filename=str(creds_path))
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.get_worksheet(0)
        
        # Sarlavhalarni tekshirish (agar jadval bo'sh bo'lsa sarlavha yozish)
        existing_rows = worksheet.row_values(1)
        if not existing_rows:
            headers = [
                "ID", "Topshirilgan sana", "F.I.SH", "Telefon", 
                "Vakansiya", "Toifasi", "Ish staji", "OTM / Ma'lumot", 
                "Sertifikatlar", "Holati"
            ]
            worksheet.append_row(headers)

        row_data = [
            f"#{candidate.get('id', '')}",
            candidate.get("submitted_at", ""),
            candidate.get("full_name", ""),
            candidate.get("phone", ""),
            candidate.get("vacancy_title", ""),
            candidate.get("category", ""),
            candidate.get("experience", ""),
            candidate.get("education", ""),
            candidate.get("cert_info", ""),
            candidate.get("status", "submitted")
        ]
        worksheet.append_row(row_data)
        logger.info(f"Nomzod #{candidate.get('id')} ma'lumotlari Google Sheets'ga yozildi.")
    except Exception as e:
        logger.error(f"Google Sheets'ga yozishda xatolik: {e}")
