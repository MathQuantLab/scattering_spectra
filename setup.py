import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

with open('requirements.txt') as f:
    reqs = f.read().splitlines()

setuptools.setup(
    name='scatspectra',
    version='1.1.1',
    author='Rudy Morel',
    author_email='rmorel@flatironinstitute.org',
    description=
    'Analysis and generation of time-series with Scattering Spectra',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/M2QF/scattering_spectra',
    license='MIT',
    install_requires=reqs,
    packages=setuptools.find_packages(),
    package_data={'scatspectra': ['data/*.csv']})
