from pathlib import Path
import os

# Klasörler
BASE_DIR = Path(__file__).resolve().parent.parent
SIM_DIR = BASE_DIR / "simulator"
SIM_DIR.mkdir(exist_ok=True)

# Anahtarlar (ENV → fallback mevcut değer)
HERE_API_KEY = os.getenv("HERE_API_KEY", "SVdlVkMWRWUtIVXzGNQ3Y5D2IQJ1OA78n9J0CpZ8LKU")
ORS_API_KEY  = os.getenv("ORS_API_KEY",  "5b3ce3597851110001cf6248efed8bc0e38542c58db8d67cdb56008f")

# C++ fizik motoru konumu ve kullanım bayrağı
PHYSICS_ENGINE_PATH = Path(os.getenv(
    "PHYSICS_ENGINE_PATH",
    str(BASE_DIR.parent / "cpp" / "build" / "physics_engine"),
))
USE_CPP_PHYSICS = os.getenv("USE_CPP_PHYSICS", "1") not in ("0", "false", "False")

# Servis URL'leri
OPEN_METEO_BASE = "https://api.open-meteo.com/v1/elevation"
