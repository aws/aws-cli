import io

import jmespath
from botocore.paginate import PageIterator

from awscli.formatter import TextFormatter


class FakePageIterator(PageIterator):
    # We intentionally don't call the parent constructor; this object is only
    # used to satisfy `isinstance(response, PageIterator)` and provide a stable
    # `build_full_result()` for the formatter.
    def __init__(self, full_result):
        self._full_result = full_result

    def build_full_result(self):
        return self._full_result


class Args:
    def __init__(self, query):
        self.query = query


def test_text_formatter_buffers_paginated_response_when_query_is_set():
    # Regression for aws/aws-cli#10061:
    # when a response is paginated, text output previously applied the query
    # per-page. If later pages didn't include the queried scalar field, the
    # formatter could emit an extra trailing "None" line.
    args = Args(query=jmespath.compile('ChangeSetId'))
    formatter = TextFormatter(args)

    response = FakePageIterator(
        {
            'ResponseMetadata': {'RequestId': 'abc'},
            'ChangeSetId': 'arn:aws:cloudformation:us-east-1:000000000000:changeSet/change-set-1/11111111111111111111111111',
            'NextToken': None,
        }
    )

    stream = io.StringIO()
    formatter('cloudformation describe-change-set', response, stream=stream)

    assert stream.getvalue().strip() == response._full_result['ChangeSetId']
