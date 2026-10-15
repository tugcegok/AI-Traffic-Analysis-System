from pydantic import BaseModel, EmailStr


# ==========================================================
# KULLANICI KAYIT ŞEMASI
# ==========================================================

class UserRegister(BaseModel):

    username: str

    email: EmailStr

    password: str


# ==========================================================
# KULLANICI GİRİŞ ŞEMASI
# ==========================================================

class UserLogin(BaseModel):

    email: EmailStr

    password: str