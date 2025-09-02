import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

with open('mapping-requirements.txt') as f:
    mapping_requirements = f.read().splitlines()

setuptools.setup(
    name="ladybug-comfort",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    author="Ladybug Tools",
    author_email="info@ladybug.tools",
    description="Ladybug comfort is a Python library that adds thermal comfort "
    "functionalities to Ladybug.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ladybug-tools/ladybug-comfort",
    packages=setuptools.find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        'mapping': mapping_requirements
    },
    entry_points={
        "console_scripts": ["ladybug-comfort = ladybug_comfort.cli:comfort"]
    },
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: IronPython",
        "Operating System :: OS Independent"
    ],
    license="AGPL-3.0"
)
