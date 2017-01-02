from setuptools import setup


setup(
    name='pygenstub',
    version='1.0a1',
    description='Python stub file generator.',
    long_description='',
    url='https://bitbucket.org/uyar/pygenstub',
    author='H. Turgut Uyar',
    author_email='uyar@tekir.org',
    license='GPL',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3.5',
    ],
    py_modules=['pygenstub'],
    install_requires=['docutils'],
    entry_points="""
        [console_scripts]
        pygenstub=pygenstub:main
    """
)
