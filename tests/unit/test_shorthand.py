# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from awscli import shorthand
from nose.tools import assert_equal


def test_parse():
    # Key val pairs with scalar value.
    yield (_can_parse, 'foo=bar', {'foo': 'bar'})
    yield (_can_parse, 'foo=bar', {'foo': 'bar'})
    yield (_can_parse, 'foo=bar,baz=qux', {'foo': 'bar', 'baz': 'qux'})
    yield (_can_parse, 'a=b,c=d,e=f', {'a': 'b', 'c': 'd', 'e': 'f'})
    # Empty values are allowed.
    yield (_can_parse, 'foo=', {'foo': None})
    yield (_can_parse, 'foo=,bar=', {'foo': None, 'bar': None})
    # Unicode is allowed.
    yield (_can_parse, u'foo=\u2713', {'foo': u'\u2713'})
    yield (_can_parse, u'foo=\u2713,\u2713', {'foo': [u'\u2713', u'\u2713']})
    # Key val pairs with csv values.
    yield (_can_parse, 'foo=a,b', {'foo': ['a', 'b']})
    yield (_can_parse, 'foo=a,b,c', {'foo': ['a', 'b', 'c']})
    yield (_can_parse, 'foo=a,b,bar=c,d', {'foo': ['a', 'b'],
                                           'bar': ['c', 'd']})
    yield (_can_parse, 'foo=a,b,c,bar=d,e,f',
           {'foo': ['a', 'b', 'c'], 'bar': ['d', 'e', 'f']})

    # Explicit lists.
    yield (_can_parse, 'foo=[]', {'foo': []})
    yield (_can_parse, 'foo=[a]', {'foo': ['a']})
    yield (_can_parse, 'foo=[a,b]', {'foo': ['a', 'b']})
    yield (_can_parse, 'foo=[a,b,c]', {'foo': ['a', 'b', 'c']})
    yield (_can_parse, 'foo=[a,b],bar=c,d',
           {'foo': ['a', 'b'], 'bar': ['c', 'd']})
    yield (_can_parse, 'foo=[a,b],bar=[c,d]',
           {'foo': ['a', 'b'], 'bar': ['c', 'd']})
    yield (_can_parse, 'foo=a,b,bar=[c,d]',
           {'foo': ['a', 'b'], 'bar': ['c', 'd']})
    yield (_can_parse, 'foo=[a=b,c=d]', {'foo': ['a=b', 'c=d']})
    yield (_can_parse, 'foo=[a=b,c=d]', {'foo': ['a=b', 'c=d']})
    # Lists with whitespace.
    yield (_can_parse, 'foo=[ a , b  , c  ]',
           {'foo': ['a', 'b', 'c']})
    yield (_can_parse, 'foo  =  [ a , b  , c  ]',
           {'foo': ['a', 'b', 'c']})

    # Single quoted strings.
    yield (_can_parse, "foo='bar'", {"foo": "bar"})
    yield (_can_parse, "foo='bar,baz'", {"foo": "bar,baz"})
    # Single quoted strings for each value in a CSV list.
    yield (_can_parse, "foo='bar','baz'", {"foo": ['bar', 'baz']})
    # Can mix single quoted and non quoted values.
    yield (_can_parse, "foo=bar,'baz'", {"foo": ['bar', 'baz']})
    # Quoted strings can include chars not allowed in unquoted strings.
    yield (_can_parse, "foo=bar,'baz=qux'", {"foo": ['bar', 'baz=qux']})
    yield (_can_parse, "foo=bar,'--option=bar space'",
           {"foo": ['bar', '--option=bar space']})
    # Can escape the single quote.
    yield (_can_parse, "foo='bar\\'baz'", {"foo": "bar'baz"})
    yield (_can_parse, "foo='bar\\\\baz'", {"foo": "bar\\baz"})

    # Double quoted strings.
    yield (_can_parse, 'foo="bar"', {'foo': 'bar'})
    yield (_can_parse, 'foo="bar,baz"', {'foo': 'bar,baz'})
    yield (_can_parse, 'foo="bar","baz"', {'foo': ['bar', 'baz']})
    yield (_can_parse, 'foo=bar,"baz=qux"', {'foo': ['bar', 'baz=qux']})
    yield (_can_parse, 'foo=bar,"--option=bar space"',
           {'foo': ['bar', '--option=bar space']})
    yield (_can_parse, 'foo="bar\\"baz"', {'foo': 'bar"baz'})
    yield (_can_parse, 'foo="bar\\\\baz"', {'foo': 'bar\\baz'})

    # Ignores whitespace around '=' and ','
    yield (_can_parse, 'foo= bar', {'foo': 'bar'})
    yield (_can_parse, 'foo =bar', {'foo': 'bar'})
    yield (_can_parse, 'foo = bar', {'foo': 'bar'})
    yield (_can_parse, 'foo  =   bar', {'foo': 'bar'})
    yield (_can_parse, 'foo = bar,baz = qux', {'foo': 'bar', 'baz': 'qux'})
    yield (_can_parse, 'a = b,  c = d , e = f', {'a': 'b', 'c': 'd', 'e': 'f'})
    yield (_can_parse, 'foo = ', {'foo': None})
    yield (_can_parse, 'a=b,c=  d,  e,  f', {'a': 'b', 'c': ['d', 'e', 'f']})
    yield (_can_parse, 'Name=foo,Values=  a  ,  b  ,  c  ',
           {'Name': 'foo', 'Values': ['a', 'b', 'c']})
    yield (_can_parse, 'Name=foo,Values= a,  b  ,  c',
           {'Name': 'foo', 'Values': ['a', 'b', 'c']})


def test_error_parsing():
    yield (_is_error, 'foo')
    # Missing closing quotes
    yield (_is_error, 'foo="bar')
    yield (_is_error, "foo='bar")
    yield (_is_error, "foo=[bar")


def test_regressions():
    return
    with open('/tmp/shorthand') as f:
        for expr in f:
            yield _can_parse, expr.strip().decode('utf-8'), {}


def _is_error(expr):
    try:
        shorthand.ShorthandParser().parse(expr)
    except shorthand.ShorthandParseError:
        #except TypeError:
        # Expected result, test passes.
        pass
    else:
        raise AssertionError("Expected ShorthandParseError, but no "
                            "exception was raised for expression: %s" % expr)

def _can_parse(data, expected):
    actual = shorthand.ShorthandParser().parse(data)
    assert_equal(actual, expected)
