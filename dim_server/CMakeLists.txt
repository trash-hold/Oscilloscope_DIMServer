cmake_minimum_required(VERSION 3.15)

# Set up project
project(DimSparc25 CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# Before running this CMake:
#   - build DIM on your system (make sure that libdim.a was created)
#   - create DIMDIR env var (should locate top directory of the dim library)
#   - modify dim_library_dir path if needed
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


# Local build
# ==========================================================
# Get the DIMDIR environment variable
set(DIMDIR_PATH $ENV{DIMDIR})

# Check if DIMDIR is set
if(NOT DIMDIR_PATH)
    message(FATAL_ERROR "DIMDIR environment variable is not set.")
endif()

# Set the path to the DIM include files
set(DIM_INCLUDE_DIR ${DIMDIR_PATH}/dim)

# Set the path to the DIM library
set(DIM_LIBRARY_DIR ${DIMDIR_PATH}/linux)
set(DIM_LIBRARY ${DIM_LIBRARY_DIR}/libdim.a)

# Add include directory
include_directories(./include)

# Add the DIM include directory
include_directories(${DIM_INCLUDE_DIR})

# Find source files
file(GLOB_RECURSE SOURCES "src/*.cxx")

# Remote dependencies
# ==========================================================
# Include the FetchContent module to manage dependencies
include(FetchContent)

# Declare the cppzmq dependency from GitHub
FetchContent_Declare(
  cppzmq
  GIT_REPOSITORY https://github.com/zeromq/cppzmq.git
  GIT_TAG        v4.10.0 # Use a specific, stable version
)

# Declare the libzmq dependency. cppzmq needs libzmq.
FetchContent_Declare(
  libzmq
  GIT_REPOSITORY https://github.com/zeromq/libzmq.git
  GIT_TAG        v4.3.5 # Use a specific, stable version
)

# Download and prepare the dependencies
FetchContent_MakeAvailable(cppzmq libzmq)

# Executable
# ==========================================================

# Add executable
add_executable(my_dim_server ${SOURCES})

# Link against the DIM library
target_link_libraries(my_dim_server PRIVATE ${DIM_LIBRARY})
target_link_libraries(my_dim_server PRIVATE cppzmq)