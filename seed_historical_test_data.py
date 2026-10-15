import sqlite3
import random

from datetime import datetime, timedelta
from pathlib import Path


# ============================================================
# 1. VERİTABANI
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "traffic_analysis.db"

connection = sqlite3.connect(DATABASE_PATH)
cursor = connection.cursor()


# ============================================================
# 2. TEST AYARLARI
# ============================================================

CAMERA_NAME = "TEST_CAMERA"

# Tekrar çalıştırırsak aynı test verileri çoğalmasın.
cursor.execute(
    """
    DELETE FROM live_traffic_hourly
    WHERE camera_name = ?
    """,
    (CAMERA_NAME,)
)

connection.commit()


# ============================================================
# 3. 10 GÜNLÜK ÖRNEK TRAFİK PROFİLİ
# ============================================================

# Saat -> yaklaşık toplam araç sayısı
#
# Özellikle 16:00 - 19:00 arasını
# daha yoğun yapıyoruz.

traffic_profile = {
    8: 45,
    9: 55,
    10: 40,
    11: 42,
    12: 50,
    13: 52,
    14: 60,
    15: 75,
    16: 115,
    17: 140,
    18: 130,
    19: 105,
    20: 70,
    21: 50
}


# ============================================================
# 4. BAŞLANGIÇ TARİHİ
# ============================================================

start_date = datetime(2026, 9, 1)


# ============================================================
# 5. 10 GÜN BOYUNCA VERİ ÜRET
# ============================================================

for day in range(10):

    current_date = start_date + timedelta(days=day)

    for hour, base_total in traffic_profile.items():

        # Her gün tamamen aynı sayı olmasın.
        variation = random.randint(-10, 10)

        total_count = max(
            0,
            base_total + variation
        )


        # Araç türlerini yaklaşık oranlarla dağıtıyoruz.
        car_count = int(
            total_count * 0.82
        )

        motorcycle_count = int(
            total_count * 0.08
        )

        bus_count = int(
            total_count * 0.04
        )

        truck_count = (
            total_count
            - car_count
            - motorcycle_count
            - bus_count
        )


        hour_start = current_date.replace(
            hour=hour,
            minute=0,
            second=0,
            microsecond=0
        )


        hour_string = hour_start.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        now_string = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )


        cursor.execute(
            """
            INSERT INTO live_traffic_hourly (
                camera_name,
                hour_start,
                car_count,
                motorcycle_count,
                bus_count,
                truck_count,
                total_count,
                created_at,
                updated_at
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                CAMERA_NAME,
                hour_string,
                car_count,
                motorcycle_count,
                bus_count,
                truck_count,
                total_count,
                now_string,
                now_string
            )
        )


connection.commit()


# ============================================================
# 6. KAÇ TEST KAYDI EKLENDİ?
# ============================================================

cursor.execute(
    """
    SELECT COUNT(*)
    FROM live_traffic_hourly
    WHERE camera_name = ?
    """,
    (CAMERA_NAME,)
)

record_count = cursor.fetchone()[0]


print()
print("======================================")
print(" TEST TRAFİK VERİLERİ OLUŞTURULDU")
print("======================================")
print()

print(f"Kamera: {CAMERA_NAME}")
print(f"Gün sayısı: 10")
print(f"Toplam kayıt: {record_count}")

print()
print(
    "Test verileri traffic_analysis.db "
    "dosyasına kaydedildi."
)


connection.close()