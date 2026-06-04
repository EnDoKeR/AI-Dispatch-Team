from app import active
from tests import helper_only


def fixture_assertion():
    assert active.VALUE
    assert helper_only.VALUE
