from setuptools import setup, find_packages
from anchor_finder.version import __version__

setup(
    name='anchor_finder',
    version=__version__,
    packages=find_packages(),
    # install_requires=['numpy==1.20.3+mkl','PySide2','opencv-python==4.4.0.46'],
    include_package_data=True,
)