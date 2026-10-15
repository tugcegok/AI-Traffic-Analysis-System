# Bu kodun amacı, internet üzerindeki canlı trafik yayınını açmak
# ve yayından her 3 saniyede bir görüntü kaydetmektir.

# OpenCV: Canlı yayını açmak ve görüntü kaydetmek için
import cv2

# Klasör ve dosya yollarını yönetmek için
import os

# Zaman aralığını kontrol etmek için
import time


# Canlı trafik yayınının internet adresi
stream_url = (
    "https://601a55c88ec6d.streamlock.net/"
    "hls/699.stream/playlist.m3u8"
)

# Görüntülerin kaydedileceği klasör
output_folder = "live_frames"

# Klasör yoksa oluşturur, varsa hata vermez
os.makedirs(output_folder, exist_ok=True)

# Canlı yayını açar
cap = cv2.VideoCapture(stream_url)

# Canlı yayının açılıp açılmadığını kontrol eder
if not cap.isOpened():
    print("Canlı yayın açılamadı.")
    exit()

print("Canlı yayın başarıyla açıldı.")
print("Kare toplama başladı.")
print("Durdurmak için terminalde Control + C kullanabilirsin.")


# Kaydedilen karelerin sayısını tutar
frame_number = 0

# Her 3 saniyede bir kare kaydedileceğini belirtir
save_interval = 3

# Son karenin kaydedildiği zamanı tutar
last_save_time = 0


try:
    # Canlı yayını sürekli olarak okur
    while True:

        # Canlı yayından bir kare alır
        ret, frame = cap.read()

        # Kare alınamazsa bir saniye bekleyip tekrar dener
        if not ret:
            print("Görüntü alınamadı, tekrar deneniyor...")
            time.sleep(1)
            continue

        # O anki zamanı saniye cinsinden alır
        current_time = time.time()

        # Son kayıttan itibaren 3 saniye geçtiyse çalışır
        if current_time - last_save_time >= save_interval:

            # Kaydedilecek görüntünün dosya yolunu oluşturur
            filename = os.path.join(
                output_folder,
                f"frame_{frame_number:04d}.jpg"
            )

            # Kareyi JPG dosyası olarak kaydeder
            cv2.imwrite(filename, frame)

            print(f"Kaydedildi: {filename}")

            # Kaydedilen kare sayısını bir artırır
            frame_number += 1

            # Son kayıt zamanını günceller
            last_save_time = current_time

# Control + C ile durdurulduğunda hata mesajını engeller
except KeyboardInterrupt:
    print("\nKare toplama kullanıcı tarafından durduruldu.")

finally:
    # Canlı yayın bağlantısını kapatır
    cap.release()

    # Toplam kaydedilen kare sayısını gösterir
    print("Kare toplama tamamlandı.")
    print(f"Toplam kaydedilen kare: {frame_number}")