from aiogram.fsm.state import State, StatesGroup

class ApplicationStates(StatesGroup):
    choosing_vacancy = State()
    waiting_full_name = State()
    waiting_phone = State()
    waiting_birth_date = State()
    waiting_education = State()
    waiting_category = State()
    waiting_experience = State()
    
    # Hujjatlar yuklash (Majburiy)
    waiting_passport = State()
    waiting_diploma = State()
    waiting_resume = State()
    
    # Hujjatlar yuklash (Ixtiyoriy)
    waiting_cert_file = State()
    waiting_degree_file = State()
    
    # Yakuniy tasdiqlash
    confirm_submission = State()

class AdminStates(StatesGroup):
    waiting_new_vacancy_title = State()
    waiting_new_vacancy_desc = State()
    waiting_new_vacancy_reqs = State()
    waiting_new_vacancy_cert_type = State()
    
    waiting_interview_details = State()
    waiting_reject_reason = State()
    waiting_reply_appeal = State()

class AuthStates(StatesGroup):
    waiting_mandatory_phone = State()

class FeedbackStates(StatesGroup):
    waiting_feedback_text = State()

