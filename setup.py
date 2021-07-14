import os
import glob

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements-dev.txt", "r") as fh:
    tests_require = [line for line in fh.read().split(os.linesep) if line]

with open("requirements.txt", "r") as fh:
    install_requires = [line for line in fh.read().split(os.linesep) if line]

setuptools.setup(
    name="edgerun-ether",
    version="0.4.0.dev3",
    author="Thomas Rausch",
    author_email="t.rausch@dsg.tuwien.ac.at",
    description="Ether - Synthesize plausible edge infrastructure topologies",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/edgerun/ether",
    packages=setuptools.find_packages(),
    include_package_data=True,
    package_data={'ether.inet': ['graphs/*.graphml']},
    setup_requires=['wheel'],
    test_suite="tests",
    tests_require=tests_require,
    install_requires=install_requires,
    pyton_requires='>=3.7',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    entry_points={
    },

)
