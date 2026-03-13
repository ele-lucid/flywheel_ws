cmake_minimum_required(VERSION 3.8)
project(flywheel_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf worlds config launch meshes
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
