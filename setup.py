from setuptools import setup

setup(name = 'sqla_yaml_fixtures',
      description = 'Load YAML data fixtures for SQLAlchemy',
      version = '0.1.1',
      license = 'MIT',
      author = 'Eduardo Naufel Schettino',
      author_email = 'schettino72@gmail.com',
      url = 'https://github.com/schettino72/sqla_yaml_fixtures',
      keywords = ['fixture', 'sqlalchemy'],
      classifiers = [
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Intended Audience :: Developers',
        ],
      py_modules = ['sqla_yaml_fixtures'],
      install_requires = ['SQLAlchemy', 'PyYAML'],
      long_description = '',
      )
