from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database import Base


# ==========================================================
# ANALİZ MODELİ
# ==========================================================

class Analysis(Base):
    __tablename__ = "analyses"

    # Her analiz için benzersiz numara
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # Yüklenen videonun adı
    filename = Column(
        String,
        nullable=False
    )

    # Araç sayıları
    car_count = Column(
        Integer,
        default=0
    )

    bus_count = Column(
        Integer,
        default=0
    )

    truck_count = Column(
        Integer,
        default=0
    )

    motorcycle_count = Column(
        Integer,
        default=0
    )

    # Toplam araç
    total_count = Column(
        Integer,
        default=0
    )

    # Dakikadaki araç sayısı
    vehicles_per_minute = Column(
        Float,
        default=0
    )

    # Trafik yoğunluğu
    density = Column(
        String,
        nullable=False
    )

    # Hareket yönleri
    direction_up = Column(
        Integer,
        default=0
    )

    direction_down = Column(
        Integer,
        default=0
    )

    # Analizin yapıldığı tarih ve saat
    created_at = Column(
        DateTime,
        default=datetime.now
    )


# ==========================================================
# KULLANICI MODELİ
# ==========================================================

class User(Base):
    __tablename__ = "users"

    # Her kullanıcı için benzersiz ID
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # Kullanıcı adı
    username = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    # E-posta adresi
    email = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    # Kullanıcının düz şifresi burada tutulmayacak.
    # Daha sonra hashlenmiş şifreyi kaydedeceğiz.
    hashed_password = Column(
        String,
        nullable=False
    )

    # Kullanıcının kayıt tarihi
    created_at = Column(
        DateTime,
        default=datetime.now
    )