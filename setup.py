import re
import setuptools
import sys

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('ladybug_comfort/__init__.py', 'r') as fd:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
        fd.read(),
        re.MULTILINE
    ).group(1)

try:
    from semantic_release import setup_hook
    setup_hook(sys.argv)
except ImportError:
    pass

setuptools.setup(
    name="ladybug-comfort",
    version=version,
    author="Ladybug Tools",
    author_email="info@ladybug.tools",
    description="Ladybug comfort is a Python library that adds the functionalities for modeling thermal comfort to Ladybug.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ladybug-tools/ladybug-comfort",
    packages=setuptools.find_packages(),
    install_requires=[
        'lbt-ladybug>=0.1.0'
    ],
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: CPython",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent"
    ],
)
