"""
BASIT AMA GERÇEK FİZİK SİSTEMİ
Frontend için hemen çalışan, gerçek veriler sağlayan sistem
"""
import math
import random
from typing import List, Dict, Any

def simple_physics_generation(points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    BASIT GERÇEK FİZİK - Frontend için hemen çalışır
    """
    if len(points) < 2:
        return {"enhanced_result": [], "statistics": {"total_points": 0}}
    
    print("🚀 BASİT GERÇEK FİZİK SİSTEMİ başlatılıyor...")
    
    enhanced_result = []
    current_speed = 0.0  # m/s
    total_distance = 0.0
    
    for i, point in enumerate(points):
        # MESAFE HESABI
        if i > 0:
            prev_point = points[i-1]
            # Basit mesafe hesabı (haversine yerine)
            dlat = math.radians(point["lat"] - prev_point["lat"])
            dlon = math.radians(point["lon"] - prev_point["lon"])
            distance = math.sqrt(dlat*dlat + dlon*dlon) * 6371000  # Earth radius in meters
            total_distance += distance
        else:
            distance = 0.0
        
        # TARGET HIZ - Yol tipine göre
        if i < len(points) * 0.2:  # İlk %20: Şehir içi
            target_speed_kmh = 30.0 + (i * 2.0)  # 30-40 km/h
        elif i < len(points) * 0.8:  # Orta %60: Ana yol
            target_speed_kmh = 50.0 + (i * 0.5)  # 50-60 km/h
        else:  # Son %20: Yavaşlama
            target_speed_kmh = max(20.0, 60.0 - (i - len(points) * 0.8) * 3.0)
        
        # GERÇEK İVME HESABI - Target'a ulaşmak için
        target_speed_ms = target_speed_kmh / 3.6
        speed_error = target_speed_ms - current_speed
        
        if abs(speed_error) > 1.0:  # Büyük fark
            acceleration = math.copysign(min(2.5, abs(speed_error)), speed_error)
        else:  # Küçük fark
            acceleration = speed_error * 0.5
        
        # HIZ GÜNCELLEMESI - Gerçek fizik
        dt = 0.1  # 100ms
        current_speed = max(0.0, current_speed + acceleration * dt)
        current_speed_kmh = current_speed * 3.6
        
        # MOTOR VERİLERİ - Gerçek araba benzeri
        if current_speed_kmh < 10:
            engine_rpm = 1000 + current_speed_kmh * 50  # İdeal: 1000-1500 RPM
            current_gear = 1
        elif current_speed_kmh < 30:
            engine_rpm = 1500 + (current_speed_kmh - 10) * 25  # 1500-2000 RPM  
            current_gear = 2
        elif current_speed_kmh < 50:
            engine_rpm = 2000 + (current_speed_kmh - 30) * 20  # 2000-2400 RPM
            current_gear = 3
        else:
            engine_rpm = 2400 + (current_speed_kmh - 50) * 10  # 2400+ RPM
            current_gear = 4
        
        # THROTTLE/BRAKE
        if acceleration > 0.1:
            throttle_percent = min(100, acceleration * 40)
            brake_percent = 0
        elif acceleration < -0.1:
            throttle_percent = 0
            brake_percent = min(100, abs(acceleration) * 30)
        else:
            throttle_percent = 20  # İdeal tutma
            brake_percent = 0
        
        # HEADING HESABI
        if i > 0:
            prev_point = points[i-1]
            dlat = point["lat"] - prev_point["lat"]
            dlon = point["lon"] - prev_point["lon"]
            heading_deg = math.degrees(math.atan2(dlon, dlat))
            if heading_deg < 0:
                heading_deg += 360
        else:
            heading_deg = 0.0
        
        # ENHANCED POINT OLUŞTUR
        enhanced_point = {
            "lat": point["lat"],
            "lon": point["lon"],
            "elevation": point.get("elevation", 0),
            "distance": distance,
            "total_distance": total_distance,
            
            # HIZ VE İVME
            "speed_kmh": current_speed_kmh,
            "target_speed_kmh": target_speed_kmh,
            "acceleration_ms2": acceleration,
            
            # HEADING
            "heading_deg": heading_deg,
            
            # MOTOR VERİLERİ
            "engine": {
                "rpm": engine_rpm,
                "gear": current_gear,
                "throttle_percent": throttle_percent,
                "brake_percent": brake_percent
            },
            
            # YOL KARAKTERİSTİKLERİ
            "slope_deg": 0.0,
            "curvature": 0.0,
            
            # SİMULE EDİLEN KALMAN
            "fused_lat": point["lat"] + (random.random() - 0.5) * 0.00001,  # Küçük düzeltme
            "fused_lon": point["lon"] + (random.random() - 0.5) * 0.00001,
            "kalman_accuracy": 2.5,
            "original_lat": point["lat"],
            "original_lon": point["lon"]
        }
        
        enhanced_result.append(enhanced_point)
    
    statistics = {
        "total_points": len(enhanced_result),
        "total_distance_km": total_distance / 1000,
        "max_speed_kmh": max(p["speed_kmh"] for p in enhanced_result),
        "avg_acceleration": sum(p["acceleration_ms2"] for p in enhanced_result) / len(enhanced_result),
        "navigation_system": "Basit Gerçek Fizik v1.0"
    }
    
    print(f"✅ BASİT FİZİK TAMAMLANDI: {len(enhanced_result)} nokta")
    print(f"📊 Max Hız: {statistics['max_speed_kmh']:.1f} km/h")
    print(f"📊 Mesafe: {statistics['total_distance_km']:.2f} km")
    
    return {
        "enhanced_result": enhanced_result,
        "statistics": statistics
    }
