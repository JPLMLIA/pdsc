from setuptools import setup

setup(name='pdsc',
    version="1.0",
    description='PDS Coincidences',
    author='Gary Doran',
    author_email='Gary.B.Doran.Jr@jpl.nasa.gov',
    url='https://github-fn.jpl.nasa.gov/COSMIC/COSMIC_PDSC',
    license="BSD compatable (see the LICENSE file)",
    packages=['pdsc'],
    platforms=['unix'],
    scripts=[
        'bin/pdsc_ingest',
        'bin/pdsc_server',
    ],
    install_requires=[
        'numpy',
        'scipy',
        'scikit-learn',
        'Polygon2',
        'progressbar',
        'PyPDS>=1.0.2',
        'PyYAML',
        'geographiclib',
        'CherryPy',
        'requests',
    ],
    dependency_links=[
        'git+https://github.com/RyanBalfanz/PyPDS.git#egg=PyPDS-1.0.2'
    ],
    provides=[
        'pdsc',
    ],
    include_package_data=True,
    extras_require={
        'devel':  [
            'pytest',
            'pytest-cov',
        ],
    }
)
