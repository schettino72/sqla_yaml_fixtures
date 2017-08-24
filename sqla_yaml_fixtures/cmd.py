'''cmd line program for sqla_yaml_fixtures'''

import argparse
import importlib

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import sqla_yaml_fixtures



def make_parser():
    '''create cmd line parser'''
    parser = argparse.ArgumentParser(
        prog='sqla_yaml_fixtures',
        description='load fixtures from yaml file into DB',)

    parser.add_argument('files', metavar='FILE', type=str, nargs='+',
                        help='YAML file with DB fixtures')
    parser.add_argument(
        '--db-base', required=True,
        help='SQLAlchemy Base class with schema metadata in the format my_package.my_module:MyClass')
    parser.add_argument(
        '--db-url', required=True,
        help='Database URL in the format dialect+driver://username:password@host:port/database')
    # parser.add_argument('--yes'
    # parser.add_argument('--jinja2'
    # parser.add_argument('--reset-db'
    # alembic_stamp
    # logging
    return parser


# TODO
# * pass arguments to `main()`


def main():
    args = make_parser().parse_args()
    print(args)

    # get Base mapper class and create engine
    engine = create_engine(args.db_url)
    module_name, class_name = args.db_base.split(':')
    module = importlib.import_module(module_name)
    BaseClass = getattr(module, class_name)

    if True:
        BaseClass.metadata.create_all(engine)

    connection = engine.connect()
    session = Session(bind=connection)
    for fixture in args.files:
        print('Loading file: {} ...'.format(fixture))
        with open(fixture) as fp:
            sqla_yaml_fixtures.load(BaseClass, session, fp.read())
    session.commit()

