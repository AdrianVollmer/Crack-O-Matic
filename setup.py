import setuptools
from crackomatic._version import __version__

setuptools.setup(
    name='Crack-O-Matic',
    version=__version__,
    author='Adrian Vollmer',
    description='Find and notify users in your Active Directory '
                'with weak passwords',
    long_description=open('README.md', 'r').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/AdrianVollmer/Crack-O-Matic",
    project_urls={
        "Read The Docs": "https://crack-o-matic.readthedocs.io",
        "Issue Tracker":
        "https://github.com/AdrianVollmer/Crack-O-Matic/issues",
    },
    packages=setuptools.find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'crackomatic=crackomatic.__main__:main'
        ],
    },
    install_requires=[
        'flask>=1.0.2',
        'flask-login>=0.4.1',
        'flask-wtf',
        'flask-migrate>=2.1.1',
        'gevent>=1.3.7',
        'sqlalchemy>=1.2.18',
        'matplotlib>=3.0.2',
        'wtforms>=2.2.0',
        'ldap3>=2.4.1',
        'argon2-cffi',
        'babel>=2.6.0',
    ],
    python_requires='>=3.6',
    extras_require={
        'tests': [
            'pytest',
            'pytest-dotenv',
            'python-dotenv',
            'python-ldap',
        ]
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
    ],
)
