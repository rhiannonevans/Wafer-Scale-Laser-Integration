from setuptools import setup, find_packages

requirements = ['setuptools>=70.2.0', 'numpy>=1.26.4', 'matplotlib>=3.8.3', 'pandas>=2.1.3', 'scipy>=1.13.1']

setup(
    name='WaferIntegration',
    version='1.0',
    description='Package to process and plot results of Laser-Integration measurements',
    author='Rhiannon Evans',
    author_email='revans01@student.ubc.ca',
    packages=find_packages(),
    install_requires=requirements
)