import aiosqlite
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import DB_PATH

@asynccontextmanager
async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()

async def init_db():
    async with get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                requirements TEXT NOT NULL,
                is_cert_mandatory INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                vacancy_id INTEGER,
                full_name TEXT,
                phone TEXT,
                birth_date TEXT,
                education TEXT,
                specialty TEXT,
                category TEXT,
                experience TEXT,
                cert_info TEXT,
                academic_degree_info TEXT,
                status TEXT DEFAULT 'draft',
                admin_notes TEXT,
                action_by_name TEXT,
                action_by_role TEXT,
                action_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                submitted_at TIMESTAMP,
                FOREIGN KEY (vacancy_id) REFERENCES vacancies (id) ON DELETE SET NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                doc_type TEXT NOT NULL,
                file_id TEXT NOT NULL,
                file_unique_id TEXT,
                file_name TEXT,
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (candidate_id) REFERENCES candidates (id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                phone TEXT NOT NULL,
                role TEXT NOT NULL,
                title TEXT,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                phone TEXT NOT NULL,
                role TEXT NOT NULL,
                title TEXT NOT NULL,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS appeals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                full_name TEXT,
                phone TEXT,
                message_text TEXT NOT NULL,
                status TEXT DEFAULT 'new',
                reply_text TEXT,
                replied_by TEXT,
                replied_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migratsiyalar: mavjud jadvallarga yangi ustunlarni qo'shish
        try:
            await db.execute("ALTER TABLE vacancies ADD COLUMN is_cert_mandatory INTEGER DEFAULT 0")
        except Exception:
            pass

        for col in ["action_by_name", "action_by_role", "action_at"]:
            try:
                await db.execute(f"ALTER TABLE candidates ADD COLUMN {col} TEXT")
            except Exception:
                pass

        # Sinov vakansiyalarini tekshirib, bo'lmasa kiritish
        cursor = await db.execute("SELECT COUNT(*) FROM vacancies")
        count = (await cursor.fetchone())[0]
        if count == 0:
            initial_vacancies = [
                (
                    "Ingliz tili o'qituvchisi",
                    "Chuqurlashtirilgan sinflar uchun 1 stavka (20-24 dars soati). Zamonaviy metodikalar, xalqaro dasturlar asosida dars o'tish.",
                    "• Oliy pedagogik ma'lumot (filologiya/ingliz tili);\n• Kamida IELTS 7.0 yoki CEFR C1 sertifikati;\n• Kamida 2 yillik pedagogik ish staji;\n• 1-toifa yoki Oliy toifa (ustunlik beradi)."
                ),
                (
                    "Informatika va axborot texnologiyalari o'qituvchisi",
                    "1 stavka. Chuqurlashtirilgan IT yo'nalishi: Python, C++, algoritmlash va olimpiada tayyorgarligi.",
                    "• Oliy sohaviy ma'lumot (Dasturiy injiniring, Informatika yoki Amaliy matematika);\n• Zamonaviy dasturlash tillarini bilish (Python / C++);\n• O'quvchilarni fan olimpiadalariga tayyorlash tajribasi;\n• Kamida 1 yillik ish staji."
                ),
                (
                    "Tarbiyachi / Psixolog",
                    "1 stavka. Ixtisoslashgan maktab o'quvchilari (internat/kunduzgi) bilan tarbiyaviy-ijtimoiy va psixologik ishlarni olib borish.",
                    "• Psixologiya yoki Pedagogika yo'nalishi bo'yicha oliy ma'lumot;\n• Iqtidorli bolalar va o'smirlar psixologiyasi bo'yicha amaliy tajriba;\n• Xushmuomalalik, mas'uliyat va stressga chidamlilik;\n• Kamida 1 yillik amaliy staj."
                )
            ]
            await db.executemany(
                "INSERT INTO vacancies (title, description, requirements) VALUES (?, ?, ?)",
                initial_vacancies
            )
        await db.commit()

# --- VAKANSIYALAR FUNKSIYALARI ---

async def get_active_vacancies() -> List[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute("SELECT * FROM vacancies WHERE is_active = 1 ORDER BY id ASC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_all_vacancies() -> List[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute("SELECT * FROM vacancies ORDER BY id DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_vacancy_by_id(vacancy_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute("SELECT * FROM vacancies WHERE id = ?", (vacancy_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def add_vacancy(title: str, description: str, requirements: str, is_cert_mandatory: int = 0) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO vacancies (title, description, requirements, is_cert_mandatory) VALUES (?, ?, ?, ?)",
            (title, description, requirements, is_cert_mandatory)
        )
        await db.commit()
        return cursor.lastrowid

async def toggle_vacancy_status(vacancy_id: int, is_active: int):
    async with get_db() as db:
        await db.execute("UPDATE vacancies SET is_active = ? WHERE id = ?", (is_active, vacancy_id))
        await db.commit()

async def delete_vacancy(vacancy_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM vacancies WHERE id = ?", (vacancy_id,))
        await db.commit()

# --- NOMZODLAR (ARIZALAR) FUNKSIYALARI ---

async def get_or_create_draft_candidate(user_id: int) -> int:
    """Nomzodning tugallanmagan draft arizasini topadi yoki yangisini ochadi"""
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM candidates WHERE user_id = ? AND status = 'draft' ORDER BY id DESC LIMIT 1",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row["id"]
        
        cursor = await db.execute(
            "INSERT INTO candidates (user_id, status) VALUES (?, 'draft')",
            (user_id,)
        )
        await db.commit()
        return cursor.lastrowid

async def update_candidate_field(candidate_id: int, field: str, value: Any):
    allowed_fields = {
        "vacancy_id", "full_name", "phone", "birth_date", "education",
        "specialty", "category", "experience", "cert_info",
        "academic_degree_info", "status", "admin_notes", "submitted_at"
    }
    if field not in allowed_fields:
        raise ValueError(f"Maydon ruxsat etilmagan: {field}")
    
    async with get_db() as db:
        await db.execute(
            f"UPDATE candidates SET {field} = ? WHERE id = ?",
            (value, candidate_id)
        )
        await db.commit()

async def finalize_candidate_submission(candidate_id: int):
    """Arizani rasmiy topshirilgan holatga o'tkazish"""
    async with get_db() as db:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(
            "UPDATE candidates SET status = 'submitted', submitted_at = ? WHERE id = ?",
            (now, candidate_id)
        )
        await db.commit()

async def cancel_candidate_draft(candidate_id: int):
    """Qoralama arizani va unga tegishli hujjatlarni bekor qilish"""
    async with get_db() as db:
        await db.execute("DELETE FROM documents WHERE candidate_id = ?", (candidate_id,))
        await db.execute("DELETE FROM candidates WHERE id = ? AND status = 'draft'", (candidate_id,))
        await db.commit()

async def get_candidate_by_id(candidate_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute("""
            SELECT c.*, v.title as vacancy_title, v.is_cert_mandatory 
            FROM candidates c
            LEFT JOIN vacancies v ON c.vacancy_id = v.id
            WHERE c.id = ?
        """, (candidate_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_submitted_candidates(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Menejer ko'rishi uchun FAQAT topshirilgan (submitted, interview, reserve, rejected) arizalarni qaytaradi.
    Draft arizalar hech qachon bu yerda ko'rinmaydi!"""
    async with get_db() as db:
        if status:
            query = """
                SELECT c.*, v.title as vacancy_title, v.is_cert_mandatory 
                FROM candidates c
                LEFT JOIN vacancies v ON c.vacancy_id = v.id
                WHERE c.status = ?
                ORDER BY c.submitted_at DESC, c.id DESC
            """
            params = (status,)
        else:
            query = """
                SELECT c.*, v.title as vacancy_title, v.is_cert_mandatory 
                FROM candidates c
                LEFT JOIN vacancies v ON c.vacancy_id = v.id
                WHERE c.status != 'draft'
                ORDER BY c.submitted_at DESC, c.id DESC
            """
            params = ()
        
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def update_candidate_status(
    candidate_id: int,
    new_status: str,
    admin_notes: Optional[str] = None,
    action_by_name: Optional[str] = None,
    action_by_role: Optional[str] = None
):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with get_db() as db:
        await db.execute(
            """UPDATE candidates 
               SET status = ?, admin_notes = ?, action_by_name = ?, action_by_role = ?, action_at = ?
               WHERE id = ?""",
            (new_status, admin_notes, action_by_name, action_by_role, now, candidate_id)
        )
        await db.commit()

# --- HUJJATLAR FUNKSIYALARI ---

async def add_candidate_document(candidate_id: int, doc_type: str, file_id: str, file_unique_id: str, file_name: str, file_path: str = ""):
    async with get_db() as db:
        await db.execute("DELETE FROM documents WHERE candidate_id = ? AND doc_type = ?", (candidate_id, doc_type))
        await db.execute(
            """INSERT INTO documents (candidate_id, doc_type, file_id, file_unique_id, file_name, file_path)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (candidate_id, doc_type, file_id, file_unique_id, file_name, file_path)
        )
        await db.commit()

async def get_candidate_documents(candidate_id: int) -> List[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM documents WHERE candidate_id = ? ORDER BY id ASC",
            (candidate_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

# --- FOYDALANUVCHILAR VA XODIMLAR FUNKSIYALARI ---

async def save_or_update_user(user_id: int, phone: str, role: str, title: str = "", full_name: str = ""):
    async with get_db() as db:
        await db.execute(
            """INSERT INTO users (user_id, phone, role, title, full_name)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
               phone = excluded.phone,
               role = excluded.role,
               title = excluded.title,
               full_name = CASE WHEN excluded.full_name != '' THEN excluded.full_name ELSE users.full_name END""",
            (user_id, phone, role, title, full_name)
        )
        await db.commit()

async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def register_staff(user_id: int, phone: str, role: str, title: str):
    await save_or_update_user(user_id, phone, role, title)

async def get_staff_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
    from config import get_staff_info_by_id
    staff_info = get_staff_info_by_id(user_id)
    user = await get_user_by_id(user_id)
    if staff_info:
        return {
            "user_id": user_id,
            "role": staff_info["role"],
            "title": staff_info["title"],
            "icon": staff_info.get("icon", "👔"),
            "phone": user.get("phone", "") if user else "",
            "full_name": user.get("full_name", "") if user else ""
        }
    if user and user.get("role") in ("admin", "menejer", "direktor"):
        return user
    return None

async def get_all_staff_user_ids() -> List[int]:
    from config import get_all_configured_staff_ids
    all_ids = set(get_all_configured_staff_ids())
    async with get_db() as db:
        async with db.execute("SELECT user_id FROM users WHERE role IN ('admin', 'menejer', 'direktor')") as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                all_ids.add(row["user_id"])
    return list(all_ids)

async def remove_staff(user_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()

# --- MUROJAATLAR (APPEALS) FUNKSIYALARI ---

async def create_appeal(user_id: int, full_name: str, phone: str, message_text: str) -> int:
    """Yangi murojaatni saqlash"""
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO appeals (user_id, full_name, phone, message_text) VALUES (?, ?, ?, ?)",
            (user_id, full_name, phone, message_text)
        )
        await db.commit()
        return cursor.lastrowid

async def get_appeal_by_id(appeal_id: int) -> Optional[Dict[str, Any]]:
    """Murojaatni ID bo'yicha olish"""
    async with get_db() as db:
        async with db.execute("SELECT * FROM appeals WHERE id = ?", (appeal_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def reply_to_appeal(appeal_id: int, reply_text: str, replied_by: str):
    """Murojaatga javob yozish va holatini yangilash"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with get_db() as db:
        await db.execute(
            """UPDATE appeals 
               SET status = 'replied', reply_text = ?, replied_by = ?, replied_at = ?
               WHERE id = ?""",
            (reply_text, replied_by, now, appeal_id)
        )
        await db.commit()


