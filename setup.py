import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='itinerum-tripkit',
    version='0.0.1',
    author='Kyle Fitzsimmons',
    author_email='kfitzsimmons@gmail.com',
    description='A toolkit for inferencing trips and trip metadata from Itinerum GPS data',
    install_requires=[
        'ciso8601>=2.1.1',
        'fiona>=1.8.6',
        'geopy>=1.20.0',
        'numpy>=1.17.2',
        'peewee>=3.10.0',
        'polyline>=1.4.0',
        'pytz>=2019.2',
        'requests>=2.22.0',
        'scipy>=1.3.1',
        'utm>=0.5.0',
    ],
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/TRIP-Lab/itinerum-tripkit',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent'
    ],
    python_requires='>=3.6',
)
