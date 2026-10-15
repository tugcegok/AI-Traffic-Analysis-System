#yüklenen trafik videosunu açmak, YOLO ile araçları tespit etmek
#bytetrack ile takip etmek, araçları saymak 
#şerit/yön/yoğunluk analizi yapmak 
#işlenmiş videoyu ve cvs raporunu üretmek 


import cv2
import csv
import numpy as np

from pathlib import Path
from collections import defaultdict
from ultralytics import YOLO


# --------------------------------------------------
# DOSYA VE KLASÖR YOLLARI
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

# Hazır YOLO11n modeli
MODEL_PATH = BASE_DIR / "yolo11n.pt"

TRACKER_PATH = (
    BASE_DIR
    / "trackers"
    / "bytetrack_traffic.yaml"
)

OUTPUT_DIR = BASE_DIR / "outputs"
REPORT_DIR = BASE_DIR / "reports"

OUTPUT_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)


# --------------------------------------------------
# VIDEO ANALİZ FONKSİYONU
# --------------------------------------------------

def analyze_video(video_path):

    model = YOLO(str(MODEL_PATH))

    cap = cv2.VideoCapture(str(video_path))

    fps = cap.get(cv2.CAP_PROP_FPS)

    width = int(
        cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    )

    height = int(
        cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    )

    total_frames = int(
        cap.get(cv2.CAP_PROP_FRAME_COUNT)
    )

    duration_seconds = (
        total_frames / fps
        if fps > 0
        else 0
    )


    # --------------------------------------------------
    # ÇIKTI DOSYALARI
    # --------------------------------------------------

    output_video_path = (
        OUTPUT_DIR / "processed_video.mp4"
    )

    csv_path = (
        REPORT_DIR / "analysis_report.csv"
    )

    fourcc = cv2.VideoWriter_fourcc(
        *"mp4v"
    )

    writer = cv2.VideoWriter(
        str(output_video_path),
        fourcc,
        fps,
        (width, height)
    )


    # --------------------------------------------------
    # SAYIM BÖLGESİ
    # --------------------------------------------------

    zone_top = int(height * 0.34)
    zone_bottom = int(height * 0.49)

    warmup_frames = 15
    min_inside_frames = 3

    counted_ids = set() #daha önce hangi araçları saydım


    # --------------------------------------------------
    # TAKİP BİLGİLERİ
    # --------------------------------------------------

    track_data = defaultdict(
        lambda: {
            "seen_outside": False,
            "inside_frames": 0,
            "first_y": None,
            "last_y": None,
            "class_name": None
        }
    )


    # --------------------------------------------------
    # ARAÇ SAYILARI
    # --------------------------------------------------

    vehicle_counts = {
        "car": 0,
        "bus": 0,
        "truck": 0,
        "motorcycle": 0
    }


    # --------------------------------------------------
    # ŞERİT BAZLI ARAÇ SAYILARI
    # 6 şerit burda 
    # --------------------------------------------------

    lane_counts = {
        "lane_1": 0,
        "lane_2": 0,
        "lane_3": 0,
        "lane_4": 0,
        "lane_5": 0,
        "lane_6": 0
    }

    # Herhangi bir şeride atanamayan araçlar
    lane_unknown = 0

    # Track ID -> şerit
    vehicle_lanes = {}


    # --------------------------------------------------
    # ŞERİT POLİGONLARI
    # --------------------------------------------------
    #
    # Perspektif nedeniyle şeritler dikdörtgen değil,
    # dörtgen poligonlar olarak tanımlanmıştır.
    #
    # Sol yol:
    # lane_1, lane_2, lane_3
    #
    # Sağ yol:
    # lane_4, lane_5, lane_6
    # --------------------------------------------------

    lane_polygons = {

        # --------------------------------------------------
        # SOL YOL
        # --------------------------------------------------

        "lane_1": np.array(
            [
                [
                    int(width * 0.00),
                    zone_bottom
                ],
                [
                    int(width * 0.15),
                    zone_top
                ],
                [
                    int(width * 0.33),
                    zone_top
                ],
                [
                    int(width * 0.18),
                    zone_bottom
                ]
            ],
            dtype=np.int32
        ),

        "lane_2": np.array(
            [
                [
                    int(width * 0.18),
                    zone_bottom
                ],
                [
                    int(width * 0.33),
                    zone_top
                ],
                [
                    int(width * 0.39),
                    zone_top
                ],
                [
                    int(width * 0.35),
                    zone_bottom
                ]
            ],
            dtype=np.int32
        ),

        "lane_3": np.array(
            [
                [
                    int(width * 0.35),
                    zone_bottom
                ],
                [
                    int(width * 0.39),
                    zone_top
                ],
                [
                    int(width * 0.46),
                    zone_top
                ],
                [
                    int(width * 0.48),
                    zone_bottom
                ]
            ],
            dtype=np.int32
        ),


        # --------------------------------------------------
        # SAĞ YOL
        # --------------------------------------------------

        "lane_4": np.array(
            [
                [
                    int(width * 0.52),
                    zone_bottom
                ],
                [
                    int(width * 0.54),
                    zone_top
                ],
                [
                    int(width * 0.61),
                    zone_top
                ],
                [
                    int(width * 0.65),
                    zone_bottom
                ]
            ],
            dtype=np.int32
        ),

        "lane_5": np.array(
            [
                [
                    int(width * 0.65),
                    zone_bottom
                ],
                [
                    int(width * 0.61),
                    zone_top
                ],
                [
                    int(width * 0.67),
                    zone_top
                ],
                [
                    int(width * 0.82),
                    zone_bottom
                ]
            ],
            dtype=np.int32
        ),

        "lane_6": np.array(
            [
                [
                    int(width * 0.82),
                    zone_bottom
                ],
                [
                    int(width * 0.67),
                    zone_top
                ],
                [
                    int(width * 0.94),
                    zone_top
                ],
                [
                    int(width * 1.00),
                    zone_bottom
                ]
            ],
            dtype=np.int32
        )
    }


    frame_number = 0


    # --------------------------------------------------
    # VİDEOYU KARE KARE İŞLE
    # --------------------------------------------------

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        frame_number += 1


        # --------------------------------------------------
        # YOLO + BYTETRACK
        # --------------------------------------------------

        results = model.track(
            frame,

            persist=True,

            tracker=str(TRACKER_PATH),

            conf=0.10,

            imgsz=1280,

            # COCO:
            # 2 = car
            # 3 = motorcycle
            # 5 = bus
            # 7 = truck
            classes=[2, 3, 5, 7],

            verbose=False
        )

        result = results[0]


        # --------------------------------------------------
        # SAYIM BÖLGESİNİ ÇİZ
        # --------------------------------------------------

        cv2.line(
            frame,
            (0, zone_top),
            (width, zone_top),
            (0, 255, 255),
            6
        )

        cv2.line(
            frame,
            (0, zone_bottom),
            (width, zone_bottom),
            (0, 255, 255),
            6
        )


        # --------------------------------------------------
        # ŞERİT POLİGONLARINI ÇİZ
        # --------------------------------------------------

        for lane_name, polygon in lane_polygons.items():

            cv2.polylines(
                frame,
                [polygon],
                True,
                (255, 0, 255),
                5
            )

            moments = cv2.moments(
                polygon
            )

            if moments["m00"] != 0:

                label_x = int(
                    moments["m10"]
                    / moments["m00"]
                )

                label_y = int(
                    moments["m01"]
                    / moments["m00"]
                )

                cv2.putText(
                    frame,
                    lane_name.upper(),
                    (
                        label_x - 60,
                        label_y
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (255, 0, 255),
                    3
                )


        # --------------------------------------------------
        # TESPİTLER
        # --------------------------------------------------

        if (
            result.boxes is not None
            and len(result.boxes) > 0
        ):

            boxes = (
                result.boxes.xyxy
                .cpu()
                .numpy()
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


            if result.boxes.id is not None:

                track_ids = (
                    result.boxes.id
                    .int()
                    .cpu()
                    .tolist()
                )

            else:

                track_ids = (
                    [None] * len(boxes)
                )


            # --------------------------------------------------
            # HER TESPİT İÇİN
            # --------------------------------------------------

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

                x1, y1, x2, y2 = map(
                    int,
                    box
                )


                # --------------------------------------------------
                # ARAÇ MERKEZ NOKTASI
                # --------------------------------------------------

                center_x = int(
                    (x1 + x2) / 2
                )

                center_y = int(
                    (y1 + y2) / 2
                )


                # --------------------------------------------------
                # SINIF ADI
                # --------------------------------------------------

                class_name = model.names[
                    class_id
                ]


                # --------------------------------------------------
                # BOUNDING BOX
                # --------------------------------------------------

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    5
                )


                if track_id is not None:

                    label = (
                        f"ID:{track_id} "
                        f"{class_name} "
                        f"{confidence:.2f}"
                    )

                else:

                    label = (
                        f"{class_name} "
                        f"{confidence:.2f}"
                    )


                cv2.putText(
                    frame,
                    label,
                    (
                        x1,
                        max(y1 - 10, 30)
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    3
                )


                # --------------------------------------------------
                # MERKEZ NOKTASINI ÇİZ
                # --------------------------------------------------

                cv2.circle(
                    frame,
                    (center_x, center_y),
                    8,
                    (0, 0, 255),
                    -1
                )


                # --------------------------------------------------
                # ID YOKSA SAYIMA DAHİL ETME
                # --------------------------------------------------

                if track_id is None:
                    continue


                data = track_data[
                    track_id
                ]


                if data["first_y"] is None:

                    data["first_y"] = (
                        center_y
                    )


                data["last_y"] = (
                    center_y
                )

                data["class_name"] = (
                    class_name
                )


                # --------------------------------------------------
                # SAYIM BÖLGESİ KONTROLÜ
                # --------------------------------------------------

                inside_zone = (
                    zone_top
                    <= center_y
                    <= zone_bottom
                )


                if not inside_zone:

                    data[
                        "seen_outside"
                    ] = True


                if inside_zone:

                    data[
                        "inside_frames"
                    ] += 1


                    should_count = (

                        track_id
                        not in counted_ids

                        and

                        frame_number
                        > warmup_frames

                        and

                        (
                            data[
                                "seen_outside"
                            ]

                            or

                            data[
                                "inside_frames"
                            ]
                            >= min_inside_frames
                        )
                    )


                    # --------------------------------------------------
                    # ARAÇ SAYIMI
                    # --------------------------------------------------

                    if should_count:

                        counted_ids.add(
                            track_id
                        )


                        if (
                            class_name
                            in vehicle_counts
                        ):

                            vehicle_counts[
                                class_name
                            ] += 1


                        # --------------------------------------------------
                        # ŞERİT TESPİTİ
                        # --------------------------------------------------

                        detected_lane = None


                        for (
                            lane_name,
                            polygon
                        ) in lane_polygons.items():

                            point_result = (
                                cv2.pointPolygonTest(
                                    polygon,
                                    (
                                        float(center_x),
                                        float(center_y)
                                    ),
                                    False
                                )
                            )


                            # pointPolygonTest sonucu:
                            #
                            # Pozitif -> poligonun içinde
                            # 0       -> poligon sınırında
                            # Negatif -> poligonun dışında

                            if point_result >= 0:

                                detected_lane = (
                                    lane_name
                                )

                                break


                        # --------------------------------------------------
                        # ŞERİT SAYACINI ARTIR
                        # --------------------------------------------------

                        if detected_lane is not None:

                            lane_counts[
                                detected_lane
                            ] += 1

                            vehicle_lanes[
                                track_id
                            ] = detected_lane

                        else:

                            # Araç genel sayımda sayıldı fakat
                            # tanımlanan 6 şerit poligonundan
                            # hiçbirine girmedi.
                            lane_unknown += 1

                            vehicle_lanes[
                                track_id
                            ] = "unknown"


        # --------------------------------------------------
        # ANLIK TOPLAM
        # --------------------------------------------------

        total_now = sum(
            vehicle_counts.values()
        )


        cv2.putText(
            frame,
            f"Total: {total_now}",
            (50, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            2,
            (255, 255, 255),
            5
        )


        # --------------------------------------------------
        # ANLIK ŞERİT SAYILARI
        # --------------------------------------------------

        lane_text = (
            f"L1:{lane_counts['lane_1']}  "
            f"L2:{lane_counts['lane_2']}  "
            f"L3:{lane_counts['lane_3']}  "
            f"L4:{lane_counts['lane_4']}  "
            f"L5:{lane_counts['lane_5']}  "
            f"L6:{lane_counts['lane_6']}  "
            f"U:{lane_unknown}"
        )


        cv2.putText(
            frame,
            lane_text,
            (50, 170),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (255, 255, 255),
            4
        )


        writer.write(
            frame
        )


    # --------------------------------------------------
    # VİDEOYU KAPAT
    # --------------------------------------------------

    cap.release()
    writer.release()


    # --------------------------------------------------
    # TOPLAM ARAÇ
    # --------------------------------------------------

    total_vehicle = sum(
        vehicle_counts.values()
    )


    # --------------------------------------------------
    # ŞERİTLERE ATANAN TOPLAM ARAÇ
    # --------------------------------------------------

    lane_total = sum(
        lane_counts.values()
    )


    # --------------------------------------------------
    # ŞERİT KONTROL TOPLAMI
    # --------------------------------------------------
    #
    # Bu değerin total_vehicle ile aynı olması beklenir:
    #
    # lane_total + lane_unknown = total_vehicle
    # --------------------------------------------------

    lane_control_total = (
        lane_total
        + lane_unknown
    )


    # --------------------------------------------------
    # ARAÇ / DAKİKA
    # --------------------------------------------------

    if duration_seconds > 0:

        vehicles_per_minute = (
            total_vehicle
            / duration_seconds
        ) * 60

    else:

        vehicles_per_minute = 0


    # --------------------------------------------------
    # TRAFİK YOĞUNLUĞU
    # --------------------------------------------------

    if vehicles_per_minute < 30:

        density = "DUSUK"

    elif vehicles_per_minute < 60:

        density = "ORTA"

    else:

        density = "YUKSEK"


    # --------------------------------------------------
    # YÖN ANALİZİ
    # --------------------------------------------------

    direction_up = 0
    direction_down = 0
    direction_unknown = 0


    for track_id in counted_ids:

        data = track_data[
            track_id
        ]

        first_y = data[
            "first_y"
        ]

        last_y = data[
            "last_y"
        ]


        if (
            first_y is None
            or last_y is None
        ):

            direction_unknown += 1
            continue


        difference = (
            last_y - first_y
        )


        if difference > 30:

            direction_down += 1


        elif difference < -30:

            direction_up += 1


        else:

            direction_unknown += 1


    # --------------------------------------------------
    # RAPOR
    # --------------------------------------------------

    report = {

        # Araç sınıfları
        "car":
            vehicle_counts["car"],

        "bus":
            vehicle_counts["bus"],

        "truck":
            vehicle_counts["truck"],

        "motorcycle":
            vehicle_counts["motorcycle"],

        "total":
            total_vehicle,


        # Trafik yoğunluğu
        "vehicles_per_minute":
            round(
                vehicles_per_minute,
                2
            ),

        "density":
            density,


        # Yön analizi
        "direction_up":
            direction_up,

        "direction_down":
            direction_down,

        "direction_unknown":
            direction_unknown,


        # --------------------------------------------------
        # ŞERİT SONUÇLARI
        # --------------------------------------------------

        "lane_1":
            lane_counts["lane_1"],

        "lane_2":
            lane_counts["lane_2"],

        "lane_3":
            lane_counts["lane_3"],

        "lane_4":
            lane_counts["lane_4"],

        "lane_5":
            lane_counts["lane_5"],

        "lane_6":
            lane_counts["lane_6"],


        # 6 şeride atanabilen toplam araç
        "lane_total":
            lane_total,


        # Hiçbir şeride atanamayan araç
        "lane_unknown":
            lane_unknown,


        # Matematiksel kontrol:
        # lane_total + lane_unknown
        "lane_control_total":
            lane_control_total,


        # --------------------------------------------------
        # DOSYA YOLLARI
        # --------------------------------------------------

        "output_video":
            str(output_video_path),

        "csv_report":
            str(csv_path)
    }


    # --------------------------------------------------
    # CSV RAPOR
    # --------------------------------------------------

    with open(
        csv_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        writer_csv = csv.writer(
            csv_file
        )

        writer_csv.writerow(
            ["Metric", "Value"]
        )


        for key, value in report.items():

            writer_csv.writerow(
                [key, value]
            )


    # --------------------------------------------------
    # SONUCU FASTAPI'YE GÖNDER
    # --------------------------------------------------

    return report