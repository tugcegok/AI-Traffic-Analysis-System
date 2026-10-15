import cv2
from ultralytics import YOLO

stream_url = "https://601a55c88ec6d.streamlock.net/hls/699.stream/playlist.m3u8"

model = YOLO("yolo11n.pt")

vehicle_classes = [2, 3, 5, 7]
# 2 = car
# 3 = motorcycle
# 5 = bus
# 7 = truck

cap = cv2.VideoCapture(stream_url)

if not cap.isOpened():
    print("Canlı yayın açılamadı.")
    exit()

print("Canlı yayın başarıyla açıldı.")
print("YOLO araç tespiti başladı.")

while True:
    ret, frame = cap.read()

    if not ret:
        print("Görüntü alınamadı.")
        break

    results = model(
        frame,
        conf=0.25,
        classes=vehicle_classes,
        verbose=False
    )

    annotated_frame = results[0].plot()

    cv2.imshow("Canli Trafik - YOLO", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()