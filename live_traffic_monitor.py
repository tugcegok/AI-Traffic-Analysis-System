# Bu kodun amacı, canlı trafik yayınındaki araçları YOLO ile tespit etmek,
# ByteTrack ile takip etmek, çizgiyi geçen araçları sınıflarına göre saymak
# ve saatlik sonuçları SQLite veritabanına kaydetmektir.

# OpenCV: Canlı yayını okumak ve görüntü üzerine çizim yapmak için
import cv2

# SQLite: Trafik sonuçlarını veritabanına kaydetmek için
import sqlite3

# Bağlantı koptuğunda beklemek için
import time

# Güncel tarih ve saat bilgilerini almak için
from datetime import datetime

# Dosya yollarını güvenli şekilde oluşturmak için
from pathlib import Path

# YOLO modelini kullanmak için
from ultralytics import YOLO


# ============================================================
# 1. AYARLAR
# ============================================================

# Analiz edilen kameranın adı
CAMERA_NAME = "07071 AKCAM SOKAK"

# Canlı trafik yayınının adresi
STREAM_URL = (
    "https://601a55c88ec6d.streamlock.net/"
    "hls/699.stream/playlist.m3u8"
)

# Kullanılacak YOLO modelinin dosyası
MODEL_PATH = "yolo11s.pt"

# Yalnızca bu araç sınıfları tespit edilir
VEHICLE_CLASSES = [2, 3, 5, 7]

# COCO sınıfları:
# 2 = car
# 3 = motorcycle
# 5 = bus
# 7 = truck


# ============================================================
# 2. VERİTABANI
# ============================================================

# Bu Python dosyasının bulunduğu klasörü alır
BASE_DIR = Path(__file__).resolve().parent

# Veritabanı dosyasının tam yolunu oluşturur
DATABASE_PATH = BASE_DIR / "traffic_analysis.db"

# SQLite veritabanına bağlanır
connection = sqlite3.connect(DATABASE_PATH)

# SQL sorgularını çalıştırmak için cursor oluşturur
cursor = connection.cursor()


# Saatlik trafik sonuçlarının tutulacağı tabloyu oluşturur
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS live_traffic_hourly (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        camera_name TEXT NOT NULL,

        hour_start TEXT NOT NULL,

        car_count INTEGER DEFAULT 0,

        motorcycle_count INTEGER DEFAULT 0,

        bus_count INTEGER DEFAULT 0,

        truck_count INTEGER DEFAULT 0,

        total_count INTEGER DEFAULT 0,

        created_at TEXT NOT NULL,

        updated_at TEXT NOT NULL,

        UNIQUE(camera_name, hour_start)
    )
    """
)

# Tablo oluşturma işlemini veritabanına kaydeder
connection.commit()

print("Veritabanı hazır.")


# ============================================================
# 3. YOLO MODELİ
# ============================================================

# Eğitilmiş YOLO modelini yükler
model = YOLO(MODEL_PATH)

print("YOLO modeli yüklendi.")


# ============================================================
# 4. SAYAÇLAR
# ============================================================

# Her araç sınıfının sayısını tutar
class_counts = {
    "car": 0,
    "motorcycle": 0,
    "bus": 0,
    "truck": 0
}

# Daha önce sayılan araçların takip ID'lerini tutar
# Böylece aynı araç ikinci kez sayılmaz
counted_ids = set()

# Araçların bir önceki karedeki merkez konumlarını tutar
previous_centers = {}


# ============================================================
# 5. SAAT BİLGİSİ
# ============================================================

def get_current_hour():
    """İçinde bulunulan saatin başlangıç zamanını döndürür."""

    # Güncel tarih ve saati alır
    now = datetime.now()

    # Dakika ve saniyeyi sıfırlayarak saat başlangıcını bulur
    hour_start = now.replace(
        minute=0,
        second=0,
        microsecond=0
    )

    return hour_start


# Programın başladığı saati kaydeder
current_hour = get_current_hour()


# ============================================================
# 6. VERİTABANINA KAYDETME
# ============================================================

def save_hourly_data():
    """Mevcut saate ait araç sayılarını veritabanına kaydeder."""

    # Bütün araç sınıflarının toplamını hesaplar
    total_count = sum(class_counts.values())

    # Güncel zamanı alır
    now = datetime.now()

    # Saat başlangıcını veritabanına uygun metne dönüştürür
    hour_string = current_hour.strftime(
        "%Y-%m-%d %H:00:00"
    )

    # Kayıt veya güncelleme zamanını metne dönüştürür
    now_string = now.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # Aynı kamera ve saat yoksa yeni kayıt ekler,
    # varsa mevcut araç sayılarını günceller
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

        ON CONFLICT(camera_name, hour_start)

        DO UPDATE SET
            car_count = excluded.car_count,

            motorcycle_count =
                excluded.motorcycle_count,

            bus_count = excluded.bus_count,

            truck_count = excluded.truck_count,

            total_count = excluded.total_count,

            updated_at = excluded.updated_at
        """,

        (
            CAMERA_NAME,
            hour_string,
            class_counts["car"],
            class_counts["motorcycle"],
            class_counts["bus"],
            class_counts["truck"],
            total_count,
            now_string,
            now_string
        )
    )

    # Değişiklikleri veritabanına kaydeder
    connection.commit()


# İçinde bulunulan saat için başlangıç kaydı oluşturur
save_hourly_data()


# ============================================================
# 7. CANLI YAYINI AÇAN FONKSİYON
# ============================================================

def open_stream():
    """Canlı yayını açar ve video bağlantısını döndürür."""

    print("Canlı kameraya bağlanılıyor...")

    # Canlı yayına bağlanmayı dener
    video = cv2.VideoCapture(STREAM_URL)

    # Bağlantı başarılıysa video nesnesini döndürür
    if video.isOpened():
        print("Canlı yayın başarıyla açıldı.")
        return video

    # Bağlantı başarısızsa None döndürür
    print("Canlı yayın açılamadı.")
    return None


# Canlı yayın bağlantısını başlatır
cap = open_stream()


# ============================================================
# 8. PROGRAM BAŞLANGICI
# ============================================================

print()
print("================================")
print(" CANLI TRAFİK MONİTÖRÜ")
print("================================")

print(f"Kamera: {CAMERA_NAME}")

# Analizin başladığı saati gösterir
print(
    "Saat:",
    current_hour.strftime("%Y-%m-%d %H:00")
)

print("Çıkmak için q tuşuna bas.")
print()


# ============================================================
# 9. ANA DÖNGÜ
# ============================================================

# Canlı yayını sürekli olarak işler
while True:

    # --------------------------------------------------------
    # Yayın kopmuşsa tekrar bağlan
    # --------------------------------------------------------

    if cap is None:

        # Yeniden bağlanmadan önce 2 saniye bekler
        time.sleep(2)

        cap = open_stream()

        # Döngünün başına döner
        continue


    # Canlı yayından bir kare alır
    ret, frame = cap.read()


    # --------------------------------------------------------
    # Görüntü alınamıyorsa yeniden bağlan
    # --------------------------------------------------------

    if not ret:

        print(
            "Yayından görüntü alınamadı. "
            "Tekrar bağlanılıyor..."
        )

        # Başarısız bağlantıyı kapatır
        cap.release()
        cap = None

        time.sleep(2)
        continue


    # --------------------------------------------------------
    # Saat değişti mi?
    # --------------------------------------------------------

    # Güncel saati tekrar alır
    detected_hour = get_current_hour()

    # Yeni bir saate geçilip geçilmediğini kontrol eder
    if detected_hour != current_hour:

        # Tamamlanan saatin son sonuçlarını kaydeder
        save_hourly_data()

        print()
        print("Saat değişti.")

        print(
            "Tamamlanan saat:",
            current_hour.strftime("%Y-%m-%d %H:00")
        )

        print(
            "Toplam araç:",
            sum(class_counts.values())
        )

        # Güncel saat bilgisini yeni saatle değiştirir
        current_hour = detected_hour

        # Yeni saat için araç sayaçlarını sıfırlar
        class_counts = {
            "car": 0,
            "motorcycle": 0,
            "bus": 0,
            "truck": 0
        }

        # Eski saate ait sayılan ID'leri temizler
        counted_ids.clear()

        # Eski araç konumlarını temizler
        previous_centers.clear()

        # Yeni saat için boş veritabanı kaydı oluşturur
        save_hourly_data()

        print(
            "Yeni saat:",
            current_hour.strftime("%Y-%m-%d %H:00")
        )

        print()


    # --------------------------------------------------------
    # Görüntü boyutları
    # --------------------------------------------------------

    # Karenin yüksekliğini ve genişliğini alır
    height, width = frame.shape[:2]


    # --------------------------------------------------------
    # Sayım çizgisi
    # --------------------------------------------------------

    # Yatay sayım çizgisinin dikey konumunu belirler
    line_y = int(height * 0.62)

    # Sayım çizgisinin başlangıç ve bitiş noktalarını belirler
    line_x1 = int(width * 0.25)
    line_x2 = int(width * 0.90)


    # --------------------------------------------------------
    # YOLO + ByteTrack
    # --------------------------------------------------------

    # Araçları tespit eder ve her araca takip ID'si verir
    results = model.track(
        frame,

        # Takip bilgilerinin kareler arasında korunmasını sağlar
        persist=True,

        # ByteTrack ayar dosyasını kullanır
        tracker="trackers/bytetrack_traffic.yaml",

        # Minimum güven eşiğini belirler
        conf=0.15,

        # Modelin görüntüyü işleyeceği boyutu belirler
        imgsz=960,

        # Yalnızca belirlenen araç sınıflarını tespit eder
        classes=VEHICLE_CLASSES,

        # Her kare için terminal çıktısını kapatır
        verbose=False
    )

    # Mevcut kareye ait sonucu alır
    result = results[0]


    # --------------------------------------------------------
    # Araçları işle
    # --------------------------------------------------------

    # Tespit kutuları ve takip ID'leri varsa çalışır
    if (
        result.boxes is not None
        and result.boxes.id is not None
    ):

        # Araçların kutu koordinatlarını alır
        boxes = (
            result.boxes.xyxy
            .cpu()
            .numpy()
        )

        # Araçların takip ID'lerini listeye çevirir
        track_ids = (
            result.boxes.id
            .int()
            .cpu()
            .tolist()
        )

        # Araçların sınıf numaralarını listeye çevirir
        class_ids = (
            result.boxes.cls
            .int()
            .cpu()
            .tolist()
        )

        # Araçların güven değerlerini listeye çevirir
        confidences = (
            result.boxes.conf
            .cpu()
            .tolist()
        )


        # Her tespit edilen aracı sırayla işler
        for (
            box,
            track_id,
            class_id,
            confidence

        ) in zip(
            boxes,
            track_ids,
            class_ids,
            confidences
        ):

            # Bounding box koordinatlarını tam sayıya çevirir
            x1, y1, x2, y2 = map(int, box)

            # Aracın yatay merkez noktasını hesaplar
            center_x = int((x1 + x2) / 2)

            # Aracın dikey merkez noktasını hesaplar
            center_y = int((y1 + y2) / 2)

            # Sınıf numarasını araç adına dönüştürür
            class_name = model.names[class_id]


            # ------------------------------------------------
            # Çizgi geçiş kontrolü
            # ------------------------------------------------

            # Aracın önceki konumu bulunuyorsa hareketini kontrol eder
            if track_id in previous_centers:

                # Aracın bir önceki merkez konumunu alır
                previous_x, previous_y = (
                    previous_centers[track_id]
                )

                # Araç çizginin bir tarafından diğer tarafına geçti mi?
                crossed_line = (
                    (
                        previous_y < line_y
                        and center_y >= line_y
                    )
                    or
                    (
                        previous_y > line_y
                        and center_y <= line_y
                    )
                )

                # Araç, sayım çizgisinin yatay sınırları içinde mi?
                inside_line = (
                    line_x1
                    <= center_x
                    <= line_x2
                )


                # --------------------------------------------
                # Araç sayımı
                # --------------------------------------------

                # Araç çizgiyi geçtiyse, çizginin içindeyse ve
                # daha önce sayılmadıysa sayım işlemini yapar
                if (
                    crossed_line
                    and inside_line
                    and track_id not in counted_ids
                ):

                    # Araç sınıfı sayaçlarda bulunuyorsa artırır
                    if class_name in class_counts:

                        # Aynı aracın tekrar sayılmasını engeller
                        counted_ids.add(track_id)

                        # İlgili araç sınıfının sayısını artırır
                        class_counts[class_name] += 1

                        print(
                            f"Sayildi -> "
                            f"ID: {track_id}, "
                            f"Sinif: {class_name}, "
                            f"Confidence: {confidence:.2f}"
                        )

                        # Araç sayıldığı anda veritabanını günceller
                        save_hourly_data()


            # Aracın mevcut konumunu bir sonraki kare için saklar
            previous_centers[track_id] = (
                center_x,
                center_y
            )


            # ------------------------------------------------
            # Bounding box
            # ------------------------------------------------

            # Aracın çevresine dikdörtgen kutu çizer
            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (255, 255, 255),
                2
            )

            # Aracın merkez noktasını çizer
            cv2.circle(
                frame,
                (center_x, center_y),
                4,
                (255, 255, 255),
                -1
            )


            # ------------------------------------------------
            # Araç etiketi
            # ------------------------------------------------

            # ID, sınıf ve güven değerinden etiket oluşturur
            label = (
                f"ID:{track_id} "
                f"{class_name} "
                f"{confidence:.2f}"
            )

            # Etiketi aracın kutusunun üzerine yazar
            cv2.putText(
                frame,
                label,
                (
                    x1,
                    max(y1 - 10, 20)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2
            )


    # ========================================================
    # 10. SAYIM ÇİZGİSİ
    # ========================================================

    # Araçların geçiş yapacağı sayım çizgisini çizer
    cv2.line(
        frame,
        (line_x1, line_y),
        (line_x2, line_y),
        (255, 255, 255),
        3
    )

    # Çizginin üzerine açıklama metni ekler
    cv2.putText(
        frame,
        "COUNTING LINE",
        (line_x1, line_y - 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )


    # ========================================================
    # 11. EKRANDA İSTATİSTİKLER
    # ========================================================

    # Sayılan bütün araçların toplamını hesaplar
    total_count = sum(class_counts.values())

    # Toplam araç sayısını ekrana yazar
    cv2.putText(
        frame,
        f"TOTAL: {total_count}",
        (30, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2
    )

    # Otomobil sayısını ekrana yazar
    cv2.putText(
        frame,
        f"Car: {class_counts['car']}",
        (30, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    # Motosiklet sayısını ekrana yazar
    cv2.putText(
        frame,
        f"Motorcycle: {class_counts['motorcycle']}",
        (30, 105),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    # Otobüs sayısını ekrana yazar
    cv2.putText(
        frame,
        f"Bus: {class_counts['bus']}",
        (30, 135),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    # Kamyon sayısını ekrana yazar
    cv2.putText(
        frame,
        f"Truck: {class_counts['truck']}",
        (30, 165),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    # Analiz edilen saat bilgisini ekrana yazar
    cv2.putText(
        frame,
        current_hour.strftime("%Y-%m-%d %H:00"),
        (30, 200),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )


    # ========================================================
    # 12. GÖRÜNTÜYÜ GÖSTER
    # ========================================================

    # İşlenmiş canlı trafik görüntüsünü ekranda gösterir
    cv2.imshow(
        "Canli Trafik Monitoru",
        frame
    )

    # Klavyeden q tuşuna basılırsa döngüyü bitirir
    if (
        cv2.waitKey(1)
        & 0xFF
        == ord("q")
    ):
        break


# ============================================================
# 13. PROGRAM KAPANIRKEN SON VERİYİ KAYDET
# ============================================================

# Program kapanmadan önce son sayaçları kaydeder
save_hourly_data()

# Canlı yayın açıksa bağlantıyı kapatır
if cap is not None:
    cap.release()

# OpenCV tarafından açılan bütün pencereleri kapatır
cv2.destroyAllWindows()

# Veritabanı bağlantısını kapatır
connection.close()


# Programın sonundaki araç sayılarını gösterir
print()
print("================================")
print(" CANLI TRAFİK MONİTÖRÜ DURDU")
print("================================")

print(f"Car: {class_counts['car']}")
print(f"Motorcycle: {class_counts['motorcycle']}")
print(f"Bus: {class_counts['bus']}")
print(f"Truck: {class_counts['truck']}")
print(f"Total: {sum(class_counts.values())}")

print(
    "Saatlik veriler "
    "traffic_analysis.db "
    "dosyasına kaydedildi."
)