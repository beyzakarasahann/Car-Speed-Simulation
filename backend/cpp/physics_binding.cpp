#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "physics_engine.hpp"

namespace py = pybind11;

PYBIND11_MODULE(physics_cpp, m) {
    m.doc() = "C++ Physics Engine for Vehicle Dynamics";
    
    py::class_<VehicleState>(m, "VehicleState")
        .def(py::init<>())
        .def_readwrite("speed_ms", &VehicleState::speed_ms)
        .def_readwrite("acceleration_ms2", &VehicleState::acceleration_ms2)
        .def_readwrite("position_m", &VehicleState::position_m)
        .def_readwrite("grade_rad", &VehicleState::grade_rad)
        .def_readwrite("elevation_m", &VehicleState::elevation_m);
    
    py::class_<VehicleParams>(m, "VehicleParams")
        .def(py::init<>())
        .def_readwrite("mass_kg", &VehicleParams::mass_kg)
        .def_readwrite("frontal_area_m2", &VehicleParams::frontal_area_m2)
        .def_readwrite("drag_coefficient", &VehicleParams::drag_coefficient)
        .def_readwrite("rolling_resistance", &VehicleParams::rolling_resistance)
        .def_readwrite("max_engine_power_kw", &VehicleParams::max_engine_power_kw)
        .def_readwrite("max_brake_force_n", &VehicleParams::max_brake_force_n);
    
    py::class_<PhysicsEngine>(m, "PhysicsEngine")
        .def(py::init<double, VehicleParams>(),
             py::arg("dt") = 0.1, py::arg("params") = VehicleParams())
        .def("calculate_acceleration", &PhysicsEngine::calculateAcceleration,
             "Calculate realistic acceleration based on physics",
             py::arg("current_speed_ms"), py::arg("target_speed_ms"),
             py::arg("grade_rad"), py::arg("distance_to_target_m"))
        .def("simulate_step", &PhysicsEngine::simulateStep,
             "Simulate one physics time step",
             py::arg("current_state"), py::arg("target_speed_ms"),
             py::arg("distance_to_target_m"));
}
