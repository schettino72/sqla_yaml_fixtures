from __future__ import print_function
from setuptools import setup
import sys

# Assume pip is new enough
pip_message = None
try:
    import pip
    pip_version = tuple([int(x) for x in pip.__version__.split('.')[:3]])
    if pip_version < (9, 0, 1) :
        pip_message = 'Your pip version is out of date, please install pip >= 9.0.1. '\
        'pip {} detected.'.format(pip.__version__)

except Exception:
    pip_message = 'This may be due to an out of date pip. Make sure you have pip >= 9.0.1.'


if pip_message:
    # Some error from pip version check
    error = """
    Python {py} detected.
    Exiting setup:
    {pip}
    """.format(py=sys.version_info, pip=pip_message )

    print(error, file=sys.stderr)
    sys.exit(1)


def readme():
    with open('README.rst') as fp:
        return fp.read()

setup(name='sqla_yaml_fixtures',
      description='Load YAML data fixtures for SQLAlchemy',
      version='1.0.0',
      license='MIT',
      author='Eduardo Naufel Schettino',
      author_email='schettino72@gmail.com',
      url='https://github.com/schettino72/sqla_yaml_fixtures',
      keywords=['fixture', 'sqlalchemy'],
      classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Intended Audience :: Developers',
        ],
      packages=['sqla_yaml_fixtures'],
      install_requires=[
          'SQLAlchemy',
          'PyYAML'
      ],
      long_description=readme(),
      )
