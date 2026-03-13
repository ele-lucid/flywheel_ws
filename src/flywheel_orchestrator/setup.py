import os
from glob import glob
from setuptools import setup, find_packages

package_name = 'flywheel_orchestrator'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    install_requires=['setuptools', 'openai'],
    zip_safe=True,
    maintainer='Andrew Ashur',
    maintainer_email='aashur@lucidbots.com',
    description='The flywheel agent brain',
    license='MIT',
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/flywheel_orchestrator']),
        (os.path.join('share', package_name), ['package.xml']),
        (os.path.join('share', package_name, 'prompts'), glob('flywheel_orchestrator/prompts/*.txt')),
    ],
    entry_points={
        'console_scripts': [
            'orchestrator = flywheel_orchestrator.orchestrator:main',
        ],
    },
)
