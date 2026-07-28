from setuptools import find_packages, setup

# Read the list of dependencies from requirements.txt so we only have
# to maintain that list in one place.
with open("requirements.txt") as f:
    content = f.readlines()

requirements = [x.strip() for x in content if "git+" not in x]

setup(
    name="package_folder",
    version="0.1",
    install_requires=requirements,
    packages=find_packages(),
)
