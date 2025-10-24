cmake_minimum_required(VERSION 3.16)
project(smartstocks_sim LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(smartstocks_sim src/smartstocks_sim.cpp)

if (MSVC)
    target_compile_options(smartstocks_sim PRIVATE /W4)
else()
    target_compile_options(smartstocks_sim PRIVATE -Wall -Wextra -Wpedantic)
endif()
