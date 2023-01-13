import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cicsim",
    version="0.1.1",
    author="Carsten Wulff",
    author_email="carsten@wulff.no",
    description="Custom IC Creator Simulation Tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wulffern/cicsim",
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    entry_points = {'console_scripts': [
        'cicsim = cicsim.cicsim:cli',
    ]},
    install_requires = 'matplotlib numpy jinja2 tikzplotlib'.split(),
    classifiers = [
        'Development Status :: 1 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Natural Language :: English',
        "License :: OSI Approved :: MIT License",
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Utilities',
        'Topic :: Scientific/Engineering',
    ],
)
