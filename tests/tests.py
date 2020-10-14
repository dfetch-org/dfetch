""" python tests main entry point, automatically finds test cases to run

@author: GlennVL
"""
from unittest import TestLoader
from xmlrunner import XMLTestRunner


def suite():
    """"
    Make an auto-discovery test loader.
    The default pattern makes the auto-discovery case
    sensitive on case sensitive filesystems (Linux)
    """
    return TestLoader().discover('.', pattern='[tT]est*.py')


def run(test, report):
    """ start html test runner with auto discovered test cases """
    with open(report, 'wb') as file:
        XMLTestRunner(output=file, verbosity=2).run(test)


if __name__ == '__main__':
    run(suite(), 'test_report.xml')
