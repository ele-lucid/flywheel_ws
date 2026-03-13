from setuptools import setup, find_packages

package_name = 'flywheel_missions'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Andrew Ashur',
    maintainer_email='aashur@lucidbots.com',
    description='Mission base class and generated missions',
    license='MIT',
    entry_points={
        'console_scripts': [
            'run_mission = flywheel_missions.mission_launcher:main',
        ],
    },
)
