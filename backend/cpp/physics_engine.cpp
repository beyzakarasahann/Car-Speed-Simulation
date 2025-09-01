#include "physics_engine.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

PhysicsEngine::PhysicsEngine(double dt, VehicleParams params) 
    : dt_(dt), params_(params) {
}

double PhysicsEngine::calculateDragForce(double speed_ms) {
    // F_drag = 0.5 * ρ * Cd * A * v²
    return 0.5 * params_.air_density * params_.drag_coefficient * 
           params_.frontal_area_m2 * speed_ms * speed_ms;
}

double PhysicsEngine::calculateRollingResistance(double speed_ms) {
    // F_rolling = Cr * m * g * (1 + v/100) - speed dependency
    return params_.rolling_resistance * params_.mass_kg * params_.gravity_ms2 * 
           (1.0 + speed_ms / 100.0);
}

double PhysicsEngine::calculateGradeResistance(double grade_rad) {
    // F_grade = m * g * sin(θ)
    return params_.mass_kg * params_.gravity_ms2 * std::sin(grade_rad);
}

// GERÇEK MOTOR RPM HESABI
double PhysicsEngine::calculateEngineRPM(double speed_ms, int gear) {
    if (gear < 1 || gear > 6) gear = 1;
    double gear_ratio = params_.gear_ratios[gear - 1];
    double wheel_speed_rpm = (speed_ms / params_.wheel_radius_m) * 60.0 / (2.0 * M_PI);
    return wheel_speed_rpm * gear_ratio * params_.final_drive_ratio;
}

// OPTIMAL VİTES SEÇİMİ
int PhysicsEngine::selectOptimalGear(double speed_ms, double target_speed_ms) {
    // Mevcut hız için en uygun vitesi bul
    for (int gear = 1; gear <= 6; gear++) {
        double rpm = calculateEngineRPM(speed_ms, gear);
        if (rpm >= params_.idle_rpm && rpm <= params_.max_rpm * 0.85) {
            // Bu vites range'inde, hedef hıza uygun mu kontrol et
            double target_rpm = calculateEngineRPM(target_speed_ms, gear);
            if (target_rpm <= params_.max_rpm * 0.9) {
                return gear;
            }
        }
    }
    return 1; // Güvenli varsayılan
}

// GERÇEK MOTOR TORK EĞRİSİ
double PhysicsEngine::calculateEngineTorque(double rpm, double throttle_percent) {
    // Gerçek Honda motor tork eğrisi
    double torque_ratio = 1.0;
    
    if (rpm < params_.idle_rpm) {
        torque_ratio = 0.3; // Motor neredeyse durmuş
    } else if (rpm < params_.optimal_rpm) {
        // İdeal tork artışı
        torque_ratio = 0.6 + 0.4 * ((rpm - params_.idle_rpm) / (params_.optimal_rpm - params_.idle_rpm));
    } else if (rpm < params_.max_rpm * 0.8) {
        // Peak tork plateau
        torque_ratio = 1.0;
    } else {
        // Yüksek RPM'de tork düşer
        torque_ratio = 1.0 - 0.3 * ((rpm - params_.max_rpm * 0.8) / (params_.max_rpm * 0.2));
    }
    
    torque_ratio = std::max(0.2, std::min(1.0, torque_ratio));
    return params_.max_torque_nm * torque_ratio * (throttle_percent / 100.0);
}

// VİTES DEĞİŞİM KARARLARI
bool PhysicsEngine::shouldUpshift(double rpm, double speed_ms) {
    return rpm > params_.optimal_rpm * 1.3 && speed_ms > 5.0; // 18 km/h üstü
}

bool PhysicsEngine::shouldDownshift(double rpm, double speed_ms) {
    return rpm < params_.idle_rpm * 1.5 && speed_ms > 2.0; // 7 km/h üstü
}

// GERÇEK MOTOR KUVVET HESABI
double PhysicsEngine::calculateEngineForce(double speed_ms, double throttle_percent, int gear) {
    double rpm = calculateEngineRPM(speed_ms, gear);
    double torque_nm = calculateEngineTorque(rpm, throttle_percent);
    
    // Tork'u tekerlek kuvvetine çevir
    double gear_ratio = params_.gear_ratios[gear - 1];
    double total_ratio = gear_ratio * params_.final_drive_ratio;
    
    return (torque_nm * total_ratio) / params_.wheel_radius_m;
}

double PhysicsEngine::calculateBrakeForce(double brake_percent) {
    return params_.max_brake_force_n * (brake_percent / 100.0);
}

double PhysicsEngine::calculateAcceleration(
    double current_speed_ms,
    double target_speed_ms,
    double grade_rad,
    double distance_to_target_m) {
    
    // Input validation
    if (current_speed_ms < 0) current_speed_ms = 0.0;
    if (target_speed_ms < 0) target_speed_ms = 0.0;
    
    // Speed control
    const double speed_error = target_speed_ms - current_speed_ms;
    const bool need_accel = speed_error > 0.1;   // accelerate
    const bool need_brake = speed_error < -0.1;  // brake
    std::cout << "🚗 HIZ: " << current_speed_ms * 3.6 << " km/h → " << target_speed_ms * 3.6
              << " km/h | Fark: " << speed_error * 3.6 << " km/h | "
              << (need_accel ? "İVME" : need_brake ? "FREN" : "SABIT") << std::endl;

    // Resistances
    const double drag_force = calculateDragForce(current_speed_ms);
    const double rolling_force = calculateRollingResistance(current_speed_ms);
    const double grade_force = calculateGradeResistance(grade_rad);
    const double total_resistance = drag_force + rolling_force + grade_force;

    // Simple PI-like controller on speed error to compute desired acceleration
    const double Kp = 0.25;     // proportional gain [1/s] (daha yumuşak takip)
    const double desired_accel = std::max(-6.0, std::min(4.0, Kp * speed_error));

    double net_force = 0.0;

    if (need_accel) {
        // Map desired acceleration to throttle percentage
        // Also ensure we overcome resistances
        int gear = selectOptimalGear(current_speed_ms, target_speed_ms);
        // düşük hızlarda ani gazı sınırlamak için hızla ölçekle
        double throttle_percent = std::max(0.0, std::min(100.0, desired_accel * 20.0 + 8.0));
        if (current_speed_ms < 3.0) {
            throttle_percent = std::min(throttle_percent, 35.0);
        }
        double engine_force = calculateEngineForce(current_speed_ms, throttle_percent, gear);
        net_force = engine_force - total_resistance;

        // Limit by traction
        double max_available_accel = engine_force / params_.mass_kg;
        if (max_available_accel > 4.0) max_available_accel = 4.0;
        net_force = std::min(net_force, params_.mass_kg * max_available_accel);

    } else if (need_brake) {
        // Map desired negative acceleration to brake percentage
        double brake_percent = std::max(0.0, std::min(100.0, -desired_accel * 8.0));
        double brake_force = calculateBrakeForce(brake_percent);
        net_force = -(brake_force + total_resistance);

        // ABS/traction limits
        double max_brake_decel = 8.0; // m/s^2
        net_force = std::max(net_force, -params_.mass_kg * max_brake_decel);

    } else {
        // Constant-speed: provide just enough engine force to cancel resistances
        net_force = 0.0; // exact balance → zero acceleration
        std::cout << "🟡 SABİT HIZ MODU: Dirençleri dengeleme" << std::endl;
    }

    double acceleration = net_force / params_.mass_kg;
    acceleration = std::max(-6.0, std::min(4.0, acceleration));
    return acceleration;
}

VehicleState PhysicsEngine::simulateStep(
    const VehicleState& current_state,
    double target_speed_ms,
    double distance_to_target_m) {
    
    VehicleState next_state = current_state;
    
    // Calculate acceleration
    next_state.acceleration_ms2 = calculateAcceleration(
        current_state.speed_ms,
        target_speed_ms,
        current_state.grade_rad,
        distance_to_target_m
    );
    
    // Update speed: v = u + at
    next_state.speed_ms = current_state.speed_ms + 
                         next_state.acceleration_ms2 * dt_;
    
    // Ensure speed doesn't go negative
    next_state.speed_ms = std::max(0.0, next_state.speed_ms);
    
    // Update position: s = ut + 0.5at²
    double displacement = current_state.speed_ms * dt_ + 
                         0.5 * next_state.acceleration_ms2 * dt_ * dt_;
    next_state.position_m = current_state.position_m + displacement;
    
    return next_state;
}
