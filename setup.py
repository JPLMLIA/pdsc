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
        'geographiclib',
        'CherryPy',
    ],
    provides=[
        'pdsc',
    ],
    include_package_data=True
)
