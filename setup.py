"""
Module used by the Wiz Instruqt Labs
  Created by: Joe Titra
"""

import setuptools

PACKAGE_VERSION = "0.2.0"

with open("README.md", "r") as fh:
    long_description = fh.read()

EXTRAS = {
    'adal': ['adal>=1.0.2']
}
REQUIRES = []
with open('requirements.txt') as f:
    for line in f:
        line, _, _ = line.partition('#')
        line = line.strip()
        if not line or line.startswith('setuptools'):
            continue
        elif ';' in line:
            requirement, _, specifier = line.partition(';')
            for_specifier = EXTRAS.setdefault(':{}'.format(specifier), [])
            for_specifier.append(requirement)
        else:
            REQUIRES.append(line)

setuptools.setup(
    name="pywizlabs",
    version=PACKAGE_VERSION,
    description="Common Functions used across the Instruqt SE Workshops",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Joe Titra",
    author_email="joe.titra@wiz.io",
    license="Apache License Version 2.0",
    url="https://github.com/jtitra/pywizlabs",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent"
    ],
    install_requires=REQUIRES,
    python_requires='>=3.12'
)
