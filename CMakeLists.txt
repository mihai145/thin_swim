cmake_minimum_required(VERSION 3.22)

project(CMakeProject VERSION 1.0 DESCRIPTION "Thin SWIM" LANGUAGES C)

# debug/release mode
set(CMAKE_BUILD_TYPE Debug)

add_library(c_setup INTERFACE)
target_compile_features(c_setup INTERFACE c_std_11)
target_compile_options(c_setup INTERFACE -Wall -Wextra)

add_executable(node node.c state.c util.c)
add_executable(start start.c)
add_executable(test_log test_log.c util.c)

# target_compile_definitions(node PRIVATE LOGS_SUCCINT)

target_link_libraries(node PRIVATE c_setup m)
target_link_libraries(start PRIVATE c_setup)
