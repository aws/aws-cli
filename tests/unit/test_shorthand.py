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
from unittest.mock import patch

import pytest
import signal

import awscli.paramfile
from awscli import shorthand
from awscli.testutils import skip_if_windows, unittest

from botocore import model

PARSING_TEST_CASES = (
    # Key val pairs with scalar value.
    ('foo=bar', {'foo': 'bar'}),
    ('foo=bar', {'foo': 'bar'}),
    ('foo=bar,baz=qux', {'foo': 'bar', 'baz': 'qux'}),
    ('a=b,c=d,e=f', {'a': 'b', 'c': 'd', 'e': 'f'}),
    # Empty values are allowed.
    ('foo=', {'foo': ''}),
    ('foo=,bar=', {'foo': '', 'bar': ''}),
    # Unicode is allowed.
    (u'foo=\u2713', {'foo': u'\u2713'}),
    (u'foo=\u2713,\u2713', {'foo': [u'\u2713', u'\u2713']}),
    # Key val pairs with csv values.
    ('foo=a,b', {'foo': ['a', 'b']}),
    ('foo=a,b,c', {'foo': ['a', 'b', 'c']}),
    ('foo=a,b,bar=c,d', {'foo': ['a', 'b'], 'bar': ['c', 'd']}),
    ('foo=a,b,c,bar=d,e,f', {'foo': ['a', 'b', 'c'], 'bar': ['d', 'e', 'f']}),
    # Spaces in values are allowed.
    ('foo=a,b=with space', {'foo': 'a', 'b': 'with space'}),
    # Trailing spaces are still ignored.
    ('foo=a,b=with trailing space  ', {'foo': 'a', 'b': 'with trailing space'}),
    ('foo=first space', {'foo': 'first space'}),
    (
        'foo=a space,bar=a space,baz=a space',
        {'foo': 'a space', 'bar': 'a space', 'baz': 'a space'}
    ),
    # Dashes are allowed in key names.
    ('with-dash=bar', {'with-dash': 'bar'}),
    # Underscore are also allowed.
    ('with_underscore=bar', {'with_underscore': 'bar'}),
    # Dots are allowed.
    ('with.dot=bar', {'with.dot': 'bar'}),
    # Pound signs are allowed.
    ('#key=value', {'#key': 'value'}),
    # Forward slashes are allowed in keys.
    ('some/thing=value', {'some/thing': 'value'}),
    # Colon chars are allowed in keys:
    ('aws:service:region:124:foo/bar=baz', {'aws:service:region:124:foo/bar': 'baz'}),
    # Explicit lists.
    ('foo=[]', {'foo': []}),
    ('foo=[a]', {'foo': ['a']}),
    ('foo=[a,b]', {'foo': ['a', 'b']}),
    ('foo=[a,b,c]', {'foo': ['a', 'b', 'c']}),
    ('foo=[a,b],bar=c,d', {'foo': ['a', 'b'], 'bar': ['c', 'd']}),
    ('foo=[a,b],bar=[c,d]', {'foo': ['a', 'b'], 'bar': ['c', 'd']}),
    ('foo=a,b,bar=[c,d]', {'foo': ['a', 'b'], 'bar': ['c', 'd']}),
    ('foo=[a=b,c=d]', {'foo': ['a=b', 'c=d']}),
    ('foo=[a=b,c=d]', {'foo': ['a=b', 'c=d']}),
    # Lists with whitespace.
    ('foo=[ a , b  , c  ]', {'foo': ['a', 'b', 'c']}),
    ('foo  =  [ a , b  , c  ]', {'foo': ['a', 'b', 'c']}),
    ('foo=[,,]', {'foo': ['', '']}),
    # Single quoted strings.
    ("foo='bar'", {"foo": "bar"}),
    ("foo='bar,baz'", {"foo": "bar,baz"}),
    # Single quoted strings for each value in a CSV list.
    ("foo='bar','baz'", {"foo": ['bar', 'baz']}),
    # Can mix single quoted and non quoted values.
    ("foo=bar,'baz'", {"foo": ['bar', 'baz']}),
    # Quoted strings can include chars not allowed in unquoted strings.
    ("foo=bar,'baz=qux'", {"foo": ['bar', 'baz=qux']}),
    ("foo=bar,'--option=bar space'", {"foo": ['bar', '--option=bar space']}),
    # Can escape the single quote.
    ("foo='bar\\'baz'", {"foo": "bar'baz"}),
    ("foo='bar\\\\baz'", {"foo": "bar\\baz"}),
    # Double quoted strings.
    ('foo="bar"', {'foo': 'bar'}),
    ('foo="bar,baz"', {'foo': 'bar,baz'}),
    ('foo="bar","baz"', {'foo': ['bar', 'baz']}),
    ('foo=bar,"baz=qux"', {'foo': ['bar', 'baz=qux']}),
    ('foo=bar,"--option=bar space"', {'foo': ['bar', '--option=bar space']}),
    ('foo="bar\\"baz"', {'foo': 'bar"baz'}),
    ('foo="bar\\\\baz"', {'foo': 'bar\\baz'}),
    # Can escape comma in CSV list.
    ('foo=a\\,b', {"foo": "a,b"}),
    ('foo=a\\,b', {"foo": "a,b"}),
    ('foo=a\\,', {"foo": "a,"}),
    ('foo=\\,', {"foo": ","}),
    ('foo=a,b\\,c', {"foo": ['a', 'b,c']}),
    ('foo=a,b\\,', {"foo": ['a', 'b,']}),
    ('foo=a,\\,bc', {"foo": ['a', ',bc']}),
    # Ignores whitespace around '=' and ','
    ('foo= bar', {'foo': 'bar'}),
    ('foo =bar', {'foo': 'bar'}),
    ('foo = bar', {'foo': 'bar'}),
    ('foo  =   bar', {'foo': 'bar'}),
    ('foo = bar,baz = qux', {'foo': 'bar', 'baz': 'qux'}),
    ('a = b,  c = d , e = f', {'a': 'b', 'c': 'd', 'e': 'f'}),
    ('foo = ', {'foo': ''}),
    ('a=b,c=  d,  e,  f', {'a': 'b', 'c': ['d', 'e', 'f']}),
    ('Name=foo,Values=  a  ,  b  ,  c  ', {'Name': 'foo', 'Values': ['a', 'b', 'c']}),
    ('Name=foo,Values= a,  b  ,  c', {'Name': 'foo', 'Values': ['a', 'b', 'c']}),
    # Can handle newlines between values.
    ('Name=foo,\nValues=a,b,c', {'Name': 'foo', 'Values': ['a', 'b', 'c']}),
    ('A=b,\nC=d,\nE=f\n', {'A': 'b', 'C': 'd', 'E': 'f'}),
    # Hashes
    ('Name={foo=bar,baz=qux}', {'Name': {'foo': 'bar', 'baz': 'qux'}}),
    ('Name={foo=[a,b,c],bar=baz}', {'Name': {'foo': ['a', 'b', 'c'], 'bar': 'baz'}}),
    ('Name={foo=bar},Bar=baz', {'Name': {'foo': 'bar'}, 'Bar': 'baz'}),
    ('Bar=baz,Name={foo=bar}', {'Bar': 'baz', 'Name': {'foo': 'bar'}}),
    ('a={b={c=d}}', {'a': {'b': {'c': 'd'}}}),
    ('a={b={c=d,e=f},g=h}', {'a': {'b': {'c': 'd', 'e': 'f'}, 'g': 'h'}}),
    # Combining lists and hashes.
    ('Name=[{foo=bar}, {baz=qux}]', {'Name': [{'foo': 'bar'}, {'baz': 'qux'}]}),
    # Combining hashes and lists.
    (
        'Name=[{foo=[a,b]}, {bar=[c,d]}]',
        {'Name': [{'foo': ['a', 'b']}, {'bar': ['c', 'd']}]}
    ),
    # key-value pairs using @= syntax
    ('foo@=bar', {'foo': 'bar'}),
    ('foo@=bar,baz@=qux', {'foo': 'bar', 'baz': 'qux'}),
    ('foo@=,bar@=', {'foo': '', 'bar': ''}),
    (u'foo@=\u2713,\u2713', {'foo': [u'\u2713', u'\u2713']}),
    ('foo@=a,b,bar=c,d', {'foo': ['a', 'b'], 'bar': ['c', 'd']}),
    ('foo=a,b@=with space', {'foo': 'a', 'b': 'with space'}),
    ('foo=a,b@=with trailing space  ', {'foo': 'a', 'b': 'with trailing space'}),
    ('aws:service:region:124:foo/bar@=baz', {'aws:service:region:124:foo/bar': 'baz'}),
    ('foo=[a,b],bar@=[c,d]', {'foo': ['a', 'b'], 'bar': ['c', 'd']}),
    ('foo  @=  [ a , b  , c  ]', {'foo': ['a', 'b', 'c']}),
    ('A=b,\nC@=d,\nE@=f\n', {'A': 'b', 'C': 'd', 'E': 'f'}),
    ('Bar@=baz,Name={foo@=bar}', {'Bar': 'baz', 'Name': {'foo': 'bar'}}),
    ('Name=[{foo@=bar}, {baz=qux}]', {'Name': [{'foo': 'bar'}, {'baz': 'qux'}]}),
    (
        'Name=[{foo@=[a,b]}, {bar=[c,d]}]',
        {'Name': [{'foo': ['a', 'b']}, {'bar': ['c', 'd']}]}
    ),
)


@pytest.mark.parametrize(
    "expr", (
        'foo',
        # Missing closing quotes
        'foo="bar',
        '"foo=bar',
        "foo='bar",
        "foo=[bar",
        "foo={bar",
        "foo={bar}",
        "foo={bar=bar",
        "foo=bar,",
        "foo==bar,\nbar=baz",
        # Duplicate keys should error otherwise they silently
        # set only one of the values.
        'foo=bar,foo=qux'
    )
)
def test_error_parsing(expr):
    with pytest.raises(shorthand.ShorthandParseError):
        shorthand.ShorthandParser().parse(expr)


@pytest.mark.parametrize(
    "expr", (
        # starting with " but unclosed, then repeated \
        f'foo="' + '\\' * 100,
        # starting with ' but unclosed, then repeated \
        f'foo=\'' + '\\' * 100,
    )
)
@skip_if_windows("Windows does not support signal.SIGALRM.")
def test_error_with_backtracking(expr):
    signal.signal(signal.SIGALRM, handle_timeout)
    # Ensure we don't spend more than 5 seconds backtracking
    signal.alarm(5)
    with pytest.raises(shorthand.ShorthandParseError):
        shorthand.ShorthandParser().parse(expr)
    signal.alarm(0)


def handle_timeout(signum, frame):
    raise TimeoutError('Shorthand parsing timed out')

@pytest.mark.parametrize(
    'data, expected',
    PARSING_TEST_CASES
)
def test_parse(data, expected):
    actual = shorthand.ShorthandParser().parse(data)
    assert actual == expected

class TestShorthandParserParamFile:
    @patch('awscli.paramfile.compat_open')
    @pytest.mark.parametrize(
        'file_contents, data, expected',
        (
            ('file-contents123', 'Foo@=file://foo,Bar={Baz@=file://foo}', {'Foo': 'file-contents123', 'Bar': {'Baz': 'file-contents123'}}),
            (b'file-contents123', 'Foo@=fileb://foo,Bar={Baz@=fileb://foo}', {'Foo': b'file-contents123', 'Bar': {'Baz': b'file-contents123'}}),
            ('file-contents123', 'Bar@={Baz=file://foo}', {'Bar': {'Baz': 'file://foo'}}),
            ('file-contents123', 'Foo@=foo,Bar={Baz@=foo}', {'Foo': 'foo', 'Bar': {'Baz': 'foo'}})
        )
    )
    def test_paramfile(self, mock_compat_open, file_contents, data, expected):
        mock_compat_open.return_value.__enter__.return_value.read.return_value = file_contents
        result = shorthand.ShorthandParser().parse(data)
        assert result == expected

    @patch('awscli.paramfile.compat_open')
    def test_paramfile_list(self, mock_compat_open):
        f1_contents = 'file-contents123'
        f2_contents = 'contents2'
        mock_compat_open.return_value.__enter__.return_value.read.side_effect = [f1_contents, f2_contents]
        result = shorthand.ShorthandParser().parse(
            f'Foo@=[a, file://foo1, file://foo2]'
        )
        assert result == {'Foo': ['a', f1_contents, f2_contents]}

    def test_paramfile_does_not_exist_error(self, capsys):
        with pytest.raises(awscli.paramfile.ResourceLoadingError):
            shorthand.ShorthandParser().parse('Foo@=file://fakefile.txt')
            captured = capsys.readouterr()
            assert "No such file or directory: 'fakefile.txt" in captured.err


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

    def test_can_convert_list_of_integers(self):
        m = model.DenormalizedStructureBuilder().with_members({
            'A': {
                'type': 'list',
                'member': {
                    'type': 'integer',
                },
            },
        }).build_model()
        b = shorthand.BackCompatVisitor()
        params = {'A': ['1', '2']}
        b.visit(params, m)
        # We should have converted each list element to an integer
        # because the type of the list member is integer.
        self.assertEqual(params, {'A': [1, 2]})
