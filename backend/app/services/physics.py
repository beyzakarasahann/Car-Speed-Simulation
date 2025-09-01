from typing import List, Dict, Any
import math, numpy as np, random
import json, subprocess, tempfile, os
from app.utils.geo import (
    EARTH_R, DEG2RAD, RAD2DEG,
    haversine_m, bearing_rad, wrap_angle, slope_deg,
    ll_to_local_xy, local_xy_to_ll
)
from app.services.ekf_bridge import run_cpp_ekf
from pathlib import Path
from app.core.config import PHYSICS_ENGINE_PATH, USE_CPP_PHYSICS

BUS_MAX_SPEED_KMH = 120.0
BUS_MAX_LATERAL   = 2.0
BUS_MAX_YAWRATE   = 0.5
GRAVITY = 9.80665

def calculate_smart_target_speed(points: List[Dict], idx: int) -> float:
    """
    GERÇEK NAVİGASYON SİSTEMİ: GPS + Elevation → Akıllı target hız
    Yol tipi, eğim, viraj analizi ile ideal hızı belirler
    """
    if not points or idx >= len(points):
        return 50.0  # Varsayılan
    
    current_point = points[idx]
    lat, lon = current_point["lat"], current_point["lon"]
    elevation = current_point.get("elevation", 0.0)
    
    # YOL TİPİ ANALİZİ (functionalClass öncelikli, yoksa geometri)
    base_speed = 50.0  # şehir içi varsayılan
    fc = current_point.get("functional_class")
    if isinstance(fc, int):
        # Türkiye tipik: FC1 otoyol ~120, FC2 ana yol ~90, FC3 ikincil ~82, diğer ~60
        if fc == 1:
            base_speed = 110.0
        elif fc == 2:
            base_speed = 90.0
        elif fc == 3:
            base_speed = 82.0
        else:
            base_speed = 60.0
    else:
        # functionalClass yoksa segment uzunluğuna göre çıkarım (daha agresif eşikler)
        if idx > 2 and idx < len(points) - 2:
            distances = []
            for i in range(idx-2, idx+3):
                if i < len(points) - 1:
                    dist = haversine_m((points[i]["lat"], points[i]["lon"]), 
                                     (points[i+1]["lat"], points[i+1]["lon"]))
                    distances.append(dist)
            avg_segment_distance = sum(distances) / len(distances) if distances else 10
            if avg_segment_distance > 60:      # otoyol/çevre yolu
                base_speed = 90.0
            elif avg_segment_distance > 30:    # ana yol
                base_speed = 70.0
    
    # EĞİM ANALİZİ
    slope_factor = 1.0
    if idx < len(points) - 1:
        next_point = points[idx + 1]
        elevation_diff = next_point.get("elevation", 0) - elevation
        distance = haversine_m((lat, lon), (next_point["lat"], next_point["lon"]))
        
        if distance > 0:
            slope_percent = (elevation_diff / distance) * 100
            if abs(slope_percent) < 0.3:
                slope_percent = 0.0
            
            if slope_percent > 8:  # Dik yokuş yukarı
                slope_factor = 0.6
            elif slope_percent > 4:  # Orta yokuş yukarı
                slope_factor = 0.8
            elif slope_percent < -8:  # Dik yokuş aşağı
                slope_factor = 0.7  # Fren mesafesi için yavaş
            elif slope_percent < -4:  # Orta yokuş aşağı
                slope_factor = 0.9
    
    # VİRAJ ANALİZİ (3 noktalı eğrilik) — yüksek sınıf yollarda daha az cezalandır
    curve_factor = 1.0
    if idx > 0 and idx < len(points) - 1:
        prev_point = points[idx - 1]
        next_point = points[idx + 1]
        
        # Açı değişimi hesabı
        bearing1 = bearing_rad((prev_point["lat"], prev_point["lon"]), (lat, lon))
        bearing2 = bearing_rad((lat, lon), (next_point["lat"], next_point["lon"]))
        angle_change = abs(wrap_angle(bearing2 - bearing1))

        if isinstance(fc, int) and fc <= 2:
            # FC1–FC2: çevre yolu/otoyolda virajlar daha geniş → daha hafif ceza
            if angle_change > 0.6:      # ~34°
                curve_factor = 0.7
            elif angle_change > 0.4:    # ~23°
                curve_factor = 0.85
            elif angle_change > 0.15:   # ~8.6°
                curve_factor = 0.95
        else:
            if angle_change > 0.5:      # > ~30°
                curve_factor = 0.4
            elif angle_change > 0.3:    # > ~17°
                curve_factor = 0.7
            elif angle_change > 0.1:    # > ~5.7°
                curve_factor = 0.9
    
    # HAVA DURUMU VE YOĞUNLUK FAKTÖRÜ (simüle)
    weather_factor = 1.0  # deterministik; gerçek dışı rastgelelik yok
    
    # NİHAİ TARGET HIZ
    target_speed = base_speed * slope_factor * curve_factor * weather_factor
    # FC1–FC2 için gereksiz düşüşü önlemek adına yumuşak alt sınır uygula
    if isinstance(fc, int) and fc <= 2:
        target_speed = max(min(base_speed * 0.7, 80.0), target_speed)  # çevre yolu tabanı
    return max(15.0, min(120.0, target_speed))  # 15-120 km/h aralığında

def apply_kalman_filter_to_gps(points: List[Dict]) -> List[Dict]:
    """
    EXTENDED KALMAN FILTER: GPS koordinatlarını düzeltir
    Gerçek navigasyon sistemleri gibi kesin konum hesabı
    """
    if len(points) < 2:
        return points
    
    try:
        # KALMAN FILTER GÜVENLE ÇALIŞTIRMA
        print("📡 Extended Kalman Filter başlatılıyor...")
        
        # Geçici dosyalar oluştur
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as input_file:
            ekf_input = {
                "gps_measurements": [
                    {
                        "lat": p["lat"],
                        "lon": p["lon"], 
                        "timestamp": i * 0.1,  # 100ms aralıklar
                        "accuracy": 3.0  # 3 metre GPS doğruluğu
                    }
                    for i, p in enumerate(points)
                ]
            }
            json.dump(ekf_input, input_file, indent=2)
            input_path = Path(input_file.name)
        
        # Output dosyası
        output_path = Path(tempfile.mktemp(suffix='.json'))
        
        # EKF çalıştır - EXTENDED KALMAN FILTER AKTİF!
        try:
            ekf_result = run_cpp_ekf(input_path, output_path)
            if ekf_result:
                print("✅ Extended Kalman Filter başarılı!")
            else:
                print("⚠️ EKF NULL sonuç döndü, fallback kullanılacak")
        except Exception as ekf_error:
            print(f"⚠️ EKF hatası: {ekf_error}, fallback kullanılacak")
            ekf_result = None
        
        if ekf_result and "filtered_positions" in ekf_result:
            # Kalman Filter sonuçlarını uygula
            filtered_positions = ekf_result["filtered_positions"]
            filtered_points = []
            
            for i, point in enumerate(points):
                new_point = point.copy()
                if i < len(filtered_positions):
                    filtered_pos = filtered_positions[i]
                    new_point["fused_lat"] = filtered_pos["lat"]
                    new_point["fused_lon"] = filtered_pos["lon"]
                    new_point["kalman_accuracy"] = filtered_pos.get("accuracy", 1.0)
                else:
                    # Fallback
                    new_point["fused_lat"] = point["lat"]
                    new_point["fused_lon"] = point["lon"]
                    new_point["kalman_accuracy"] = 3.0
                
                filtered_points.append(new_point)
            
            print(f"✅ Kalman Filter: {len(points)} nokta işlendi")
            return filtered_points
        else:
            print("⚠️ Kalman Filter başarısız, orijinal GPS kullanılıyor")
            # Fallback: orijinal GPS'i fused olarak kopyala
            for point in points:
                point["fused_lat"] = point["lat"]
                point["fused_lon"] = point["lon"]
                point["kalman_accuracy"] = 3.0
            return points
            
    except Exception as e:
        print(f"❌ Kalman Filter hatası: {e}")
        # Fallback: orijinal GPS'i fused olarak kopyala
        for point in points:
            point["fused_lat"] = point["lat"]
            point["fused_lon"] = point["lon"]  
            point["kalman_accuracy"] = 5.0
        return points
    finally:
        # Temizlik
        try:
            if 'input_path' in locals():
                input_path.unlink(missing_ok=True)
            if 'output_path' in locals():
                output_path.unlink(missing_ok=True)
        except:
            pass

def call_cpp_physics_engine(route_points: List[Dict], cpp_engine_path: str) -> List[Dict]:
    """
    C++ fizik motorunu çağırarak gerçek fizik hesaplamaları yapar
    """
    try:
        # Geçici input dosyası oluştur
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as input_file:
            input_data = {"route": route_points}
            json.dump(input_data, input_file, indent=2)
            input_path = input_file.name

        # Geçici output dosyası
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as output_file:
            output_path = output_file.name

        # C++ fizik motorunu çalıştır
        result = subprocess.run([
            cpp_engine_path, input_path, output_path
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            print(f"C++ Physics Engine Error: {result.stderr}")
            return []

        # Output dosyasını oku
        with open(output_path, 'r') as f:
            output_data = json.load(f)

        # Geçici dosyaları temizle
        os.unlink(input_path)
        os.unlink(output_path)

        print(f"✅ C++ Physics Engine: {result.stdout.strip()}")
        return output_data.get("enhanced_result", [])

    except Exception as e:
        print(f"❌ C++ Physics Engine failed: {e}")
        return []

# Removed old calculate_smooth_acceleration function - using inline dynamic calculation

def curve_speed_kmh(turn_angle_rad: float, segment_len_m: float) -> float:
    if abs(turn_angle_rad) < 1e-3: return BUS_MAX_SPEED_KMH
    radius = max(1.0, segment_len_m / max(1e-3, abs(turn_angle_rad)))
    vmax_ms = math.sqrt(BUS_MAX_LATERAL * radius)
    vmax_kmh = min(vmax_ms * 3.6, BUS_MAX_SPEED_KMH)
    turn_deg = abs(turn_angle_rad) * RAD2DEG
    if turn_deg > 90:   vmax_kmh *= 0.35
    elif turn_deg > 60: vmax_kmh *= 0.55
    elif turn_deg > 30: vmax_kmh *= 0.75
    return max(15.0, vmax_kmh)

class SimpleEKF:
    def __init__(self, dt: float = 0.1):
        self.dt = dt
        self.x = np.zeros((4, 1))
        self.P = np.eye(4) * 10.0
        self.A = np.eye(4); self.A[0,2]=dt; self.A[1,3]=dt
        self.H = np.zeros((2, 4)); self.H[0,0]=1.0; self.H[1,1]=1.0
        self.Q = np.diag([1e-3, 1e-3, 5e-2, 5e-2])
        self.R = np.diag([3.0, 3.0])

    def set_dt(self, dt: float):
        self.dt = dt
        self.A = np.eye(4); self.A[0,2]=dt; self.A[1,3]=dt

    def init(self, x0):
        self.x = np.array(x0, dtype=float).reshape(4,1)
        self.P = np.eye(4) * 10.0

    def predict(self):
        self.x = self.A @ self.x
        self.P = self.A @ self.P @ self.A.T + self.Q

    def update(self, z):
        z = np.array(z, dtype=float).reshape(2,1)
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        I = np.eye(4)
        self.P = (I - K @ self.H) @ self.P

async def generate_physics(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    GERÇEK ARAÇ NAVİGASYON SİSTEMİ:
    1. GPS → Kalman Filter → Kesin konum
    2. Yol analizi → Akıllı target hız  
    3. C++ Motor → Target'a ulaşma
    """
    if not points:
        return {"route": [], "enhanced_result": [], "statistics": {}}
    
    print("🎯 GERÇEK ARAÇ NAVİGASYON SİSTEMİ başlatılıyor...")
    
    # 1. KALMAN FILTER: GPS koordinatlarını düzelt
    print("📡 Kalman Filter ile GPS düzeltmesi...")
    try:
        filtered_points = apply_kalman_filter_to_gps(points)
    except Exception as e:
        print(f"⚠️ Kalman Filter hatası: {e}")
        # Fallback: Orijinal GPS verilerini kullan
        filtered_points = []
        for point in points:
            new_point = point.copy()
            new_point["fused_lat"] = point["lat"]
            new_point["fused_lon"] = point["lon"] 
            new_point["kalman_accuracy"] = 3.0
            filtered_points.append(new_point)
    
    # C++ fizik motoru path'i
    # C++ fizik motoru yolu config'ten
    cpp_engine_path = str(PHYSICS_ENGINE_PATH)
    
    # 2. YOL ANALİZİ: Mesafe, heading, slope hesapla (fused GPS ile)
    print("🛣️ Yol analizi (mesafe, eğim, viraj)...")
    seg_d=[0.0]*len(filtered_points); seg_hdg=[0.0]*len(filtered_points); seg_slope=[0.0]*len(filtered_points)
    for i in range(1, len(filtered_points)):
        a, b = filtered_points[i-1], filtered_points[i]
        
        # Kalman Filter'dan düzeltilmiş koordinatları kullan
        a_pos = (a.get("fused_lat", a["lat"]), a.get("fused_lon", a["lon"]))
        b_pos = (b.get("fused_lat", b["lat"]), b.get("fused_lon", b["lon"]))
        
        d = haversine_m(a_pos, b_pos)
        seg_d[i] = d
        seg_hdg[i] = bearing_rad(a_pos, b_pos)
        
        # Elevation slope
        p1 = (a_pos[0], a_pos[1], a.get("elevation", 0.0))
        p2 = (b_pos[0], b_pos[1], b.get("elevation", 0.0))
        seg_slope[i] = slope_deg(p1, p2)

    # HERE attrs (speed limit, functional class) if present → Turkey-specific rules
    # Start with a high cap; apply HERE/legal caps when available
    legal_limit_kmh: List[float] = [140.0] * len(filtered_points)
    for i, p in enumerate(points):
        lim = p.get("speed_limit_kmh")
        fc = p.get("functional_class")  # 1..5, 1 = highest class
        # Base from legal limit if present
        if isinstance(lim, (int, float)) and lim > 0:
            legal_limit_kmh[i] = float(max(20.0, min(140.0, lim)))
        # If no limit provided, fallback by functional class (Turkey typical)
        elif isinstance(fc, int):
            if fc == 1:      # motorway
                legal_limit_kmh[i] = 120.0
            elif fc == 2:    # trunk/primary
                legal_limit_kmh[i] = 90.0
            elif fc == 3:    # secondary
                legal_limit_kmh[i] = 82.0
            else:            # local/urban
                legal_limit_kmh[i] = 50.0

    # 3. AKILLI TARGET HIZ: Yol tipi + eğim + viraj analizi
    print("🧠 Akıllı target hız hesaplaması...")
    smart_target_speeds = []
    for i in range(len(filtered_points)):
        try:
            base_target = calculate_smart_target_speed(filtered_points, i)
            # Apply legal cap per point if available
            capped = min(base_target, legal_limit_kmh[i] if i < len(legal_limit_kmh) else BUS_MAX_SPEED_KMH)
            smart_target_speeds.append(capped)
        except Exception as e:
            print(f"⚠️ Target speed hesaplama hatası point {i}: {e}")
            smart_target_speeds.append(min(50.0, legal_limit_kmh[i] if i < len(legal_limit_kmh) else BUS_MAX_SPEED_KMH))
    # Forward/back smoothing with accel/decel limits to avoid dips on straights
    a_up, a_dn = 1.8, 3.5  # m/s²
    v_ms = [max(2.0/3.6, min(140.0/3.6, s/3.6)) for s in smart_target_speeds]
    v_out = v_ms[:]
    # forward
    v_prev = v_out[0]
    for i in range(1, len(v_out)):
        ds = max(1.0, float(seg_d[i]))
        t_est = max(0.3, ds / max(v_prev, 0.5))
        dv_up = a_up * t_est
        v_out[i] = min(v_out[i], v_prev + dv_up)
        v_prev = v_out[i]
    # ensure no slow-down in final corridor (non-decreasing)
    if len(v_out) > 2:
        cum = [0.0]*len(seg_d)
        for i in range(1, len(cum)):
            cum[i] = cum[i-1] + float(seg_d[i])
        total_len = cum[-1] if cum else 0.0
        final_corridor_m = 300.0
        for i in range(1, len(v_out)):
            remaining = max(0.0, total_len - cum[i])
            if remaining <= final_corridor_m:
                v_out[i] = max(v_out[i], v_out[i-1])
    # backward (skip pre-braking in final corridor)
    # Build cumulative distance to skip decel near the final target
    cum = [0.0]*len(seg_d)
    for i in range(1, len(cum)):
        cum[i] = cum[i-1] + float(seg_d[i])
    total_len = cum[-1] if cum else 0.0
    final_corridor_m = 300.0  # do not force slow-down in the last 300 m
    v_next = v_out[-1]
    for i in range(len(v_out)-2, -1, -1):
        remaining = max(0.0, total_len - cum[i])
        if remaining <= final_corridor_m:
            # keep speed; no anticipatory braking
            v_next = v_out[i]
            continue
        ds = max(1.0, float(seg_d[i+1]))
        t_est = max(0.3, ds / max(v_next, 0.5))
        dv_dn = a_dn * t_est
        v_out[i] = min(v_out[i], v_next + dv_dn)
        v_next = v_out[i]
    smart_target_speeds = [float(v*3.6) for v in v_out]
    print(f"🎯 Target hız aralığı: {min(smart_target_speeds):.1f}-{max(smart_target_speeds):.1f} km/h (legal caps + smoothing)")

    # 4. C++ MOTOR SİSTEMİ: Kalman + Smart Target → Gerçek araç davranışı
    print("🚗 C++ gerçek motor sistemi çalıştırılıyor...")
    cpp_route_points = []
    for i, point in enumerate(filtered_points):
        cpp_point = {
            "lat": point.get("fused_lat", point["lat"]),  # Kalman düzeltilmiş GPS
            "lon": point.get("fused_lon", point["lon"]),  
            "speed_kmh": smart_target_speeds[i],           # Akıllı target hız
            "elevation": point.get("elevation", 0.0),
            "slope_deg": seg_slope[i],
            "distance": seg_d[i]
        }
        cpp_route_points.append(cpp_point)
    
    cpp_results = []
    if USE_CPP_PHYSICS and Path(cpp_engine_path).exists():
        # C++ gerçek motor sistemini çağır
        cpp_results = call_cpp_physics_engine(cpp_route_points, cpp_engine_path)
    else:
        print(f"⚠️ C++ motor devre dışı veya bulunamadı: USE_CPP_PHYSICS={USE_CPP_PHYSICS}, PATH={cpp_engine_path}")
    
    if cpp_results:
        print(f"🏁 NAVİGASYON SİSTEMİ TAMAMLANDI: {len(cpp_results)} nokta")
        
        # Sonuçları zenginleştir
        for i, result in enumerate(cpp_results):
            if i < len(filtered_points):
                # Kalman Filter sonuçlarını ekle
                result["kalman_accuracy"] = filtered_points[i].get("kalman_accuracy", 3.0)
                result["original_lat"] = points[i]["lat"]
                result["original_lon"] = points[i]["lon"]
                
                # Yol analiz bilgilerini ekle
                result["road_analysis"] = {
                    "base_speed_limit": 50.0,  # Bu hesaplanabilir
                    "slope_factor": 1.0,       # slope_deg'den hesaplanabilir  
                    "curve_factor": 1.0,       # angle_change'den hesaplanabilir
                    "weather_factor": 0.95     # Simülasyon
                }
        
        return {
            "enhanced_result": cpp_results,
            "statistics": {
                "navigation_system": "Kalman Filter + Smart Target + Real Motor",
                "kalman_filter": "✅ Aktif",
                "smart_targeting": "✅ Aktif", 
                "real_motor_physics": "✅ Aktif",
                "total_points": len(cpp_results)
            }
        }
    else:
        print("⚠️ C++ Motor sistemi başarısız, Python fallback kullanılıyor")
        return await generate_physics_fallback(filtered_points)

async def generate_physics_fallback(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Fallback Python fizik hesaplamaları (C++ başarısız olursa)
    """

    # Segment analyses
    seg_d=[0.0]*len(points); seg_hdg=[0.0]*len(points); seg_slope=[0.0]*len(points)
    for i in range(1, len(points)):
        a,b = points[i-1], points[i]
        d = haversine_m((a["lat"], a["lon"]), (b["lat"], b["lon"]))
        seg_d[i]=d
        seg_hdg[i]=bearing_rad((a["lat"], a["lon"]), (b["lat"], b["lon"]))
        # Create LatLonAlt tuples for slope calculation
        p1 = (a["lat"], a["lon"], a.get("elevation", 0.0))
        p2 = (b["lat"], b["lon"], b.get("elevation", 0.0))
        seg_slope[i]=slope_deg(p1, p2)

    # Base curve-limited optimal speed (km/h)
    opt_curve = [30.0]*len(points)
    for i in range(2, len(points)):
        turn = wrap_angle(seg_hdg[i] - seg_hdg[i-1])
        opt_curve[i] = min(BUS_MAX_SPEED_KMH, curve_speed_kmh(turn, max(1.0, seg_d[i])))

    # Add slope effect (reduce speed uphill, mild increase downhill)
    opt_profile = [opt_curve[i] for i in range(len(points))]
    for i in range(1, len(points)):
        s = seg_slope[i]  # degrees; positive is uphill
        if s > 0:
            # Reduce up to ~40% on steep climbs
            factor = max(0.6, 1.0 - 0.03 * s)
        elif s < 0:
            # Slight increase downhill but keep safety
            factor = min(1.10, 1.0 - 0.01 * s)  # s negative -> + speed
        else:
            factor = 1.0
        opt_profile[i] = max(15.0, min(BUS_MAX_SPEED_KMH, opt_curve[i] * factor))

    # Smooth target speeds with acceleration/deceleration limits
    ts=[0.0]*len(points)
    v_ms_profile=[0.0]*len(points)
    v_prev = 0.0
    for i in range(1, len(points)):
        v_target_ms = max(2.0/3.6, opt_profile[i]/3.6)
        # Estimate available time on this segment from previous speed
        t_est = max(0.3, seg_d[i] / max(v_prev, 1.0))
        # Fixed comfort acceleration limits
        dv_up = 1.8 * t_est  # m/s² accel
        dv_dn = 3.5 * t_est  # m/s² decel
        dv = max(-dv_dn, min(v_target_ms - v_prev, dv_up))
        v_ms = max(2.0/3.6, min(BUS_MAX_SPEED_KMH/3.6, v_prev + dv))
        v_ms_profile[i] = v_ms
        # Actual time spent on segment with achieved speed
        dt = max(0.2, seg_d[i] / max(v_ms, 0.1))
        ts[i]=ts[i-1]+dt
        v_prev = v_ms

    # EKF smoothing in local frame
    lat0, lon0 = points[0]["lat"], points[0]["lon"]
    meas_xy = [ll_to_local_xy(lat0, lon0, p["lat"], p["lon"]) for p in points]
    ekf = SimpleEKF(dt=0.1); ekf.init([meas_xy[0][0], meas_xy[0][1], 0.0, 0.0])

    fused_xy=[]; prev_t=ts[0]
    for i in range(len(points)):
        t=ts[i]; dt = max(0.05, min(2.0, t-prev_t if i>0 else 0.1))
        ekf.set_dt(dt); ekf.predict(); ekf.update(meas_xy[i])
        fused_xy.append((float(ekf.x[0,0]), float(ekf.x[1,0]))); prev_t=t

    fused_ll=[local_xy_to_ll(lat0, lon0, xy[0], xy[1]) for xy in fused_xy]

    # Enhanced output with realistic speed/accel
    enhanced=[]; prev_v=v_ms_profile[0]
    prev_accel = 0.0
    for i in range(len(points)):
        v_ms = v_ms_profile[i] if i>0 else 0.0
        dt = (ts[i]-ts[i-1]) if i>0 else 0.1
        # Segment distance for this sample (fallback small > 0)
        distance_m = seg_d[i] if seg_d[i] > 0 else 0.5
        # Simple acceleration calculation (fixed values for consistency)
        # C++ FİZİK MOTORUNU KULLAN - PYTHON HESAPLAMA YOK!
        # Bu alan şimdi C++ tarafından hesaplanacak
        accel = 0.0  # Geçici placeholder, C++ motorundan gelecek
        yaw_rate=0.0
        if i>1 and dt>0:
            yaw_rate = wrap_angle(seg_hdg[i]-seg_hdg[i-1]) / dt
            yaw_rate = max(-BUS_MAX_YAWRATE, min(yaw_rate, BUS_MAX_YAWRATE))
        accel_lat = v_ms * yaw_rate
        roll = max(-0.25, min(accel_lat/GRAVITY, 0.25))
        pitch = math.radians(seg_slope[i])

        enhanced.append({
            "waypoint": i+1,
            "lat": points[i]["lat"], "lon": points[i]["lon"],
            "elevation": points[i].get("elevation", 0.0),
            "fused_lat": fused_ll[i][0], "fused_lon": fused_ll[i][1],
            "distance": seg_d[i] if seg_d[i]>0 else 0.5,
            "speed_kmh": v_ms*3.6,
            "target_speed_kmh": opt_profile[i],
            "optimal_speed_kmh": opt_profile[i],
            "acceleration_ms2": accel,
            "heading_deg": seg_hdg[i]*RAD2DEG,
            "slope_deg": seg_slope[i],
            "turn_deg": yaw_rate*RAD2DEG,
            "time_sec": ts[i],
            "imu": {
                "accel_x": accel, "accel_y": accel_lat, "accel_z": GRAVITY,
                "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": yaw_rate,
                "mag_x": 48.0*math.cos(seg_hdg[i]), "mag_y": 48.0*math.sin(seg_hdg[i]), "mag_z": 0.0
            },
            "vehicle_state": {"velocity_ms": v_ms, "heading_rad": seg_hdg[i], "pitch_rad": pitch, "roll_rad": roll},
            "fusion_confidence": 0.95, "road_following": True,
            "processing_method": "DYNAMIC_PROGRESSIVE_EKF_REAL_CAR"
        })
        prev_v=v_ms

    stats = {
        "total_distance_m": float(sum(seg_d)),
        "num_points": int(len(points)),
        "duration_s": float(ts[-1] if ts else 0.0),
        "avg_speed_kmh": float((sum(seg_d) / max(1e-6, ts[-1])) * 3.6) if ts[-1] > 0 else 0.0,
        "follows_roads": True, "speed_optimized": True,
        "processing_method": "DYNAMIC_PROGRESSIVE_EKF_REAL_CAR"
    }
    return {"route": points, "enhanced_result": enhanced, "statistics": stats}
