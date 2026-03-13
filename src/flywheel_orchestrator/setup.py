from setuptools import setup, find_packages
import os
from glob import glob

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
        (os.path.join('share', package_name, 'prompts'), glob('flywheel_orchestrator/prompts/*.txt')),
    ],
    entry_points={
        'console_scripts': [
            'orchestrator = flywheel_orchestrator.orchestrator:main',
        ],
    },
)
