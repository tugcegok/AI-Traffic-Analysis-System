import cv2

stream_url = "https://601a55c88ec6d.streamlock.net/hls/699.stream/playlist.m3u8"

cap = cv2.VideoCapture(stream_url)

if not cap.isOpened():
    print("Canlı yayın açılamadı.")
    exit()

print("Canlı yayın başarıyla açıldı.")

while True:
    ret, frame = cap.read()

    if not ret:
        print("Görüntü alınamadı.")
        break

    cv2.imshow("Canli Trafik Kamerasi", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()