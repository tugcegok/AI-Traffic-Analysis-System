import cv2
from ultralytics import YOLO

# --------------------------------------------------
# 1. CANLI KAMERA
# --------------------------------------------------

stream_url = (
    "https://601a55c88ec6d.streamlock.net/"
    "hls/699.stream/playlist.m3u8"
)

# Daha güçlü hazır YOLO modeli
model = YOLO("yolo11s.pt")

# COCO araç sınıfları
vehicle_classes = [2, 3, 5, 7]

# 2 = car
# 3 = motorcycle
# 5 = bus
# 7 = truck


# --------------------------------------------------
# 2. CANLI YAYINI AÇ
# --------------------------------------------------

cap = cv2.VideoCapture(stream_url)

if not cap.isOpened():
    print("Canlı yayın açılamadı.")
    exit()

print("Canlı yayın başarıyla açıldı.")
print("YOLO + ByteTrack araç sayımı başladı.")
print("Çıkmak için q tuşuna bas.")


# --------------------------------------------------
# 3. SAYIM DEĞİŞKENLERİ
# --------------------------------------------------

class_counts = {
    "car": 0,
    "motorcycle": 0,
    "bus": 0,
    "truck": 0
}

# Daha önce sayılmış araçların ID'leri
counted_ids = set()

# Her aracın bir önceki merkez konumu
previous_centers = {}


# --------------------------------------------------
# 4. CANLI GÖRÜNTÜ DÖNGÜSÜ
# --------------------------------------------------

while True:

    ret, frame = cap.read()

    if not ret:
        print("Görüntü alınamadı.")
        break

    height, width = frame.shape[:2]


    # --------------------------------------------------
    # 5. SAYIM ÇİZGİSİ
    # --------------------------------------------------

    line_y = int(height * 0.62)

    # Çizginin sadece yol üzerinde kalan kısmı
    line_x1 = int(width * 0.25)
    line_x2 = int(width * 0.90)


    # --------------------------------------------------
    # 6. YOLO + BYTETRACK
    # --------------------------------------------------

    results = model.track(
        frame,
        persist=True,
        tracker="trackers/bytetrack_traffic.yaml",
        conf=0.15,
        imgsz=960,
        classes=vehicle_classes,
        verbose=False
    )

    result = results[0]


    # --------------------------------------------------
    # 7. ARAÇLARI İNCELE
    # --------------------------------------------------

    if (
        result.boxes is not None
        and result.boxes.id is not None
    ):

        boxes = result.boxes.xyxy.cpu().numpy()

        track_ids = (
            result.boxes.id
            .int()
            .cpu()
            .tolist()
        )

        class_ids = (
            result.boxes.cls
            .int()
            .cpu()
            .tolist()
        )

        confidences = (
            result.boxes.conf
            .cpu()
            .tolist()
        )


        # --------------------------------------------------
        # 8. HER ARAÇ İÇİN
        # --------------------------------------------------

        for box, track_id, class_id, confidence in zip(
            boxes,
            track_ids,
            class_ids,
            confidences
        ):

            x1, y1, x2, y2 = map(int, box)

            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)

            class_name = model.names[class_id]


            # --------------------------------------------------
            # 9. ÇİZGİ GEÇİŞİNİ KONTROL ET
            # --------------------------------------------------

            if track_id in previous_centers:

                previous_x, previous_y = (
                    previous_centers[track_id]
                )

                # Araç yukarıdan aşağıya
                # veya aşağıdan yukarıya çizgiyi geçti mi?
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

                # Araç çizginin yol üzerindeki
                # bölümünden mi geçti?
                inside_counting_area = (
                    line_x1
                    <= center_x
                    <= line_x2
                )


                # --------------------------------------------------
                # 10. ARACI SAY
                # --------------------------------------------------

                if (
                    crossed_line
                    and inside_counting_area
                    and track_id not in counted_ids
                ):

                    counted_ids.add(track_id)

                    if class_name in class_counts:

                        class_counts[class_name] += 1

                        print(
                            f"Sayildi -> "
                            f"ID: {track_id}, "
                            f"Sinif: {class_name}, "
                            f"Confidence: "
                            f"{confidence:.2f}"
                        )


            # Güncel merkez konumunu kaydet
            previous_centers[track_id] = (
                center_x,
                center_y
            )


            # --------------------------------------------------
            # 11. BOUNDING BOX ÇİZ
            # --------------------------------------------------

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (255, 255, 255),
                2
            )


            # Aracın merkez noktası
            cv2.circle(
                frame,
                (center_x, center_y),
                5,
                (255, 255, 255),
                -1
            )


            # ID + sınıf + confidence
            label = (
                f"ID:{track_id} "
                f"{class_name} "
                f"{confidence:.2f}"
            )

            cv2.putText(
                frame,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2
            )


    # --------------------------------------------------
    # 12. SAYIM ÇİZGİSİNİ ÇİZ
    # --------------------------------------------------

    cv2.line(
        frame,
        (line_x1, line_y),
        (line_x2, line_y),
        (255, 255, 255),
        3
    )


    cv2.putText(
        frame,
        "COUNTING LINE",
        (line_x1, line_y - 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


    # --------------------------------------------------
    # 13. TOPLAM SAYILAR
    # --------------------------------------------------

    total_count = sum(class_counts.values())

    cv2.putText(
        frame,
        f"TOTAL: {total_count}",
        (30, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Car: {class_counts['car']}",
        (30, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Motorcycle: {class_counts['motorcycle']}",
        (30, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Bus: {class_counts['bus']}",
        (30, 140),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Truck: {class_counts['truck']}",
        (30, 170),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


    # --------------------------------------------------
    # 14. GÖRÜNTÜYÜ GÖSTER
    # --------------------------------------------------

    cv2.imshow(
        "Canli Trafik - Arac Sayimi",
        frame
    )


    # q ile çık
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# --------------------------------------------------
# 15. PROGRAMI KAPAT
# --------------------------------------------------

cap.release()
cv2.destroyAllWindows()

print()
print("Canlı araç sayımı durduruldu.")
print("Sonuç:")
print(f"Car: {class_counts['car']}")
print(
    f"Motorcycle: "
    f"{class_counts['motorcycle']}"
)
print(f"Bus: {class_counts['bus']}")
print(f"Truck: {class_counts['truck']}")
print(
    f"Total: "
    f"{sum(class_counts.values())}"
)