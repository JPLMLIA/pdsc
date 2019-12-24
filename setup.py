import os
import sys
from setuptools import setup

# brings in "version" and "description" vars
versionfile = 'version.py'
versionpath = os.path.join('pdsc', versionfile)
with open(versionpath, 'r') as f:
    code = compile(f.read(), versionfile, 'exec')
    exec(code)

if sys.version_info[0] == 2:
    install_requires=[
        'tempora<=1.13',
        'more-itertools<5.0.0',
        'numpy<=1.16',
        'scipy==0.13.3',
        'scikit-learn<0.20.0',
        'Polygon2',
        'progressbar',
        'PyYAML',
        'geographiclib',
        'CherryPy<18.0.0',
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
    url='https://github-fn.jpl.nasa.gov/COSMIC/COSMIC_PDSC',
    license="BSD compatable (see the LICENSE file)",
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
