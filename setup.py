from distutils.core import setup

setup(
    name='assay',
    version='0.0',
    description='Future testing framework',
    long_description='Not quite written yet',
    license='MIT',
    author='Brandon Rhodes',
    author_email='brandon@rhodesmill.org',
    url='http://github.com/brandon-rhodes/python-skyfield/',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        ],
    packages=['assay'],
    entry_points = {
        'console_scripts': ['assay=assay.command:main'],
        },
    )
