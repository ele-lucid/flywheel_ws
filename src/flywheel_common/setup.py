from setuptools import setup, find_packages

package_name = 'flywheel_common'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Andrew Ashur',
    maintainer_email='aashur@lucidbots.com',
    description='Shared constants and utilities for the flywheel project',
    license='MIT',
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
)
