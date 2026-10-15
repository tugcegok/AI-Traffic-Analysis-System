from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext


# ==========================================================
# ŞİFRE HASHLEME AYARI
# ==========================================================

password_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# ==========================================================
# JWT AYARLARI
# ==========================================================

# Bu anahtar JWT tokenlarını imzalamak için kullanılır.
# Bu proje şu an yerel geliştirme ortamında olduğu için burada tutuluyor.
# Gerçek bir production projesinde environment variable içinde tutulmalıdır."
load_dotenv()

SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30


# ==========================================================
# ŞİFREYİ HASHLE
# ==========================================================

def hash_password(password: str) -> str:
    """
    Kullanıcının düz metin şifresini
    güvenli bir hash değerine dönüştürür.
    """

    return password_context.hash(password)


# ==========================================================
# ŞİFREYİ DOĞRULA
# ==========================================================

def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """
    Kullanıcının giriş sırasında yazdığı şifre ile
    veritabanındaki hashlenmiş şifreyi karşılaştırır.
    """

    return password_context.verify(
        plain_password,
        hashed_password
    )


# ==========================================================
# JWT ACCESS TOKEN OLUŞTUR
# ==========================================================

def create_access_token(
    user_id: int,
    email: str
) -> str:
    """
    Giriş yapan kullanıcı için JWT access token oluşturur.
    """

    # Token'ın sona ereceği zamanı hesapla
    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )


    # Token içerisinde tutulacak bilgiler
    payload = {

        # sub = subject
        # Token'ın hangi kullanıcıya ait olduğunu belirtir.
        "sub": str(user_id),

        "email": email,

        # Token'ın son kullanma zamanı
        "exp": expire

    }


    # JWT token oluştur
    token = jwt.encode(

        payload,

        SECRET_KEY,

        algorithm=ALGORITHM

    )


    return token


# ==========================================================
# JWT TOKEN DOĞRULA
# ==========================================================

def verify_access_token(token: str):
    """
    Gelen JWT token'ın geçerli olup olmadığını kontrol eder.
    Token geçerliyse içerisindeki bilgileri döndürür.
    Geçersiz veya süresi dolmuşsa None döndürür.
    """

    try:

        payload = jwt.decode(

            token,

            SECRET_KEY,

            algorithms=[ALGORITHM]

        )

        return payload


    except InvalidTokenError:

        return None
