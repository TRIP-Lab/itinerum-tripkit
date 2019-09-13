import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="itinerum-tripkit",
    version="0.0.1",
    author="Kyle Fitzsimmons",
    author_email="kfitzsimmons@gmail.com",
    description="A toolkit for inferencing trips and trip metadata from Itinerum GPS data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/TRIP-Lab/itinerum-tripkit",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent"
    ]
)
