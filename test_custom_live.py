import cv2
from ultralytics import YOLO

stream_url = "https://601a55c88ec6d.streamlock.net/hls/699.stream/playlist.m3u8"

# Kendi eğittiğimiz model
model = YOLO("models/best.pt")

# Kendi modelimizin sınıf numaraları:
# 0 = bus
# 1 = car
# 2 = motorbike
# 3 = person
# 4 = truck

vehicle_classes = [0, 1, 2, 4]

cap = cv2.VideoCapture(stream_url)

if not cap.isOpened():
    print("Canlı yayın açılamadı.")
    exit()

print("Canlı yayın başarıyla açıldı.")
print("Custom best.pt modeli ile test başladı.")

while True:
    ret, frame = cap.read()

    if not ret:
        print("Görüntü alınamadı.")
        break

    results = model(
        frame,
        conf=0.10,
        imgsz=1280,
        classes=vehicle_classes,
        verbose=False
    )

    result = results[0]

    if result.boxes is not None:

        boxes = result.boxes.xyxy.cpu().numpy()
        class_ids = result.boxes.cls.int().cpu().tolist()
        confidences = result.boxes.conf.cpu().tolist()

        for box, class_id, confidence in zip(
            boxes,
            class_ids,
            confidences
        ):

            x1, y1, x2, y2 = map(int, box)

            class_name = model.names[class_id]

            # Datasetimizde isim "motorbike"
            # Ekranda daha anlaşılır olması için "motorcycle" yazdırıyoruz.
            if class_name == "motorbike":
                display_name = "motorcycle"
            else:
                display_name = class_name

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                f"{display_name} {confidence:.2f}",
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

    cv2.imshow(
        "Canli Trafik - Custom best.pt Test",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()