from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Projenin ana klasörünü buluyoruz.
BASE_DIR = Path(__file__).resolve().parent.parent


# SQLite veritabanı dosyamız burada oluşacak:
# traffic_analysis_project/traffic_analysis.db
DATABASE_PATH = BASE_DIR / "traffic_analysis.db"


# SQLAlchemy'nin anlayacağı veritabanı adresi.
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"


# Python ile SQLite arasındaki bağlantıyı yöneten engine.
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False
    }
)


# Her veritabanı işlemi için kullanacağımız oturumları üretir.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Birazdan oluşturacağımız tabloların temel sınıfı.
Base = declarative_base()


def get_db():
    """
    Veritabanı oturumu oluşturur.
    İşlem tamamlanınca bağlantıyı kapatır.
    """

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
        