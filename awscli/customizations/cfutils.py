# This one should go into botocore/utils.py
from datetime import datetime


def datetime2epoch(dt):
    """
    Calculate the POSIX epoch time based on the given datetime instance.

    If the input datetime is naive, it will be treated as UTC time.
    (Note that this is different than the timestamp() behavior in Python3.3+.
    We want unambiguous UTC to avoid test cases failing on different locale.)
    """
    if dt.tzinfo:
        d = dt.replace(tzinfo=None) - dt.utcoffset() - datetime(1970, 1, 1)
    else:
        d = dt - datetime(1970, 1, 1)
    if hasattr(d, "total_seconds"):
        return d.total_seconds()  # Works in Python 2.7+
    return (d.microseconds + (d.seconds + d.days * 24 * 3600) * 10**6) / 10**6
