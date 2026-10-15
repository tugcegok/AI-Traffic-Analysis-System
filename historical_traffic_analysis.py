# Bu kodun amacı, SQLite veritabanındaki geçmiş trafik kayıtlarını
# saatlere göre analiz etmek ve en yoğun saati bulmaktır.

# SQLite veritabanına bağlanmak için
import sqlite3

# Dosya yollarını güvenli şekilde oluşturmak için
from pathlib import Path


# ============================================================
# 1. VERİTABANI YOLU
# ============================================================

# Bu Python dosyasının bulunduğu klasörü alır
BASE_DIR = Path(__file__).resolve().parent

# Veritabanı dosyasının tam yolunu oluşturur
DATABASE_PATH = BASE_DIR / "traffic_analysis.db"


# ============================================================
# 2. ANALİZ EDİLECEK KAMERA
# ============================================================

# Sadece bu kameraya ait trafik kayıtları analiz edilir
CAMERA_NAME = "TEST_CAMERA"


# ============================================================
# 3. VERİTABANINA BAĞLAN
# ============================================================

# SQLite veritabanıyla bağlantı kurar
connection = sqlite3.connect(DATABASE_PATH)

# SQL sorgularını çalıştırmak için cursor oluşturur
cursor = connection.cursor()


# ============================================================
# 4. SAATLİK ORTALAMA TRAFİK ANALİZİ
# ============================================================

# Kayıtları saate göre gruplandırır ve ortalamaları hesaplar
cursor.execute(
    """
    SELECT
        -- Tarih bilgisinden yalnızca saati alır
        strftime('%H', hour_start) AS hour,

        -- Bu saate ait kaç günlük kayıt olduğunu hesaplar
        COUNT(*) AS record_count,

        -- Araç türlerinin saatlik ortalamalarını hesaplar
        AVG(car_count) AS avg_car,
        AVG(motorcycle_count) AS avg_motorcycle,
        AVG(bus_count) AS avg_bus,
        AVG(truck_count) AS avg_truck,

        -- Toplam araç sayısının ortalamasını hesaplar
        AVG(total_count) AS avg_total

    FROM live_traffic_hourly

    -- Yalnızca seçilen kameranın kayıtlarını alır
    WHERE camera_name = ?

    -- Kayıtları saat bilgisine göre gruplandırır
    GROUP BY strftime('%H', hour_start)

    -- Sonuçları saate göre sıralar
    ORDER BY hour
    """,

    # Soru işareti yerine güvenli şekilde kamera adını gönderir
    (CAMERA_NAME,)
)

# SQL sorgusunun döndürdüğü bütün satırları alır
rows = cursor.fetchall()


# ============================================================
# 5. VERİ VAR MI?
# ============================================================

# Kamera için herhangi bir trafik kaydı bulunamadıysa çalışır
if not rows:

    print(
        f"{CAMERA_NAME} için "
        "analiz edilecek veri bulunamadı."
    )

    # Veritabanı bağlantısını kapatır
    connection.close()

    # Programı sonlandırır
    exit()


# ============================================================
# 6. SONUÇLARI YAZDIR
# ============================================================

# Analiz başlığını terminale yazdırır
print()
print("==========================================")
print("       TARİHSEL TRAFİK ANALİZİ")
print("==========================================")

print()
print(f"Kamera: {CAMERA_NAME}")
print()


# En yoğun saati saklar
busiest_hour = None

# Karşılaştırma yapabilmek için başlangıç değeri belirler
busiest_average = -1


# Sorgudan gelen her saatlik sonucu sırayla inceler
for row in rows:

    # Satırdaki değerleri ayrı değişkenlere yerleştirir
    (
        hour,
        record_count,
        avg_car,
        avg_motorcycle,
        avg_bus,
        avg_truck,
        avg_total
    ) = row

    # Saatlik ortalama araç sayılarını terminale yazdırır
    print(
        f"{hour}:00 -> "
        f"Ortalama Toplam: {avg_total:.2f} | "
        f"Car: {avg_car:.2f} | "
        f"Motorcycle: {avg_motorcycle:.2f} | "
        f"Bus: {avg_bus:.2f} | "
        f"Truck: {avg_truck:.2f} | "
        f"Gün Sayısı: {record_count}"
    )

    # Mevcut saatin ortalaması daha yüksekse en yoğun saati günceller
    if avg_total > busiest_average:

        busiest_average = avg_total
        busiest_hour = hour


# ============================================================
# 7. EN YOĞUN SAAT
# ============================================================

# Analizin genel sonucunu terminale yazdırır
print()
print("------------------------------------------")
print("SONUÇ")
print("------------------------------------------")

# En yoğun saati gösterir
print(
    f"En yoğun saat: "
    f"{busiest_hour}:00"
)

# En yoğun saatteki ortalama araç sayısını gösterir
print(
    f"Bu saatte günlük ortalama araç sayısı: "
    f"{busiest_average:.2f}"
)

print()

# Sonucu açıklayıcı bir cümle hâlinde gösterir
print(
    f"Geçmiş trafik kayıtlarına göre "
    f"bu yol genellikle "
    f"{busiest_hour}:00 civarında "
    f"daha yoğun gözlemlenmektedir."
)


# ============================================================
# 8. VERİTABANI BAĞLANTISINI KAPAT
# ============================================================

# İşlem tamamlandıktan sonra veritabanı bağlantısını kapatır
connection.close()