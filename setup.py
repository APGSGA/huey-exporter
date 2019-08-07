from setuptools import find_packages, setup

setup(
        name='huey-exporter',
        version='1.0.1.dev2',
        description=' Hueyx exporter for Prometheus',
        url='https://github.com/apgsga/huey-exporter',
        author='Severin Bühler',
        license='MIT',
        packages=find_packages(),
        include_package_data=True,
        install_requires=[
            'prometheus_client>=0.2.0',
            'click>=6.7',
            'redis>=2.10.6',
        ],
        entry_points={
          'console_scripts': [
              'huey_exporter = huey_exporter.exporter:main'
          ]
        }
)
