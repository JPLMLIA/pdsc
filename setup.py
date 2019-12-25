import os
import sys
from setuptools import setup

# brings in "version" and "description" vars
versionfile = 'version.py'
versionpath = os.path.join('pdsc', versionfile)
with open(versionpath, 'r') as f:
    code = compile(f.read(), versionfile, 'exec')
    exec(code)

with open('README.md', 'r') as f:
    long_description = f.read()

if sys.version_info[0] == 2:
    install_requires=[
        'tempora<=1.11',
        'more-itertools<5.0.0',
        'numpy<=1.16',
        'scipy==0.13.3',
        'scikit-learn<0.20.0',
        'Polygon2',
        'progressbar',
        'PyYAML',
        'geographiclib',
        'cheroot==6.1.0',
        'CherryPy==14.0.1',
        'requests',
        'future',
    ]

elif sys.version_info[0] == 3:
    install_requires=[
        'numpy',
        'scipy',
        'scikit-learn',
        'Polygon3',
        'progressbar',
        'PyYAML',
        'geographiclib',
        'CherryPy',
        'requests',
        'future',
    ]

setup(name='pdsc',
    version=__version__,
    description=__description__,
    author='Gary Doran',
    author_email='Gary.B.Doran.Jr@jpl.nasa.gov',
    url='https://github.com/JPLMLIA/pdsc',
    license="BSD compatable (see the LICENSE file)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=['pdsc'],
    platforms=['unix'],
    python_requires='>=2.7',
    scripts=[
        'bin/pdsc_util',
        'bin/pdsc_ingest',
        'bin/pdsc_server',
    ],
    install_requires=install_requires,
    provides=[
        'pdsc',
    ],
    include_package_data=True,
    extras_require={
        'devel':  [
            'pytest',
            'pytest-cov',
            'mock',
            'sphinx',
            'sphinx_rtd_theme',
        ],
    }
)
