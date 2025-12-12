import streamlit as st
from streamlit_folium import st_folium
import folium
import requests
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime
from PIL import Image
import base64
import json
import os

# ===============================
# PAGE CONFIG (WAJIB PALING ATAS)
# ===============================
st.set_page_config(
    page_title="Cek Aman Pembakaran Jerami",
    layout="centered",
)

# ===============================
# BACKGROUND IMAGE HELPER
# ===============================
def get_base64_image(image_path: str):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return None

bg_image = get_base64_image("background_sawah.png")

# ===============================
# CUSTOM CSS
# ===============================
if bg_image:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{bg_image}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        .stApp::before {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(255, 255, 255, 0.75);
            z-index: -1;
        }}
        .weather-info {{
            background-color: rgba(255, 255, 255, 0.98);
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.15);
            margin: 1rem 0;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(200, 200, 200, 0.3);
        }}
        .stMarkdown ul li {{
            color: #000000 !important;
            font-weight: 500 !important;
            background-color: rgba(255, 255, 255, 0.95);
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 4px solid #ff4b4b;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <style>
        .weather-info {
            background-color: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 1rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ===============================
# HEADER (ICON + TITLE)
# ===============================
col1, col2 = st.columns([0.22, 0.78])

with col1:
    try:
        gambarIkon = Image.open("iconbakarjerami.png")
        st.image(gambarIkon, width=120)
    except Exception:
        st.write("")

with col2:
    st.markdown(
        """
        <h1 style='text-align:left; margin-top: 12px; color:#ff4b4b;'>
            PERIKSA KEAMANAN PEMBAKARAN JERAMI
        </h1>
        """,
        unsafe_allow_html=True
    )

# ===============================
# DEFAULT LOCATION
# ===============================
default_location = [-8.65, 115.2167]  # Bali

if "location" not in st.session_state:
    st.session_state["location"] = default_location
if "zoom_level" not in st.session_state:
    st.session_state["zoom_level"] = 10

# Bandara I Gusti Ngurah Rai
bandara_lat = -8.7482
bandara_lon = 115.1670

# ===============================
# FUNGSI BANTUAN
# ===============================
def arah_angin(degrees):
    arah = ["Utara", "Timur Laut", "Timur", "Tenggara", "Selatan", "Barat Daya", "Barat", "Barat Laut"]
    if degrees is None:
        return "Tidak tersedia"
    index = int((degrees + 22.5) // 45) % 8
    return arah[index]

def hitung_jarak(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def aman_di_rentang(nilai, low, high, include_low=True, include_high=True):
    if nilai is None:
        return False
    if include_low and include_high:
        return low <= nilai <= high
    if include_low and not include_high:
        return low <= nilai < high
    if not include_low and include_high:
        return low < nilai <= high
    return low < nilai < high

def ambil_index_saat_ini(current, hourly):
    hourly_times = hourly.get("time", [])
    current_time_str = current.get("time")
    if not current_time_str or not hourly_times:
        return None
    try:
        return hourly_times.index(current_time_str)
    except ValueError:
        return None

def ambil_dari_list(lst, idx, default=None):
    if lst is None or idx is None:
        return default
    try:
        return lst[idx]
    except (TypeError, IndexError):
        return default

# ===============================
# MAP VIEW
# ===============================
m = folium.Map(
    location=st.session_state["location"],
    zoom_start=st.session_state["zoom_level"],
)

folium.Marker(
    location=st.session_state["location"],
    tooltip="Lokasi Terpilih",
    icon=folium.Icon(color="red"),
).add_to(m)

st.markdown("🗺️ **Klik pada peta untuk memilih lokasi**")
map_data = st_folium(m, height=500, width="100%")

if map_data:
    if "zoom" in map_data:
        st.session_state["zoom_level"] = map_data["zoom"]

    if map_data.get("last_clicked"):
        lat = map_data["last_clicked"]["lat"]
        lon = map_data["last_clicked"]["lng"]
        st.session_state["location"] = [lat, lon]
        st.success(f"Koordinat dipilih: Latitude {lat:.5f}, Longitude {lon:.5f}")

lat, lon = st.session_state["location"]

# ===============================
# OPEN-METEO FETCH (CACHE + BUTTON)
# ===============================
CACHE_FILE = "weather_cache.json"

def save_cache(lat, lon, data):
    """Simpan data cuaca ke file lokal dengan timestamp"""
    try:
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "latitude": lat,
            "longitude": lon,
            "data": data
        }
        with open(CACHE_FILE, "w") as f:
            json.dump(cache_data, f)
    except Exception as e:
        st.warning(f"Gagal menyimpan cache: {e}")

def load_cache(lat, lon, max_age_minutes=60):
    """Load data dari cache jika masih valid (dalam rentang koordinat dan waktu)"""
    try:
        if not os.path.exists(CACHE_FILE):
            return None
        
        with open(CACHE_FILE, "r") as f:
            cache_data = json.load(f)
        
        # Cek apakah cache masih fresh (< max_age_minutes)
        cache_time = datetime.fromisoformat(cache_data["timestamp"])
        age_minutes = (datetime.now() - cache_time).total_seconds() / 60
        
        # Cek apakah koordinat sama (dengan toleransi 0.01 derajat ~ 1km)
        lat_diff = abs(cache_data["latitude"] - lat)
        lon_diff = abs(cache_data["longitude"] - lon)
        
        if age_minutes <= max_age_minutes and lat_diff < 0.01 and lon_diff < 0.01:
            return cache_data
        
        return None
    except Exception:
        return None

@st.cache_data(ttl=300)
def fetch_open_meteo(params: dict):
    """Fetch data dari OpenMeteo API dengan caching"""
    r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=15)
    r.raise_for_status()
    return r.json()

params = {
    "latitude": lat,
    "longitude": lon,
    "hourly": "temperature_2m,relative_humidity_2m,windspeed_10m,winddirection_10m,windgusts_10m,boundary_layer_height",
    "current_weather": "true",
    "timezone": "auto",
}

st.markdown("---")
if not st.button("🌦️ Ambil Data Cuaca"):
    st.info("Klik tombol **Ambil Data Cuaca** untuk memuat data cuaca & hasil analisis.")
    st.stop()

# Coba load dari cache terlebih dahulu
cached = load_cache(lat, lon, max_age_minutes=60)
data = None
data_source = None

with st.spinner("Mengambil data cuaca dari Open-Meteo..."):
    try:
        # Coba ambil data fresh dari API
        data = fetch_open_meteo(params)
        data_source = "fresh"
        # Simpan ke cache lokal
        save_cache(lat, lon, data)
        st.success("✅ Data cuaca berhasil diambil dari API")
        
    except requests.HTTPError as e:
        # Jika rate limit (429), gunakan cache
        if hasattr(e, "response") and e.response is not None and e.response.status_code == 429:
            if cached:
                st.warning("⚠️ Batas permintaan API tercapai. Menggunakan data cache terakhir.")
                cache_age = (datetime.now() - datetime.fromisoformat(cached["timestamp"])).total_seconds() / 60
                st.info(f"📦 Data cache dari {int(cache_age)} menit yang lalu (koordinat: {cached['latitude']:.4f}, {cached['longitude']:.4f})")
                data = cached["data"]
                data_source = "cached"
            else:
                st.error("❌ Batas permintaan API tercapai dan tidak ada data cache tersedia.")
                st.info("💡 **Solusi:** Tunggu beberapa saat atau coba lagi besok. OpenMeteo gratis memiliki limit harian.")
                if hasattr(e, "response"):
                    try:
                        st.json(e.response.json())
                    except Exception:
                        pass
                st.stop()
        else:
            st.error(f"Gagal mengambil data cuaca (HTTPError): {e}")
            if hasattr(e, "response") and e.response is not None:
                st.write("Status:", e.response.status_code)
                try:
                    st.write(e.response.json())
                except Exception:
                    st.write(e.response.text[:500])
            st.stop()
            
    except Exception as e:
        # Untuk error lain, coba gunakan cache jika ada
        if cached:
            st.warning(f"⚠️ Gagal mengambil data baru: {e}")
            cache_age = (datetime.now() - datetime.fromisoformat(cached["timestamp"])).total_seconds() / 60
            st.info(f"📦 Menggunakan data cache dari {int(cache_age)} menit yang lalu")
            data = cached["data"]
            data_source = "cached"
        else:
            st.error(f"Gagal mengambil data cuaca: {e}")
            st.stop()

current = data.get("current_weather", {})
hourly = data.get("hourly", {})

# ===============================
# AMBIL DATA CUACA
# ===============================
idx_now = ambil_index_saat_ini(current, hourly)

temp = current.get("temperature")
wind = current.get("windspeed")
wind_dir = current.get("winddirection")

humidity_list = hourly.get("relative_humidity_2m", [])
pbl_list = hourly.get("boundary_layer_height", [])
wd_hourly = hourly.get("winddirection_10m", [])

humidity = ambil_dari_list(humidity_list, idx_now)
pbl = ambil_dari_list(pbl_list, idx_now)

idx_12h = (idx_now - 12) if (idx_now is not None) else None
wind_dir_12h = ambil_dari_list(wd_hourly, idx_12h) if (idx_12h is not None and idx_12h >= 0) else None

arah_wd = arah_angin(wind_dir)

# Ventilation Rate = PBL * WindSpeed (hindari cek "wind and pbl")
vr = (pbl * wind) if (pbl is not None and wind is not None) else None

jarak_bandara = hitung_jarak(lat, lon, bandara_lat, bandara_lon)

# Jam lokal dari API (timezone=auto)
jam_desimal = None
try:
    t = current.get("time")
    if t:
        dt = datetime.fromisoformat(t)  # "YYYY-MM-DDTHH:MM"
        jam_desimal = dt.hour + dt.minute / 60.0
        now_str = dt.strftime("%H:%M")
    else:
        now_str = datetime.now().strftime("%H:%M")
except Exception:
    now_str = datetime.now().strftime("%H:%M")

perubahan_wd = abs(wind_dir - wind_dir_12h) if (wind_dir is not None and wind_dir_12h is not None) else None

# ===============================
# TAMPILKAN INFO CUACA
# ===============================
st.markdown("<div class='weather-info'>", unsafe_allow_html=True)

# Tampilkan badge sumber data
if data_source == "fresh":
    st.markdown("### 🌦️ Info Cuaca Lengkap 🟢 _Live Data_")
elif data_source == "cached":
    st.markdown("### 🌦️ Info Cuaca Lengkap 🟡 _Data Cache_")
else:
    st.markdown("### 🌦️ Info Cuaca Lengkap")

colA, colB = st.columns(2)

with colA:
    st.write(f"**Suhu (T):** {temp}°C" if temp is not None else "**Suhu (T):** Tidak tersedia")
    st.write(f"**Kelembaban (RH):** {humidity}%" if humidity is not None else "**Kelembaban (RH):** Tidak tersedia")
    st.write(f"**Kecepatan Angin (WS):** {wind} kph" if wind is not None else "**Kecepatan Angin (WS):** Tidak tersedia")
    st.write(f"**Boundary Layer Height (PBL):** {pbl} m" if pbl is not None else "**Boundary Layer Height (PBL):** Tidak tersedia")
    st.write(f"**Ventilation Rate (VR):** {vr:.2f} m²/s" if vr is not None else "**Ventilation Rate (VR):** Tidak tersedia")

with colB:
    st.write(f"**Arah Angin (WD):** {wind_dir}° ({arah_wd})" if wind_dir is not None else "**Arah Angin (WD):** Tidak tersedia")
    st.write(f"**WD 12 jam lalu:** {wind_dir_12h}°" if wind_dir_12h is not None else "**WD 12 jam lalu:** Tidak tersedia")
    st.write(f"**Perubahan WD:** {perubahan_wd:.1f}°" if perubahan_wd is not None else "**Perubahan WD:** Tidak dapat dihitung")
    st.write(f"**Jarak ke bandara:** {jarak_bandara:.2f} km")
    st.write(f"**Waktu Lokal:** {now_str}")

st.write(f"**Lokasi Terpilih:** {lat:.5f}, {lon:.5f}")
st.markdown("</div>", unsafe_allow_html=True)

# ===============================
# LOGIKA KELAYAKAN (TANPA SKOR)
# ===============================
alasan = []
aman = True

# 1. RH 10–80%
if not aman_di_rentang(humidity, 10, 80, include_low=True, include_high=True):
    aman = False
    alasan.append(f"Kelembaban {humidity}% di luar rentang aman 10–80%." if humidity is not None else "Data kelembaban tidak tersedia.")

# 2. WS 6–40 kph
if not aman_di_rentang(wind, 6, 40, include_low=True, include_high=True):
    aman = False
    alasan.append(f"Kecepatan angin {wind} kph di luar rentang aman 6–40 kph." if wind is not None else "Data kecepatan angin tidak tersedia.")

# 3. ΔWD > 30°
if perubahan_wd is not None and perubahan_wd > 30:
    aman = False
    alasan.append(f"Arah angin berubah signifikan (ΔWD {perubahan_wd:.1f}° > 30°) dalam 12 jam terakhir.")
elif perubahan_wd is None:
    alasan.append("Perubahan arah angin 12 jam terakhir tidak dapat dihitung.")

# 4. Suhu -1 – 43°C
if not aman_di_rentang(temp, -1, 43, include_low=True, include_high=True):
    aman = False
    alasan.append(f"Suhu {temp}°C di luar rentang aman -1 sampai 43°C." if temp is not None else "Data suhu tidak tersedia.")

# 5. Jarak bandara > 2 km
if jarak_bandara < 2:
    aman = False
    alasan.append(f"Jarak ke bandara hanya {jarak_bandara:.2f} km (harus > 2 km).")

# 6. VR 3580–44720
if vr is None or not aman_di_rentang(vr, 3580, 44720, include_low=True, include_high=True):
    aman = False
    alasan.append(f"Ventilation Rate {vr:.2f} m²/s di luar rentang aman 3580–44720 m²/s." if vr is not None else "Ventilation Rate tidak tersedia.")

# 7. Waktu 09.30 – 18.00
if jam_desimal is None or not aman_di_rentang(jam_desimal, 9.5, 18, include_low=True, include_high=True):
    aman = False
    alasan.append(f"Waktu sekarang {now_str} di luar rentang aman 09.30 – 18.00.")

# ===============================
# STATUS + REKOMENDASI
# ===============================
st.markdown("---")
if aman:
    st.success("### ✅ CUACA AMAN UNTUK PEMBAKARAN")

    if wind is not None and 3 <= wind <= 25:
        st.markdown("<div class='weather-info'>", unsafe_allow_html=True)
        st.markdown("### TEKNIK PEMBAKARAN")
        st.markdown("Teknik pembakaran yang direkomendasikan adalah **Headfire** (api bergerak searah angin).")
        st.markdown("</div>", unsafe_allow_html=True)

    elif wind is not None and 27 <= wind <= 40:
        st.markdown("<div class='weather-info'>", unsafe_allow_html=True)
        st.markdown("### TEKNIK PEMBAKARAN")
        st.markdown("Rekomendasi: **Flankfire** (tegak lurus angin) atau **Backfire** (melawan arah angin).")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='weather-info'>", unsafe_allow_html=True)
    st.markdown("### REKOMENDASI PEMBUATAN FIREBREAK")
    st.markdown(
        """
        Pembuatan **Firebreak** harus dilakukan sebelum pembakaran jerami.

        Firebreak dapat berupa:
        1. Garis kendali / garis bajak (mencangkul atau membajak).
        2. Natural breaks: sungai, selokan, jalan tanpa rumput.
        3. Jalur bakar / jalur basah:
           - Jalur bakar: teknik backfire atau flankfire.
           - Jalur basah: membasahi batas plot pembakaran.
        """
    )
    st.markdown("</div>", unsafe_allow_html=True)

else:
    st.error("### ⚠️ PEMBAKARAN TIDAK AMAN")
    st.write("**Alasan:**")
    for a in alasan:
        st.write(f"- {a}")
