from pathlib import Path
import shutil

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Request,
    HTTPException,
    Depends
)

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse

from sqlalchemy import text

from app.analyzer import analyze_video

# Veritabanı
from app.database import Base, engine, SessionLocal

# Veritabanı modelleri
from app.models import Analysis, User

# Pydantic şemaları
from app.schemas import UserRegister, UserLogin

# Şifre ve JWT işlemleri
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    verify_access_token
)


# ============================================================
# VERİTABANI TABLOLARINI OLUŞTUR
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# FASTAPI UYGULAMASI
# ============================================================

app = FastAPI(
    title="Traffic Analysis API",
    description=(
        "Araç tespit, takip, canlı trafik izleme "
        "ve trafik yoğunluğu analiz sistemi"
    ),
    version="2.0.0"
)


# ============================================================
# JWT BEARER GÜVENLİK AYARI
# ============================================================

security = HTTPBearer()


# ============================================================
# KLASÖR YOLLARI
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
REPORT_DIR = BASE_DIR / "reports"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)


# ============================================================
# HTML TEMPLATE AYARI
# ============================================================

templates = Jinja2Templates(
    directory=str(
        BASE_DIR / "app" / "templates"
    )
)


# ============================================================
# ANA SAYFA
# ============================================================

@app.get("/")
def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )


# ============================================================
# KULLANICI KAYDI
# ============================================================

@app.post("/register")
def register(user: UserRegister):

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # KULLANICI ADI KONTROLÜ
        # ----------------------------------------------------

        existing_username = (
            db.query(User)
            .filter(
                User.username == user.username
            )
            .first()
        )

        if existing_username:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Bu kullanıcı adı zaten "
                    "kullanılıyor."
                )
            )


        # ----------------------------------------------------
        # E-POSTA KONTROLÜ
        # ----------------------------------------------------

        existing_email = (
            db.query(User)
            .filter(
                User.email == user.email
            )
            .first()
        )

        if existing_email:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Bu e-posta adresi zaten "
                    "kullanılıyor."
                )
            )


        # ----------------------------------------------------
        # ŞİFREYİ HASHLE
        # ----------------------------------------------------

        hashed_password = hash_password(
            user.password
        )


        # ----------------------------------------------------
        # YENİ KULLANICI
        # ----------------------------------------------------

        new_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password
        )

        db.add(new_user)

        db.commit()

        db.refresh(new_user)


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {

            "message":
                "Kullanıcı başarıyla oluşturuldu.",

            "user": {

                "id":
                    new_user.id,

                "username":
                    new_user.username,

                "email":
                    new_user.email,

                "created_at":
                    new_user.created_at
            }
        }


    finally:

        db.close()


# ============================================================
# KULLANICI GİRİŞİ + JWT TOKEN
# ============================================================

@app.post("/login")
def login(user: UserLogin):

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # E-POSTA İLE KULLANICI BUL
        # ----------------------------------------------------

        existing_user = (
            db.query(User)
            .filter(
                User.email == user.email
            )
            .first()
        )


        if not existing_user:

            raise HTTPException(
                status_code=401,
                detail="E-posta veya şifre hatalı."
            )


        # ----------------------------------------------------
        # ŞİFREYİ KONTROL ET
        # ----------------------------------------------------

        password_is_correct = verify_password(
            user.password,
            existing_user.hashed_password
        )


        if not password_is_correct:

            raise HTTPException(
                status_code=401,
                detail="E-posta veya şifre hatalı."
            )


        # ----------------------------------------------------
        # JWT TOKEN OLUŞTUR
        # ----------------------------------------------------

        access_token = create_access_token(
            user_id=existing_user.id,
            email=existing_user.email
        )


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {

            "message":
                "Giriş başarılı.",

            "access_token":
                access_token,

            "token_type":
                "bearer",

            "user": {

                "id":
                    existing_user.id,

                "username":
                    existing_user.username,

                "email":
                    existing_user.email
            }
        }


    finally:

        db.close()


# ============================================================
# GİRİŞ YAPAN KULLANICI
# JWT İLE KORUNAN ENDPOINT
# ============================================================

@app.get("/me")
def get_current_user(
    credentials:
        HTTPAuthorizationCredentials
        = Depends(security)
):

    # Bearer token
    token = credentials.credentials


    # JWT doğrula
    payload = verify_access_token(token)


    if payload is None:

        raise HTTPException(
            status_code=401,
            detail=(
                "Geçersiz veya süresi "
                "dolmuş token."
            )
        )


    # Token içindeki kullanıcı ID
    user_id = payload.get("sub")


    if user_id is None:

        raise HTTPException(
            status_code=401,
            detail=(
                "Token içerisinde kullanıcı "
                "bilgisi bulunamadı."
            )
        )


    db = SessionLocal()

    try:

        existing_user = (
            db.query(User)
            .filter(
                User.id == int(user_id)
            )
            .first()
        )


        if not existing_user:

            raise HTTPException(
                status_code=401,
                detail="Kullanıcı bulunamadı."
            )


        return {

            "message":
                "Token geçerli.",

            "user": {

                "id":
                    existing_user.id,

                "username":
                    existing_user.username,

                "email":
                    existing_user.email
            }
        }


    finally:

        db.close()


# ============================================================
# VİDEO ANALİZİ
# ============================================================

@app.post("/analyze")
def analyze(
    file: UploadFile = File(...)
):

    # Yüklenen video yolu
    video_path = (
        UPLOAD_DIR / file.filename
    )


    # --------------------------------------------------------
    # VİDEOYU KAYDET
    # --------------------------------------------------------

    with open(
        video_path,
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )


    # --------------------------------------------------------
    # YOLO + BYTETRACK ANALİZİ
    # --------------------------------------------------------

    report = analyze_video(
        video_path
    )


    # --------------------------------------------------------
    # ANALİZİ VERİTABANINA KAYDET
    # --------------------------------------------------------

    db = SessionLocal()

    try:

        new_analysis = Analysis(

            filename=
                file.filename,

            car_count=
                report["car"],

            bus_count=
                report["bus"],

            truck_count=
                report["truck"],

            motorcycle_count=
                report["motorcycle"],

            total_count=
                report["total"],

            vehicles_per_minute=
                report[
                    "vehicles_per_minute"
                ],

            density=
                report["density"],

            direction_up=
                report["direction_up"],

            direction_down=
                report["direction_down"]
        )


        db.add(new_analysis)

        db.commit()

        db.refresh(new_analysis)

        analysis_id = (
            new_analysis.id
        )


    finally:

        db.close()


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {

        "message":
            "Video analizi tamamlandi",

        "analysis_id":
            analysis_id,

        "report":
            report
    }


# ============================================================
# İŞLENMİŞ VİDEO
# ============================================================

@app.get("/processed-video")
def processed_video():

    video_path = (
        OUTPUT_DIR /
        "processed_video.mp4"
    )


    if not video_path.exists():

        return {
            "error":
                "İşlenmiş video henüz "
                "oluşturulmadı."
        }


    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename="processed_video.mp4"
    )


# ============================================================
# CSV RAPORU İNDİR
# ============================================================

@app.get("/download-report")
def download_report():

    csv_path = (
        REPORT_DIR /
        "analysis_report.csv"
    )


    if not csv_path.exists():

        return {
            "error":
                "CSV raporu henüz "
                "oluşturulmadı."
        }


    return FileResponse(
        path=str(csv_path),
        media_type="text/csv",
        filename="analysis_report.csv"
    )


# ============================================================
# ANALİZ GEÇMİŞİ
# YÜKLENEN VİDEOLAR
# ============================================================

@app.get("/history")
def get_history():

    db = SessionLocal()

    try:

        analyses = (

            db.query(Analysis)

            .order_by(
                Analysis.created_at.desc()
            )

            .all()
        )


        history = []


        for analysis in analyses:

            history.append({

                "id":
                    analysis.id,

                "filename":
                    analysis.filename,

                "car":
                    analysis.car_count,

                "bus":
                    analysis.bus_count,

                "truck":
                    analysis.truck_count,

                "motorcycle":
                    analysis.motorcycle_count,

                "total":
                    analysis.total_count,

                "vehicles_per_minute":
                    analysis.vehicles_per_minute,

                "density":
                    analysis.density,

                "direction_up":
                    analysis.direction_up,

                "direction_down":
                    analysis.direction_down,

                "created_at":
                    analysis.created_at
            })


        return {

            "count":
                len(history),

            "history":
                history
        }


    finally:

        db.close()


# ============================================================
# ESKİ SAATLİK TRAFİK İSTATİSTİĞİ
# YÜKLENEN VİDEOLARIN ÇALIŞTIRILMA SAATİNE GÖRE
# ============================================================

@app.get("/hourly-stats")
def hourly_stats():

    db = SessionLocal()

    try:

        analyses = (

            db.query(Analysis)

            .order_by(
                Analysis.created_at.asc()
            )

            .all()
        )


        hourly_data = {}


        for analysis in analyses:

            # Örnek:
            # 2026-09-07 15:20 -> 15:00

            hour = (
                analysis.created_at
                .strftime("%H:00")
            )


            if hour not in hourly_data:

                hourly_data[hour] = {

                    "total_vehicles":
                        0,

                    "analysis_count":
                        0
                }


            hourly_data[
                hour
            ][
                "total_vehicles"
            ] += analysis.total_count


            hourly_data[
                hour
            ][
                "analysis_count"
            ] += 1


        stats = []


        for (
            hour,
            values
        ) in hourly_data.items():

            stats.append({

                "hour":
                    hour,

                "total_vehicles":
                    values[
                        "total_vehicles"
                    ],

                "analysis_count":
                    values[
                        "analysis_count"
                    ]
            })


        return {
            "stats": stats
        }


    finally:

        db.close()


# ============================================================
# ============================================================
#
#          CANLI TRAFİK KAMERA SİSTEMİ
#
# ============================================================
# ============================================================


# ============================================================
# CANLI TRAFİK - KAMERA LİSTESİ
# ============================================================

@app.get("/live-traffic/cameras")
def live_traffic_cameras():

    db = SessionLocal()

    try:

        result = db.execute(

            text(
                """
                SELECT DISTINCT
                    camera_name

                FROM live_traffic_hourly

                ORDER BY camera_name
                """
            )
        )


        cameras = [
            row[0]
            for row in result.fetchall()
        ]


        return {

            "count":
                len(cameras),

            "cameras":
                cameras
        }


    finally:

        db.close()


# ============================================================
# CANLI TRAFİK - HAM GEÇMİŞ KAYITLARI
# ============================================================

@app.get("/live-traffic/history")
def live_traffic_history(
    camera_name: str = "07071 AKCAM SOKAK"
):

    db = SessionLocal()

    try:

        result = db.execute(

            text(
                """
                SELECT

                    id,
                    camera_name,
                    hour_start,

                    car_count,
                    motorcycle_count,
                    bus_count,
                    truck_count,

                    total_count,

                    created_at,
                    updated_at

                FROM live_traffic_hourly

                WHERE camera_name = :camera_name

                ORDER BY hour_start DESC
                """
            ),

            {
                "camera_name":
                    camera_name
            }
        )


        rows = result.mappings().all()


        history = []


        for row in rows:

            history.append({

                "id":
                    row["id"],

                "camera_name":
                    row["camera_name"],

                "hour_start":
                    row["hour_start"],

                "car":
                    row["car_count"],

                "motorcycle":
                    row[
                        "motorcycle_count"
                    ],

                "bus":
                    row["bus_count"],

                "truck":
                    row["truck_count"],

                "total":
                    row["total_count"],

                "created_at":
                    row["created_at"],

                "updated_at":
                    row["updated_at"]
            })


        return {

            "camera_name":
                camera_name,

            "record_count":
                len(history),

            "history":
                history
        }


    finally:

        db.close()


# ============================================================
# CANLI TRAFİK - SON SAATLİK KAYIT
# ============================================================

@app.get("/live-traffic/latest")
def live_traffic_latest(
    camera_name: str = "07071 AKCAM SOKAK"
):

    db = SessionLocal()

    try:

        result = db.execute(

            text(
                """
                SELECT

                    camera_name,
                    hour_start,

                    car_count,
                    motorcycle_count,
                    bus_count,
                    truck_count,

                    total_count,

                    updated_at

                FROM live_traffic_hourly

                WHERE camera_name = :camera_name

                ORDER BY hour_start DESC

                LIMIT 1
                """
            ),

            {
                "camera_name":
                    camera_name
            }
        )


        row = (
            result
            .mappings()
            .first()
        )


        if row is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Bu kamera için canlı "
                    "trafik verisi bulunamadı."
                )
            )


        return {

            "camera_name":
                row["camera_name"],

            "hour_start":
                row["hour_start"],

            "car":
                row["car_count"],

            "motorcycle":
                row[
                    "motorcycle_count"
                ],

            "bus":
                row["bus_count"],

            "truck":
                row["truck_count"],

            "total":
                row["total_count"],

            "updated_at":
                row["updated_at"]
        }


    finally:

        db.close()


# ============================================================
# CANLI TRAFİK - TARİHSEL SAATLİK PROFİL
# ============================================================

@app.get("/live-traffic/profile")
def live_traffic_profile(
    camera_name: str = "07071 AKCAM SOKAK"
):

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # AYNI SAATİN FARKLI GÜNLERDEKİ
        # ORTALAMALARINI HESAPLA
        # ----------------------------------------------------

        result = db.execute(

            text(
                """
                SELECT

                    strftime(
                        '%H',
                        hour_start
                    ) AS hour,

                    COUNT(*) AS record_count,

                    COUNT(
                        DISTINCT date(
                            hour_start
                        )
                    ) AS day_count,

                    AVG(
                        car_count
                    ) AS avg_car,

                    AVG(
                        motorcycle_count
                    ) AS avg_motorcycle,

                    AVG(
                        bus_count
                    ) AS avg_bus,

                    AVG(
                        truck_count
                    ) AS avg_truck,

                    AVG(
                        total_count
                    ) AS avg_total

                FROM live_traffic_hourly

                WHERE camera_name = :camera_name

                GROUP BY
                    strftime(
                        '%H',
                        hour_start
                    )

                ORDER BY hour
                """
            ),

            {
                "camera_name":
                    camera_name
            }
        )


        rows = (
            result
            .mappings()
            .all()
        )


        if not rows:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Bu kamera için tarihsel "
                    "trafik verisi bulunamadı."
                )
            )


        hourly_profile = []

        busiest_hour = None

        busiest_average = -1


        # ----------------------------------------------------
        # HER SAAT İÇİN ORTALAMA
        # ----------------------------------------------------

        for row in rows:

            hour = (
                row["hour"]
            )

            avg_total = float(
                row["avg_total"]
                or 0
            )


            hourly_profile.append({

                "hour":
                    f"{hour}:00",

                "record_count":
                    row[
                        "record_count"
                    ],

                "day_count":
                    row[
                        "day_count"
                    ],

                "average": {

                    "car":
                        round(
                            float(
                                row[
                                    "avg_car"
                                ]
                                or 0
                            ),
                            2
                        ),

                    "motorcycle":
                        round(
                            float(
                                row[
                                    "avg_motorcycle"
                                ]
                                or 0
                            ),
                            2
                        ),

                    "bus":
                        round(
                            float(
                                row[
                                    "avg_bus"
                                ]
                                or 0
                            ),
                            2
                        ),

                    "truck":
                        round(
                            float(
                                row[
                                    "avg_truck"
                                ]
                                or 0
                            ),
                            2
                        ),

                    "total":
                        round(
                            avg_total,
                            2
                        )
                }
            })


            # ------------------------------------------------
            # EN YOĞUN SAATİ BUL
            # ------------------------------------------------

            if (
                avg_total
                >
                busiest_average
            ):

                busiest_average = (
                    avg_total
                )

                busiest_hour = (
                    f"{hour}:00"
                )


        # ----------------------------------------------------
        # KAÇ FARKLI GÜN VERİSİ VAR?
        # ----------------------------------------------------

        day_result = db.execute(

            text(
                """
                SELECT
                    COUNT(
                        DISTINCT date(
                            hour_start
                        )
                    )

                FROM live_traffic_hourly

                WHERE camera_name = :camera_name
                """
            ),

            {
                "camera_name":
                    camera_name
            }
        )


        total_days = (
            day_result.scalar()
            or 0
        )


        # ----------------------------------------------------
        # ANALİZ YORUMU
        # ----------------------------------------------------

        if total_days >= 3:

            conclusion = (

                f"Geçmiş trafik kayıtlarına göre "
                f"bu yol genellikle "
                f"{busiest_hour} civarında "
                f"daha yoğun gözlemlenmektedir."
            )

        else:

            conclusion = (

                f"Şu ana kadar en yüksek ortalama "
                f"{busiest_hour} saatinde "
                f"gözlemlenmiştir. Ancak tipik "
                f"trafik profili çıkarabilmek için "
                f"daha fazla günlük veri "
                f"toplanmalıdır."
            )


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {

            "camera_name":
                camera_name,

            "total_observation_days":
                total_days,

            "busiest_hour":
                busiest_hour,

            "busiest_average":
                round(
                    busiest_average,
                    2
                ),

            "conclusion":
                conclusion,

            "hourly_profile":
                hourly_profile
        }


    finally:

        db.close()


# ============================================================
# CANLI TRAFİK - ÖZET
# ============================================================

@app.get("/live-traffic/summary")
def live_traffic_summary(
    camera_name: str = "07071 AKCAM SOKAK"
):

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # TOPLAM KAYIT VE GÜN
        # ----------------------------------------------------

        general_result = db.execute(

            text(
                """
                SELECT

                    COUNT(*) AS record_count,

                    COUNT(
                        DISTINCT date(
                            hour_start
                        )
                    ) AS day_count,

                    SUM(
                        car_count
                    ) AS car_total,

                    SUM(
                        motorcycle_count
                    ) AS motorcycle_total,

                    SUM(
                        bus_count
                    ) AS bus_total,

                    SUM(
                        truck_count
                    ) AS truck_total,

                    SUM(
                        total_count
                    ) AS vehicle_total

                FROM live_traffic_hourly

                WHERE camera_name = :camera_name
                """
            ),

            {
                "camera_name":
                    camera_name
            }
        )


        data = (
            general_result
            .mappings()
            .first()
        )


        if (
            data is None
            or
            data[
                "record_count"
            ] == 0
        ):

            raise HTTPException(
                status_code=404,
                detail=(
                    "Bu kamera için trafik "
                    "verisi bulunamadı."
                )
            )


        return {

            "camera_name":
                camera_name,

            "record_count":
                data[
                    "record_count"
                ],

            "observation_days":
                data[
                    "day_count"
                ],

            "vehicle_totals": {

                "car":
                    data[
                        "car_total"
                    ] or 0,

                "motorcycle":
                    data[
                        "motorcycle_total"
                    ] or 0,

                "bus":
                    data[
                        "bus_total"
                    ] or 0,

                "truck":
                    data[
                        "truck_total"
                    ] or 0,

                "total":
                    data[
                        "vehicle_total"
                    ] or 0
            }
        }


    finally:

        db.close()