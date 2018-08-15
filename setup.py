from setuptools import setup

# brings in "version" and "description" vars
execfile(os.path.join('pytc', 'version.py'))

setup(name='pdsc',
    version=__version__,
    description=__description__,
    author='Gary Doran',
    author_email='Gary.B.Doran.Jr@jpl.nasa.gov',
    url='https://github-fn.jpl.nasa.gov/COSMIC/COSMIC_PDSC',
    license="BSD compatable (see the LICENSE file)",
    packages=['pdsc'],
    platforms=['unix'],
    scripts=[
        'bin/pdsc_util',
        'bin/pdsc_ingest',
        'bin/pdsc_server',
    ],
    install_requires=[
        'numpy',
        'scipy',
        'scikit-learn',
        'Polygon2',
        'progressbar',
        'PyPDS>=1.0.1',
        'PyYAML',
        'geographiclib',
        'CherryPy',
        'requests',
    ],
    dependency_links=[
        'git+https://github.com/RyanBalfanz/PyPDS.git#egg=PyPDS-1.0.1'
    ],
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
