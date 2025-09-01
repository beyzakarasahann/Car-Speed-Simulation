cmake_minimum_required(VERSION 3.12)
project(physics_engine)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create standalone physics executable
add_executable(physics_engine 
    physics_engine.cpp
    physics_main.cpp
)

# Compile options
target_compile_features(physics_engine PRIVATE cxx_std_17)
