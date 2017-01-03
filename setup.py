from setuptools import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')


setup(
    name='pygenstub',
    version='1.0a2',
    description='Python stub file generator.',
    long_description=readme + '\n\n' + history,
    url='https://bitbucket.org/uyar/pygenstub',
    author='H. Turgut Uyar',
    author_email='uyar@tekir.org',
    license='GPL',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5'
    ],
    py_modules=['pygenstub'],
    install_requires=['docutils'],
    extras_require={
        'dev': [
            'flake8',
            'mypy-lang'
        ],
        'doc': [
            'sphinx'
        ],
        'test': [
            'pytest',
            'pytest-cov'
        ],
    },
    entry_points="""
        [console_scripts]
        pygenstub=pygenstub:main
    """
)
