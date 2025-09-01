#include "physics_engine.hpp"
#include "json.hpp"
#include <iostream>
#include <fstream>
#include <vector>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

using json = nlohmann::json;

struct RoutePoint {
    double lat;
    double lon;
    double speed_kmh;
    double elevation_m;
    double slope_deg;
    double distance_m;
};

int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cerr << "Usage: " << argv[0] << " <input.json> <output.json>" << std::endl;
        return 1;
    }

    try {
        // Read input JSON
        std::ifstream input_file(argv[1]);
        json input_data;
        input_file >> input_data;
        
        // Parse route points
        std::vector<RoutePoint> route_points;
        for (const auto& point : input_data["route"]) {
            RoutePoint rp;
            rp.lat = point["lat"];
            rp.lon = point["lon"];
            rp.speed_kmh = point["speed_kmh"];
            rp.elevation_m = point.value("elevation", 0.0);
            rp.slope_deg = point.value("slope_deg", 0.0);
            rp.distance_m = point.value("distance", 1.0);
            route_points.push_back(rp);
        }

        // Create physics engine
        VehicleParams params;
        params.mass_kg = 1500.0;
        params.frontal_area_m2 = 2.5;
        params.drag_coefficient = 0.35;
        params.rolling_resistance = 0.015;
        params.max_engine_power_kw = 150.0;
        params.max_brake_force_n = 8000.0;

        PhysicsEngine physics(0.1, params);
        
        // Process each point
        json output_data;
        output_data["enhanced_result"] = json::array();
        
        VehicleState current_state;
        current_state.speed_ms = 0.0;
        current_state.acceleration_ms2 = 0.0;
        current_state.position_m = 0.0;
        current_state.engine_rpm = params.idle_rpm;
        current_state.current_gear = 1;
        current_state.throttle_percent = 0.0;
        current_state.brake_percent = 0.0;
        
        // Target hız için rampa sınırlayıcı (ani değişimleri engelle)
        double filtered_target_ms = route_points.empty() ? 0.0 : route_points.front().speed_kmh / 3.6;
        const double dt = 0.1; // time step
        const double target_rate_ms_per_s = 1.5; // hedef hız değişim sınırı (m/s^2 karşılığı)
        const double max_target_delta = target_rate_ms_per_s * dt; // her adımda max değişim

        for (size_t i = 0; i < route_points.size(); ++i) {
            const auto& point = route_points[i];
            
            // Convert target speed to m/s + rampa sınırlama
            double target_speed_ms_raw = point.speed_kmh / 3.6;
            double delta = target_speed_ms_raw - filtered_target_ms;
            if (delta > max_target_delta) delta = max_target_delta;
            if (delta < -max_target_delta) delta = -max_target_delta;
            filtered_target_ms += delta;
            double target_speed_ms = std::max(0.0, filtered_target_ms);
            
            // Convert slope to radians
            current_state.grade_rad = point.slope_deg * M_PI / 180.0;
            current_state.elevation_m = point.elevation_m;
            
            // Calculate physics-based acceleration
            double distance_to_target = point.distance_m;
            current_state.acceleration_ms2 = physics.calculateAcceleration(
                current_state.speed_ms,
                target_speed_ms,
                current_state.grade_rad,
                distance_to_target
            );
            
            // KRITIK: HIZ VE MOTOR GÜNCELLEMESİ OUTPUT'TAN ÖNCE OLMALI!
            current_state.speed_ms = std::max(0.0, current_state.speed_ms + current_state.acceleration_ms2 * dt);
            current_state.position_m += current_state.speed_ms * dt;
            
            // MOTOR VE VİTES GÜNCELLEMESİ
            current_state.current_gear = physics.selectOptimalGear(current_state.speed_ms, target_speed_ms);
            current_state.engine_rpm = physics.calculateEngineRPM(current_state.speed_ms, current_state.current_gear);
            
            // TARGET KONTROLÜ: aşma durumunda sert kesme yok (C++ ivme kontrolüne bırak)
            
            // Create output point
            json output_point;
            output_point["waypoint"] = i + 1;
            output_point["lat"] = point.lat;
            output_point["lon"] = point.lon;
            output_point["elevation"] = point.elevation_m;
            output_point["fused_lat"] = point.lat;
            output_point["fused_lon"] = point.lon;
            output_point["distance"] = point.distance_m;
            output_point["speed_kmh"] = current_state.speed_ms * 3.6;
            output_point["target_speed_kmh"] = point.speed_kmh;
            output_point["optimal_speed_kmh"] = point.speed_kmh;
            output_point["acceleration_ms2"] = current_state.acceleration_ms2;
            output_point["heading_deg"] = 0.0; // Will be calculated by Python
            output_point["slope_deg"] = point.slope_deg;
            output_point["turn_deg"] = 0.0;
            output_point["time_sec"] = i * 0.1;
            
            // Add physics-specific data - GERÇEK MOTOR BİLGİLERİ
            output_point["physics"] = {
                {"engine_force_n", 0.0},  // Hesaplanacak
                {"drag_force_n", 0.0},    // Hesaplanacak
                {"rolling_force_n", 0.0}, // Hesaplanacak
                {"grade_force_n", 0.0},   // Hesaplanacak
                {"net_force_n", current_state.acceleration_ms2 * params.mass_kg}
            };
            
            // MOTOR VE VİTES BİLGİLERİ
            output_point["engine"] = {
                {"rpm", current_state.engine_rpm},
                {"gear", current_state.current_gear},
                {"throttle_percent", current_state.throttle_percent},
                {"brake_percent", current_state.brake_percent}
            };
            
            output_data["enhanced_result"].push_back(output_point);
        }

        // Add statistics
        output_data["statistics"] = {
            {"total_points", route_points.size()},
            {"physics_engine", "C++ Real Physics"},
            {"vehicle_mass_kg", params.mass_kg},
            {"max_power_kw", params.max_engine_power_kw}
        };

        // Write output JSON
        std::ofstream output_file(argv[2]);
        output_file << output_data.dump(2);
        
        std::cout << "C++ Physics calculation completed successfully!" << std::endl;
        std::cout << "Processed " << route_points.size() << " route points" << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
