cmake_minimum_required(VERSION 3.10)
project(VehicleEKF)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Eigen3
find_package(Eigen3 REQUIRED)
if(NOT Eigen3_FOUND)
    message(FATAL_ERROR "Eigen3 not found! Install with: sudo apt-get install libeigen3-dev")
endif()

# Include directories
include_directories(${EIGEN3_INCLUDE_DIR})

# Add nlohmann/json (header-only)
find_path(JSON_INCLUDE_DIR nlohmann/json.hpp
    HINTS 
    /usr/include
    /usr/local/include
    ${CMAKE_SOURCE_DIR}/include
)

if(NOT JSON_INCLUDE_DIR)
    message(STATUS "nlohmann/json not found, downloading...")
    file(DOWNLOAD 
        "https://github.com/nlohmann/json/releases/download/v3.11.3/json.hpp"
        "${CMAKE_CURRENT_SOURCE_DIR}/json.hpp"
    )
    set(JSON_INCLUDE_DIR ${CMAKE_CURRENT_SOURCE_DIR})
endif()

include_directories(${JSON_INCLUDE_DIR})

# Compiler flags for optimization
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native -Wall -Wextra")
set(CMAKE_CXX_FLAGS_DEBUG "-g -Wall -Wextra")

# Create executable
add_executable(main main.cpp)

# Link Eigen3
target_link_libraries(main Eigen3::Eigen)

# Print info
message(STATUS "Eigen3 version: ${EIGEN3_VERSION}")
message(STATUS "Eigen3 include dir: ${EIGEN3_INCLUDE_DIR}")
message(STATUS "JSON include dir: ${JSON_INCLUDE_DIR}")

# Installation
install(TARGETS main DESTINATION bin)