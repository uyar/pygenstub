"""The module for installing pygenstub."""

from setuptools import setup


with open("README.rst") as readme_file:
    readme = readme_file.read()


setup(
    name="pygenstub",
    version="1.2",
    description="Python stub file generator.",
    long_description=readme,
    url="https://github.com/uyar/pygenstub",
    author="H. Turgut Uyar",
    author_email="uyar@tekir.org",
    license="GPL",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Framework :: Sphinx :: Extension",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Documentation :: Sphinx",
        "Topic :: Software Development :: Documentation",
    ],
    py_modules=["pygenstub"],
    install_requires=["docutils"],
    extras_require={
        "dev": [
            "black",
            "flake8",
            "flake8-isort",
            "flake8-docstrings",
            "readme_renderer",
            "wheel",
            "twine",
        ],
        "doc": ["sphinx", "sphinx_rtd_theme"],
        "test": ["pytest", "pytest-cov"],
    },
    entry_points="""
        [console_scripts]
        pygenstub=pygenstub:main
    """,
)
