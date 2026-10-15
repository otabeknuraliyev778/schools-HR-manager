# 🏛 Ixtisoslashgan Maktab Kadrlar Menejeri Yordamchi Telegram Boti

Ushbu loyiha ixtisoslashgan maktablar (Prezident maktablari, ijod va ixtisoslashtirilgan ta'lim muassasalari) uchun kadrlar saralash, vakansiyalarni e'lon qilish hamda nomzodlardan arizalar va hujjatlarni to'liq, tartibli qabul qilish tizimidir.

---

## 🌟 Tizimning asosiy afzalliklari va qoidalari

1. **«Qoralama (Draft)» filtri:**
   - Nomzod ariza to'ldirishni boshlab, oxiriga yetkazmaguncha yoki «Tasdiqlash va yuborish» tugmasini bosmaguncha, arizasi **kadrlar menejeriga ko'rinmaydi** va topshirilmagan hisoblanadi. Bu menejerni chala arizalardan butunlay xalos qiladi.
2. **Bosqichma-bosqich qabul (FSM):**
   - Shaxsiy ma'lumotlar (F.I.SH, Telefon raqam, Tug'ilgan sana);
   - Ma'lumoti, tamomlagan OTM va mutaxassisligi;
   - Malaka toifasi (Oliy, 1-toifa, 2-toifa, Mutaxassis, Toifasiz);
   - Pedagogik ish staji;
   - Majburiy hujjatlar: Pasport/ID-karta, Diplom va ilovasi, Rezyume (CV);
   - Ixtiyoriy hujjatlar: Til/Fan sertifikati (IELTS, CEFR, Milliy sertifikat), Ilmiy daraja hujjati (PhD, DSc).
3. **Kadrlar Menejeri (Admin) Paneli:**
   - Yangi topshirilgan nomzodlar dosyesini ko'rish;
   - Nomzodning barcha yuklangan hujjatlarini (PDF/rasm) bir zumda olish;
   - 🟢 **Suhbatga chaqirish:** Suhbat kuni va joyini kiritish (nomzodga bot orqali rasmiy xabarnoma boradi);
   - 🟡 **Kadrlar zaxirasiga olish;**
   - 🔴 **Rad etish:** Sababini ko'rsatgan holda xushmuomala javob yuborish;
   - 📑 **Excel hisobot:** Barcha arizalarni chiroyli formatlangan `.xlsx` jadval ko'rinishida yuklab olish;
   - ⚙️ **Vakansiyalar boshqaruvi:** Yangi vakansiya qo'shish, mavjudlarini yoqish/o'chirish yoki o'chirish.
4. **Majburiy telefon orqali shaxsni tasdiqlash va Avtomatik Rol aniqlash:**
   - Botga kirgan har qanday foydalanuvchidan dastlab **majburiy** tarzda o'z telefon raqamini tasdiqlash so'raladi (`📱 Telefon raqamimni yuborish`).
   - Alohida "xodim kirishi" tugmasi kerak emas! Bot kiritilgan raqamdan avtomatik aniqlaydi:
     * `+998938224228` -> darhol **Admin Paneli** ochiladi.
     * `+998932602280` -> darhol **Kadrlar Menejeri Paneli** ochiladi.
     * `+998997189788` -> darhol **Direktor Boshqaruv Paneli** ochiladi.
     * Boshqa har qanday raqam -> darhol **Nomzod (Talabgor)** menyusi ochiladi.
   - Nomzod ariza topshirayotganda telefon raqami allaqachon tasdiqlangani sababli qayta so'ralmaydi va xatoliklarning oldi olinadi.
5. **Google Sheets integratsiyasi (ixtiyoriy):**
   - Yangi arizalar avtomatik ravishda onlayn Google Jadvalga ham tushib borishi mumkin.

---

## 📁 Loyiha tuzilmasi

```
maktab_hr_bot/
├── config.py              # Bot sozlamalari, yo'llar va admin ID lari
├── database.py            # SQLite asinxron modeli va CRUD funksiyalari
├── states.py              # Aiogram FSM holatlari (Nomzod va Admin oqimlari)
├── keyboards/
│   ├── candidate.py       # Nomzodlar uchun tugmalar va menyular
│   └── admin.py           # Menejer uchun boshqaruv tugmalari
├── handlers/
│   ├── start.py           # /start, ma'lumot va bekor qilish
│   ├── vacancy.py         # Vakansiyalar bilan tanishish
│   ├── application.py     # Hujjat topshirishning to'liq FSM zanjiri
│   └── admin.py           # Menejerning to'liq boshqaruv logikasi
├── services/
│   ├── excel.py           # Nomzodlar hisobotini .xlsx formatida generatsiya qilish
│   └── sheets.py          # Google Sheets bilan xavfsiz sinxronlash
├── uploads/               # Nomzodlarning yuklagan fayllari
├── main.py                # Botni ishga tushiruvchi asosiy fayl
├── requirements.txt       # Kerakli Python kutubxonalari
├── .env                   # Maxfiy sozlamalar (Token, Admin ID)
└── .env.example           # Sozlamalar namunasi
```

---

## 🚀 Ishga tushirish bo'yicha qo'llanma

### 1. Sozlamalarni kiritish
Loyiha papkasidagi `.env` faylini oching va ma'lumotlarni to'ldiring:
```env
# @BotFather dan olingan bot tokeni
BOT_TOKEN=1234567890:AAH...

# Kadrlar menejeri(lari)ning Telegram ID raqami (@userinfobot orqali bilish mumkin)
# Agar bir nechta bo'lsa, vergul bilan yozing: 12345678,87654321
ADMIN_IDS=123456789
```

### 2. Botni ishga tushirish
Terminalda quyidagi buyruqni bering:
```powershell
.venv\Scripts\python main.py
```

Bot ishga tushgach, avtomatik ravishda bazaga sinov uchun 3 ta vakansiyani kiritadi:
- **Ingliz tili o'qituvchisi**
- **Informatika va axborot texnologiyalari o'qituvchisi**
- **Tarbiyachi / Psixolog**

Siz admin paneldan turib istalgan paytda qo'shimcha vakansiyalar qo'shishingiz yoki mavjudlarini o'zgartirishingiz mumkin.
