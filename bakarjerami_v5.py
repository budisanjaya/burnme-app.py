import streamlit as st
from streamlit_folium import st_folium
import folium
import requests
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime
from PIL import Image
import base64


# gambarIkon = Image.open('iconbakarjerami.png')
# st.set_page_config(
#     page_title="Cek Aman Pembakaran Jerami",
#     layout="centered"
# )


gambarIkon = Image.open("iconbakarjerami.png")


col1, col2 = st.columns([0.2, 0.8])  

with col1:
    st.image(gambarIkon, width=150)

with col2:
    st.markdown(
        """
        <h1 style='text-align:left; margin-top: 15px;'>
            PERIKSA KEAMANAN PEMBAKARAN JERAMI
        </h1>
        """,
        unsafe_allow_html=True
    )


# ===============================
#     FUNGSI BACKGROUND IMAGE
# ===============================
def get_base64_image(image_path):
    """Mengkonversi gambar ke base64 untuk digunakan di CSS"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

# Encode background image
bg_image = get_base64_image("background_sawah.png")

# ===============================
#           CUSTOM CSS
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
        .main {{
            padding: 2rem;
            border-radius: 10px;
        }}
        .stButton button {{
            width: 100%;
            border-radius: 5px;
            background-color: #ff4b4b;
        }}
        h1 {{
            color: #ff4b4b;
            text-align: center;
            padding: 1rem;
            border-bottom: 2px solid #ff4b4b;
            margin-bottom: 2rem;
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
        /* Membuat teks lebih gelap dan jelas */
        .weather-info p, .weather-info div {{
            color: #1a1a1a !important;
            font-weight: 500;
        }}
        /* Styling untuk error/warning messages */
        .stAlert {{
            background-color: rgba(255, 255, 255, 0.98) !important;
            border: 2px solid !important;
        }}
        /* Membuat teks di error box lebih jelas */
        .stAlert p, .stAlert div, .stAlert li {{
            color: #1a1a1a !important;
            font-weight: 600 !important;
        }}
        /* Styling khusus untuk list alasan */
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
    # Fallback CSS jika gambar tidak ditemukan
    st.markdown(
        """
        <style>
        .main {{
            padding: 2rem;
            border-radius: 10px;
        }}
        .stButton button {{
            width: 100%;
            border-radius: 5px;
            background-color: #ff4b4b;
        }}
        h1 {{
            color: #ff4b4b;
            text-align: center;
            padding: 1rem;
            border-bottom: 2px solid #ff4b4b;
            margin-bottom: 2rem;
        }}
        .weather-info {{
            background-color: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 1rem 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )



# Lokasi default: Bali
default_location = [-8.65, 115.2167]

if "location" not in st.session_state:
    st.session_state["location"] = default_location
if "zoom_level" not in st.session_state:
    st.session_state["zoom_level"] = 10


# ===============================
#       FUNGSI BANTUAN
# ===============================

def arah_angin(degrees):
    """Mengubah derajat arah angin menjadi teks (Utara, Timur, dst)."""
    arah = [
        "Utara",
        "Timur Laut",
        "Timur",
        "Tenggara",
        "Selatan",
        "Barat Daya",
        "Barat",
        "Barat Laut",
    ]
    if degrees is None:
        return "Tidak tersedia"
    index = int((degrees + 22.5) // 45) % 8
    return arah[index]


def hitung_jarak(lat1, lon1, lat2, lon2):
    """Haversine distance - jarak km antara dua koordinat."""
    R = 6371  # km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def aman_di_rentang(nilai, low, high, include_low=True, include_high=True):
    """Helper untuk cek apakah nilai masih di dalam rentang."""
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
    """Cari index waktu current_weather di deret waktu hourly."""
    hourly_times = hourly.get("time", [])
    current_time_str = current.get("time")
    if not current_time_str or not hourly_times:
        return None
    try:
        return hourly_times.index(current_time_str)
    except ValueError:
        return None


def ambil_dari_list(lst, idx, default=None):
    """Aman ambil data dari list berdasarkan index."""
    if lst is None:
        return default
    try:
        return lst[idx]
    except (TypeError, IndexError):
        return default


# Koordinat Bandara I Gusti Ngurah Rai
bandara_lat = -8.7482
bandara_lon = 115.1670


# ===============================
#            MAP VIEW
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

# Update zoom & lokasi berdasarkan interaksi peta
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
#      REQUEST CUACA API
# ===============================

url = (
    "https://api.open-meteo.com/v1/forecast?"
    f"latitude={lat}&longitude={lon}"
    "&hourly=temperature_2m,relative_humidity_2m,windspeed_10m,"
    "winddirection_10m,windgusts_10m,boundary_layer_height"
    "&current_weather=true"
)

try:
    response = requests.get(url, timeout=10)
except requests.RequestException:
    st.error("Tidak dapat menghubungi server cuaca.")
    st.stop()

if response.status_code != 200:
    st.error("Gagal mengambil data cuaca dari server.")
    st.stop()

data = response.json()

current = data.get("current_weather", {})
hourly = data.get("hourly", {})

# Cari index data current di deret hourly
idx_now = ambil_index_saat_ini(current, hourly)

# Ambil data dasar
temp = current.get("temperature")
wind = current.get("windspeed")
wind_dir = current.get("winddirection")

humidity_list = hourly.get("relative_humidity_2m", [])
pbl_list = hourly.get("boundary_layer_height", [])
wd_hourly = hourly.get("winddirection_10m", [])

if idx_now is not None:
    humidity = ambil_dari_list(humidity_list, idx_now)
    pbl = ambil_dari_list(pbl_list, idx_now)
    # 12 jam sebelum: mundur 12 jam dari index saat ini
    idx_12h = idx_now - 12
    wind_dir_12h = ambil_dari_list(wd_hourly, idx_12h) if idx_12h >= 0 else None
else:
    # fallback: ambil index pertama / ke-12 seperti sebelumnya
    humidity = ambil_dari_list(humidity_list, 0)
    pbl = ambil_dari_list(pbl_list, 0)
    wind_dir_12h = ambil_dari_list(wd_hourly, 12)

arah_wd = arah_angin(wind_dir)

# Ventilation Index = PBL * WindSpeed
if pbl is not None and wind is not None:
    vi = pbl * wind
else:
    vi = None

# Hitung jarak ke bandara
jarak_bandara = hitung_jarak(lat, lon, bandara_lat, bandara_lon)

now = datetime.now()
jam_desimal = now.hour + now.minute / 60.0

# Hitung perubahan arah angin
perubahan_wd = None
if wind_dir is not None and wind_dir_12h is not None:
    perubahan_wd = abs(wind_dir - wind_dir_12h)


# ===============================
#       TAMPILKAN INFO CUACA
# ===============================

st.markdown("<div class='weather-info'>", unsafe_allow_html=True)
st.markdown("### 🌦️ Info Cuaca Lengkap")

col1, col2 = st.columns(2)

with col1:
    st.write(f"**Suhu (T):** {temp}°C" if temp is not None else "**Suhu (T):** Tidak tersedia")
    st.write(
        f"**Kelembaban (RH):** {humidity}%"
        if humidity is not None
        else "**Kelembaban (RH):** Tidak tersedia"
    )
    st.write(
        f"**Kecepatan Angin (WS):** {wind} kph"
        if wind is not None
        else "**Kecepatan Angin (WS):** Tidak tersedia"
    )
    st.write(
        f"**Boundary Layer Height (PBL):** {pbl} m"
        if pbl is not None
        else "**Boundary Layer Height (PBL):** Tidak tersedia"
    )
    if vi is not None:
        st.write(f"**Ventilation Index (VI):** {vi:.2f} m²/s")
    else:
        st.write("**Ventilation Index (VI):** Tidak tersedia")

with col2:
    st.write(
        f"**Arah Angin (WD):** {wind_dir}° ({arah_wd})"
        if wind_dir is not None
        else "**Arah Angin (WD):** Tidak tersedia"
    )
    if wind_dir_12h is not None:
        st.write(f"**WD 12 jam lalu:** {wind_dir_12h}°")
    else:
        st.write("**WD 12 jam lalu:** Tidak tersedia")

    if perubahan_wd is not None:
        st.write(f"**Perubahan WD:** {perubahan_wd:.1f}°")
    else:
        st.write("**Perubahan WD:** Tidak dapat dihitung")

    st.write(f"**Jarak ke bandara:** {jarak_bandara:.2f} km")
    st.write(f"**Waktu Sekarang:** {now.strftime('%H:%M')}")

st.write(f"**Lokasi Terpilih:** {lat:.5f}, {lon:.5f}")
st.markdown("</div>", unsafe_allow_html=True)




# ===============================
#      LOGIKA KELAYAKAN
# ===============================

alasan = []
aman = True

# 1. Kelembaban: 10–80% (inklusif)
if not aman_di_rentang(humidity, 10, 80, include_low=True, include_high=True):
    aman = False
    alasan.append(
        f"Kelembaban {humidity}% di luar rentang aman 10–80%."
        if humidity is not None
        else "Data kelembaban tidak tersedia."
    )

# 2. Kecepatan angin: 6–40 kph (inklusif)
if not aman_di_rentang(wind, 6, 40, include_low=True, include_high=True):
    aman = False
    alasan.append(
        f"Kecepatan angin {wind} kph di luar rentang aman 6–40 kph."
        if wind is not None
        else "Data kecepatan angin tidak tersedia."
    )
    


# 3. Perubahan arah angin > 30°
if perubahan_wd is not None and perubahan_wd > 30:
    aman = False
    alasan.append(
        f"Arah angin berubah signifikan (ΔWD {perubahan_wd:.1f}° > 30°) dalam 12 jam terakhir."
    )
elif perubahan_wd is None:
    # Tidak langsung menjadikan tidak aman, tapi informasikan
    alasan.append("Perubahan arah angin 12 jam terakhir tidak dapat dihitung.")

# 4. Suhu: -1 sampai 43°C (inklusif)
if not aman_di_rentang(temp, -1, 43, include_low=True, include_high=True):
    aman = False
    alasan.append(
        f"Suhu {temp}°C di luar rentang aman -1 sampai 43°C."
        if temp is not None
        else "Data suhu tidak tersedia."
    )

# 5. Jarak ke bandara > 2 km
if jarak_bandara < 2:
    aman = False
    alasan.append(
        f"Jarak ke bandara hanya {jarak_bandara:.2f} km (harus > 2 km)."
    )

# 6. Ventilation Index 3580–44720 m²/s
if vi is None or not aman_di_rentang(vi, 3580, 44720, include_low=True, include_high=True):
    aman = False
    if vi is not None:
        alasan.append(
            f"Ventilation Index {vi:.2f} m²/s di luar rentang aman 3580–44720 m²/s."
        )
    else:
        alasan.append("Ventilation Index tidak tersedia.")

# 7. Waktu pembakaran: 09.30 – 18.00 (inklusif)
if not aman_di_rentang(jam_desimal, 9.5, 18, include_low=True, include_high=True):
    aman = False
    alasan.append(
        f"Waktu sekarang {now.strftime('%H:%M')} di luar rentang aman 09.30 – 18.00."
    )


# ===============================
#            STATUS
# ===============================

if aman:
    st.success("### ✅ CUACA AMAN UNTUK PEMBAKARAN")
    if wind >= 3 and wind <=25 :
        st.markdown("<div class='weather-info'>", unsafe_allow_html=True)
        st.markdown("### TEKNIK PEMBAKARAN")
        st.markdown("""
                Teknik pembakaran yang direkomendasikan adalah Headfire
                (Api bergerak searah angin)
                 
                    """)
        st.markdown("</div>", unsafe_allow_html=True)
       

        
    elif wind >= 27 and wind <=40:
        st.markdown("<div class='weather-info'>", unsafe_allow_html=True)
        st.markdown("### REKOMENDASI PEMBUATAN FIREBREAK")
        st.markdown("""
                Teknik pembakaran yang direkomendasikan adalah Flankfire (Api bergerak tegak lurus arah angin
                atau Backfire (Api bergerak melawan arah angin)
                    """)
        st.markdown("</div>", unsafe_allow_html=True)
        


    st.markdown("<div class='weather-info'>", unsafe_allow_html=True)
    st.markdown("### REKOMENDASI PEMBUATAN FIREBREAK")
    st.markdown("""
    Pembuatan Firebreak harus dilakukan sebelum pembakaran jerami

    Firebreak dapat berupa :
    1. Garis kendali/Garis bajak yang dibuat dengan mencangkul atau bajak.
    2. Natural breaks seperti sungai, selokan, jalan tanpa rumput.
    3. Jalur bakar atau jalur basah. Jalur bakar dilakukan dengan teknik backfire atau flankfire, 
    jalur basah dilakukan dengan membasahi batas batas plot pembakaran            
                """)
    st.markdown("</div>", unsafe_allow_html=True)

    
else:
    st.error("### ⚠️ PEMBAKARAN TIDAK AMAN")
    st.write("**Alasan:**")
    for a in alasan:
        st.write(f"- {a}")
