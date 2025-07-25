cmake_minimum_required(VERSION 3.10.0)
project(Git++ VERSION 0.1.0 LANGUAGES C CXX)

include_directories("src/include")

add_executable(Git++ 
    main.cpp
    src/VCS.cpp
    src/CommandLine.cpp
)

