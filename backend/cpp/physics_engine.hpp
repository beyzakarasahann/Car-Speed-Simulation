#ifndef PHYSICS_ENGINE_HPP
#define PHYSICS_ENGINE_HPP

#include <vector>
#include <cmath>

struct VehicleState {
    double speed_ms;        // m/s
    double acceleration_ms2; // m/s²
    double position_m;      // meters along route
    double grade_rad;       // road grade in radians
    double elevation_m;     // elevation in meters
    
    // MOTOR VE VİTES BİLGİLERİ
    double engine_rpm;      // Motor devri
    int current_gear;       // Mevcut vites (1-6)
    double throttle_percent; // Gaz pedalı (0-100%)
    double brake_percent;   // Fren pedalı (0-100%)
};

struct VehicleParams {
    // GERÇEK ARAÇ PARAMETRELERİ (Honda Civic benzeri)
    double mass_kg = 1400.0;           // Araç kütlesi
    double frontal_area_m2 = 2.1;      // Ön alan
    double drag_coefficient = 0.28;    // Aerodinamik direnç katsayısı (modern araç)
    double rolling_resistance = 0.012; // Yuvarlanma direnci (iyi lastikler)
    
    // MOTOR PARAMETRELERİ
    double max_engine_power_kw = 125.0; // 168 HP benzinli motor
    double max_torque_nm = 220.0;       // Maksimum tork
    double idle_rpm = 800.0;            // Rölanti devri
    double max_rpm = 6500.0;            // Kırmızı çizgi
    double optimal_rpm = 4000.0;        // Optimal tork devri
    
    // FREN SİSTEMİ
    double max_brake_force_n = 9000.0;  // ABS limitli fren
    double brake_disc_radius_m = 0.15;  // Fren diski yarıçapı
    
    // FİZİK SABİTLERİ
    double gravity_ms2 = 9.81;         // Yer çekimi
    double air_density = 1.225;        // Hava yoğunluğu
    
    // VİTES KUTUSU
    double gear_ratios[6] = {3.54, 2.06, 1.36, 1.03, 0.84, 0.70}; // 6 vites
    double final_drive_ratio = 4.35;   // Diferansiyel oranı
    double wheel_radius_m = 0.32;      // Tekerlek yarıçapı (205/55R16)
};

class PhysicsEngine {
private:
    VehicleParams params_;
    double dt_;

    // Calculate aerodynamic drag force
    double calculateDragForce(double speed_ms);
    
    // Calculate rolling resistance force
    double calculateRollingResistance(double speed_ms);
    
    // Calculate grade resistance force
    double calculateGradeResistance(double grade_rad);
    
    // GERÇEK MOTOR SİSTEMİ
    double calculateEngineTorque(double rpm, double throttle_percent);
    double calculateEngineForce(double speed_ms, double throttle_percent, int gear);
    
    // FREN SİSTEMİ
    double calculateBrakeForce(double brake_percent);
    
    // VİTES DEĞİŞİMİ
    bool shouldUpshift(double rpm, double speed_ms);
    bool shouldDownshift(double rpm, double speed_ms);

public:
    PhysicsEngine(double dt = 0.1, VehicleParams params = VehicleParams());
    
    // Calculate realistic acceleration based on current state and target speed
    double calculateAcceleration(
        double current_speed_ms,
        double target_speed_ms,
        double grade_rad,
        double distance_to_target_m
    );
    
    // Simulate vehicle dynamics for one time step
    VehicleState simulateStep(
        const VehicleState& current_state,
        double target_speed_ms,
        double distance_to_target_m
    );
    
    // PUBLIC MOTOR FONKSİYONLARI (main.cpp için)
    double calculateEngineRPM(double speed_ms, int gear);
    int selectOptimalGear(double speed_ms, double target_speed_ms);
};

#endif // PHYSICS_ENGINE_HPP
