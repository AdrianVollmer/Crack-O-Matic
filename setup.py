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
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'crackomatic=crackomatic.__main__:main'
        ],
    },
    install_requires=[
        'flask',
        'flask-login',
        'flask-wtf',
        'flask-migrate',
        'gevent',
        'sqlalchemy',
        'matplotlib',
        'wtforms',
        'ldap3',
        'argon2-cffi',
        'babel',
    ],
    python_requires='>=3',
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
