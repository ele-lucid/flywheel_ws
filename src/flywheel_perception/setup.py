import os
from glob import glob
from setuptools import setup

package_name = 'flywheel_perception'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Andrew Ashur',
    maintainer_email='aashur@lucidbots.com',
    description='Sensor processing and world model fusion',
    license='MIT',
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/flywheel_perception']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name), ['package.xml']),
    ],
    entry_points={
        'console_scripts': [
            'lidar_processor = flywheel_perception.lidar_processor:main',
            'depth_processor = flywheel_perception.depth_processor:main',
            'imu_processor = flywheel_perception.imu_processor:main',
            'world_model = flywheel_perception.world_model:main',
        ],
    },
)
