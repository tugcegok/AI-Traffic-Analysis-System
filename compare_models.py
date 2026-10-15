# OpenCV: Videoyu açmak ve görüntü kaydetmek için
import cv2

# YOLO: Araçları tespit etmek için
from ultralytics import YOLO


# İncelenecek videonun yolu
VIDEO_PATH = "uploads/20581-310903371.mp4"

# Hazır eğitilmiş YOLO modelini yükler
model = YOLO("yolo11n.pt")

# Videoyu açar
cap = cv2.VideoCapture(VIDEO_PATH)

# Video açılmadıysa programı durdurur
if not cap.isOpened():
    print("Video açılamadı.")
    exit()


# İşlenen karelerin sayısını tutar
frame_number = 0

# Motosiklet bulunup bulunmadığını tutar
motorcycle_found = False


# Videoyu kare kare inceler
while True:

    # Videodan bir kare okur
    ret, frame = cap.read()

    # Kare okunamazsa video bitmiştir
    if not ret:
        break

    # Kare numarasını bir artırır
    frame_number += 1

    # Mevcut karede araç tespiti yapar
    results = model.predict(
        frame,

        # En az %10 güvene sahip tespitleri alır
        conf=0.10,

        # Küçük ve uzaktaki araçlar için görüntü boyutu
        imgsz=1280,

        # COCO sınıfları:
        # 2 = araba, 3 = motosiklet
        # 5 = otobüs, 7 = kamyon
        classes=[2, 3, 5, 7],

        # Her karede terminal çıktısı verilmesini engeller
        verbose=False
    )

    # İşlenen karenin sonucunu alır
    result = results[0]

    # Hiç tespit yoksa sonraki kareye geçer
    if result.boxes is None or len(result.boxes) == 0:
        continue

    # Tespit edilen nesnelerin sınıf numaralarını listeye çevirir
    class_ids = (
        result.boxes.cls
        .int()
        .cpu()
        .tolist()
    )

    # 3 numaralı sınıf motosiklettir
    if 3 in class_ids:

        # Motosiklet bulunduğunu kaydeder
        motorcycle_found = True

        print(f"Motosiklet bulundu! Frame: {frame_number}")

        # Tespit kutularını karenin üzerine çizer
        annotated_frame = result.plot()

        # İşaretlenmiş kareyi JPG olarak kaydeder
        cv2.imwrite(
            "motorcycle_test.jpg",
            annotated_frame
        )

        # İlk motosiklet bulunduğu için döngüyü bitirir
        break


# Video kaynağını kapatır
cap.release()


# İşlemin sonucunu terminalde gösterir
if motorcycle_found:
    print("motorcycle_test.jpg oluşturuldu.")
else:
    print("Bu videoda YOLO tarafından motosiklet tespit edilemedi.")