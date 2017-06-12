from doitpy.pyflakes import Pyflakes
from doitpy.coverage import Coverage, PythonModule


DOIT_CONFIG = {
    'default_tasks': ['pyflakes'],
    'verbosity': 2,
}


def task_pyflakes():
    flaker = Pyflakes()
    yield flaker.tasks('*.py')


def task_coverage():
    """show coverage for all modules including tests"""
    cov = Coverage(
        [PythonModule('sqla_yaml_fixtures.py', 'test_sqla_yaml_fixtures.py')],
        config={'branch':True,},
    )
    yield cov.all() # create task `coverage`
    yield cov.src() # create task `coverage_src`

