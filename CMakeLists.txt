cmake_minimum_required(VERSION 3.22)

project(CMakeProject VERSION 1.0 DESCRIPTION "Thin SWIM" LANGUAGES C)

# debug/release mode
set(CMAKE_BUILD_TYPE Debug)

add_library(c_setup INTERFACE)
target_compile_features(c_setup INTERFACE c_std_11)
target_compile_options(c_setup INTERFACE -Wall -Wextra)
target_include_directories(c_setup INTERFACE include)

add_executable(node src/node.c src/node_manager.c src/state.c src/log.c)
add_executable(test_log test/test_log.c src/log.c)
add_executable(test_sleep test/test_sleep.c src/log.c src/time_utils.c)
add_executable(start start.c)

# target_compile_definitions(node PRIVATE LOGS_SUCCINT)

target_link_libraries(node PRIVATE c_setup m)
target_link_libraries(test_log PRIVATE c_setup)
target_link_libraries(test_sleep PRIVATE c_setup)
target_link_libraries(start PRIVATE c_setup)
