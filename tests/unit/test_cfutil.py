# This one should go into botocore/tests/unit/test_utils.py
from datetime import datetime
from dateutil.tz import tzutc

from awscli.customizations.cfutils import datetime2epoch


def test_datetime2epoch_naive():
    assert datetime2epoch(datetime(1970, 1, 2))==86400

def test_datetime2epoch_aware():
    assert datetime2epoch(datetime(1970, 1, 2, tzinfo=tzutc()))==86400
