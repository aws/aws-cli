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
from awscli.testutils import unittest

from botocore import model

from nose.tools import assert_equal


def test_parse():
    # Key val pairs with scalar value.
    yield (_can_parse, 'foo=bar', {'foo': 'bar'})
    yield (_can_parse, 'foo=bar', {'foo': 'bar'})
    yield (_can_parse, 'foo=bar,baz=qux', {'foo': 'bar', 'baz': 'qux'})
    yield (_can_parse, 'a=b,c=d,e=f', {'a': 'b', 'c': 'd', 'e': 'f'})
    # Empty values are allowed.
    yield (_can_parse, 'foo=', {'foo': ''})
    yield (_can_parse, 'foo=,bar=', {'foo': '', 'bar': ''})
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
    # Spaces in values are allowed.
    yield (_can_parse, 'foo=a,b=with space', {'foo': 'a', 'b': 'with space'})
    # Trailing spaces are still ignored.
    yield (_can_parse, 'foo=a,b=with trailing space  ',
           {'foo': 'a', 'b': 'with trailing space'})
    yield (_can_parse, 'foo=first space',
           {'foo': 'first space'})
    yield (_can_parse, 'foo=a space,bar=a space,baz=a space',
           {'foo': 'a space', 'bar': 'a space', 'baz': 'a space'})

    # Dashes are allowed in key names.
    yield (_can_parse, 'with-dash=bar', {'with-dash': 'bar'})

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
    yield (_can_parse, 'foo=[,,]', {'foo': ['', '']})

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

    # Can escape comma in CSV list.
    yield (_can_parse, 'foo=a\\,b', {"foo": "a,b"})
    yield (_can_parse, 'foo=a\\,b', {"foo": "a,b"})
    yield (_can_parse, 'foo=a\\,', {"foo": "a,"})
    yield (_can_parse, 'foo=\\,', {"foo": ","})
    yield (_can_parse, 'foo=a,b\\,c', {"foo": ['a', 'b,c']})
    yield (_can_parse, 'foo=a,b\\,', {"foo": ['a', 'b,']})
    yield (_can_parse, 'foo=a,\\,bc', {"foo": ['a', ',bc']})

    # Ignores whitespace around '=' and ','
    yield (_can_parse, 'foo= bar', {'foo': 'bar'})
    yield (_can_parse, 'foo =bar', {'foo': 'bar'})
    yield (_can_parse, 'foo = bar', {'foo': 'bar'})
    yield (_can_parse, 'foo  =   bar', {'foo': 'bar'})
    yield (_can_parse, 'foo = bar,baz = qux', {'foo': 'bar', 'baz': 'qux'})
    yield (_can_parse, 'a = b,  c = d , e = f', {'a': 'b', 'c': 'd', 'e': 'f'})
    yield (_can_parse, 'foo = ', {'foo': ''})
    yield (_can_parse, 'a=b,c=  d,  e,  f', {'a': 'b', 'c': ['d', 'e', 'f']})
    yield (_can_parse, 'Name=foo,Values=  a  ,  b  ,  c  ',
           {'Name': 'foo', 'Values': ['a', 'b', 'c']})
    yield (_can_parse, 'Name=foo,Values= a,  b  ,  c',
           {'Name': 'foo', 'Values': ['a', 'b', 'c']})

    # Can handle newlines between values.
    yield (_can_parse, 'Name=foo,\nValues=a,b,c',
           {'Name': 'foo', 'Values': ['a', 'b', 'c']})
    yield (_can_parse, 'A=b,\nC=d,\nE=f\n',
           {'A': 'b', 'C': 'd', 'E': 'f'})

    # Hashes
    yield (_can_parse, 'Name={foo=bar,baz=qux}',
           {'Name': {'foo': 'bar', 'baz': 'qux'}})
    yield (_can_parse, 'Name={foo=[a,b,c],bar=baz}',
           {'Name': {'foo': ['a', 'b', 'c'], 'bar': 'baz'}})
    yield (_can_parse, 'Name={foo=bar},Bar=baz',
           {'Name': {'foo': 'bar'}, 'Bar': 'baz'})
    yield (_can_parse, 'Bar=baz,Name={foo=bar}',
           {'Bar': 'baz', 'Name': {'foo': 'bar'}})
    yield (_can_parse, 'a={b={c=d}}',
           {'a': {'b': {'c': 'd'}}})
    yield (_can_parse, 'a={b={c=d,e=f},g=h}',
           {'a': {'b': {'c': 'd', 'e': 'f'}, 'g': 'h'}})

    # Combining lists and hashes.
    yield (_can_parse, 'Name=[{foo=bar}, {baz=qux}]',
           {'Name': [{'foo': 'bar'}, {'baz': 'qux'}]})

    # Combining hashes and lists.
    yield (_can_parse, 'Name=[{foo=[a,b]}, {bar=[c,d]}]',
           {'Name': [{'foo': ['a', 'b']}, {'bar': ['c', 'd']}]})


def test_error_parsing():
    yield (_is_error, 'foo')
    # Missing closing quotes
    yield (_is_error, 'foo="bar')
    yield (_is_error, "foo='bar")
    yield (_is_error, "foo=[bar")
    yield (_is_error, "foo={bar")
    yield (_is_error, "foo={bar}")
    yield (_is_error, "foo={bar=bar")
    yield (_is_error, "foo=bar,")


def _is_error(expr):
    try:
        shorthand.ShorthandParser().parse(expr)
    except shorthand.ShorthandParseError:
        pass
    except Exception as e:
        raise AssertionError(
            "Expected ShorthandParseError, but received unexpected "
            "exception instead (%s): %s" % (e.__class__, e))
    else:
        raise AssertionError("Expected ShorthandParseError, but no "
                            "exception was raised for expression: %s" % expr)

def _can_parse(data, expected):
    actual = shorthand.ShorthandParser().parse(data)
    assert_equal(actual, expected)


class TestModelVisitor(unittest.TestCase):
    def test_promote_to_list_of_ints(self):
        m = model.DenormalizedStructureBuilder().with_members({
            'A': {
                'type': 'list',
                'member': {'type': 'string'}
            },
        }).build_model()
        b = shorthand.BackCompatVisitor()

        params = {'A': 'foo'}
        b.visit(params, m)
        self.assertEqual(params, {'A': ['foo']})

    def test_dont_promote_list_if_none_value(self):
        m = model.DenormalizedStructureBuilder().with_members({
            'A': {
                'type': 'list',
                'member': {
                    'type': 'structure',
                    'members': {
                        'Single': {'type': 'string'}
                    },
                },
            },
        }).build_model()
        b = shorthand.BackCompatVisitor()
        params = {}
        b.visit(params, m)
        self.assertEqual(params, {})

    def test_can_convert_scalar_types_from_string(self):
        m = model.DenormalizedStructureBuilder().with_members({
            'A': {'type': 'integer'},
            'B': {'type': 'string'},
            'C': {'type': 'float'},
            'D': {'type': 'boolean'},
            'E': {'type': 'boolean'},
        }).build_model()
        b = shorthand.BackCompatVisitor()

        params = {'A': '24', 'B': '24', 'C': '24.12345',
                  'D': 'true', 'E': 'false'}
        b.visit(params, m)
        self.assertEqual(
            params,
            {'A': 24, 'B': '24', 'C': float('24.12345'),
             'D': True, 'E': False})

    def test_empty_values_not_added(self):
        m = model.DenormalizedStructureBuilder().with_members({
            'A': {'type': 'boolean'},
        }).build_model()
        b = shorthand.BackCompatVisitor()

        params = {}
        b.visit(params, m)
        self.assertEqual(params, {})
