'''cmd line program for sqla_yaml_fixtures'''

import sys
import argparse
import importlib
import subprocess

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import sqla_yaml_fixtures



def make_parser():
    '''create cmd line parser'''
    parser = argparse.ArgumentParser(
        prog='sqla_yaml_fixtures',
        description='load fixtures from yaml file into DB',)

    parser.add_argument(
        'files', metavar='FILE', type=str, nargs='+',
        help='YAML file with DB fixtures')

    parser.add_argument(
        '--db-base', required=True,
        help='SQLAlchemy Base class with schema metadata in the '\
             'format my_package.my_module:MyClass')

    parser.add_argument(
        '--db-url', required=True,
        help='Database URL in the format '\
             'dialect+driver://username:password@host:port/database')

    parser.add_argument(
        '--yes', action='store_true',
        help='Do NOT ask for confirmation before applying fixtures')

    parser.add_argument(
        '--reset-db', action='store_true',
        help='Drop DB schema and data and re-create schema '\
             'before loading fixtures')

    parser.add_argument(
        '--alembic-stamp', action='store_true',
        help='Perform `alembic stamp head`')

    parser.add_argument(
        '--jinja2', action='store_true',
        help='load fixture files as jinja2 templates')

    # TODO logging
    # import logging
    # logging.basicConfig()
    # logging.getLogger('sqlalchemy.engine').setLevel(logging.WARN)
    return parser


# TODO
# * pass arguments to `main()`


def main(argv=None):
    args = make_parser().parse_args(argv)

    if not args.yes:
        print('DB: \x1b[0;34;40m{}\x1b[0m'.format(args.db_url))
        if (args.reset_db):
            print('RESET DB: \x1b[0;37;41m{}\x1b[0m'.format('DB data will be deleted!'))
        print('Load fixtures, OK? (Ctrl-C to cancel)')
        try:
            input() # input doest matter
        except KeyboardInterrupt:
            print('\nCancelled.')
            sys.exit(100)

    # get Base mapper class and create engine
    engine = create_engine(args.db_url)
    module_name, class_name = args.db_base.split(':')
    module = importlib.import_module(module_name)
    BaseClass = getattr(module, class_name)

    # reset DB
    if args.reset_db:
        BaseClass.metadata.drop_all(engine)
        BaseClass.metadata.create_all(engine)

    # load fixtures
    connection = engine.connect()
    session = Session(bind=connection)
    try:
        fixture_yaml = []
        for fixture_name in args.files:
            print('Loading file: {} ...'.format(fixture_name))
            with open(fixture_name) as fp:
                if args.jinja2:
                    from jinja2 import Template
                    file_yaml = Template(fp.read()).render()
                else:
                    file_yaml = fp.read()
            fixture_yaml.append(file_yaml)
        data_yaml = '\n'.join(fixture_yaml)
        sqla_yaml_fixtures.load(BaseClass, session, data_yaml)
        session.commit()
    except:
        session.close()
        raise

    if args.alembic_stamp:
        subprocess.check_call('alembic stamp head', shell=True)

