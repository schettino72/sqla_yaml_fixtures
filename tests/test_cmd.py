import os
import subprocess

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_sample():
    work_dir = os.path.dirname(__file__)
    db_file = '{}/sample.db'.format(work_dir)
    db_url = 'sqlite:///{}'.format(db_file)
    params = {
        'cwd': work_dir,
        'url': db_url,
        'base': 'sample.schema:BaseModel',
        'files': 'sample/fixtures.yaml',
    }
    cmd = '''cd {cwd};'''\
          '''python -m sqla_yaml_fixtures'''\
          '''       --db-url "{url}"'''\
          '''       --db-base "{base}"'''\
          '''       --yes --reset-db'''\
          '''       {files}'''.format(**params)

    subprocess.check_call(cmd, shell=True)


    engine = create_engine(db_url)
    connection = engine.connect()
    session = Session(bind=connection)

    # TEST
    from sample.schema import User
    users = session.query(User).all()
    assert len(users) == 2
    assert users[0].username == 'joey'
    assert users[1].username == 'deedee'
