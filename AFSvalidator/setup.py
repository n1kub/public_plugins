from setuptools import setup, find_packages
from AFSvalidator.version import __version__

with open('requirements.txt', 'r') as f:
    reqs = f.readlines()
setup(
    name='AFSvalidator',
    version=__version__,
    packages=find_packages(),
    install_requires=reqs,
    # dependency_links=["git+https://readrepo:YQJMrPVMNr75CYwidazn@gitlab.corp.geoscan.aero/i.maksimchuk/test_project#egg=anchor_finder&subdirectory=anchor_finder"],
    include_package_data=True,
)