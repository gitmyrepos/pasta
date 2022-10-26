from setuptools import setup

from src.engine import VERSION

url_base = 'https://github.com/gitmyrepos/pasta'
download_url = '%s/archive/pasta-%s.tar.gz' % (url_base, VERSION)

setup(
    name='pasta',
    version=VERSION,
    description='Visualize your source code as DOT flowcharts',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    entry_points={
        'console_scripts': ['pasta=src.engine:main'],
    },
    license='MIT',
    author='gitmyrepos',
    author_email='',
    url=url_base,
    download_url=download_url,
    packages=['pasta'],
    python_requires='>=3.6',
    include_package_data=True,
    classifiers=[
        'Natural Language :: English',
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ]
)
