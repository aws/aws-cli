# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os

from prompt_toolkit.completion import Completion

from awscli.testutils import unittest, mock
from awscli.autocomplete import completer, parser
from awscli.autocomplete.local import basic
from awscli.autocomplete.completer import CompletionResult

from tests.unit.autocomplete import InMemoryIndex


class TestAutoCompleter(unittest.TestCase):
    def setUp(self):
        self.parser = mock.Mock(spec=parser.CLIParser)
        self.parsed_result = parser.ParsedResult()
        self.parser.parse.return_value = self.parsed_result

    def test_delegates_to_autocompleters(self):
        mock_complete = mock.Mock(spec=completer.BaseCompleter)
        expected = [
            CompletionResult('ec2', -1),
            CompletionResult('ecs', -1)
        ]
        mock_complete.complete.return_value = expected
        auto_complete = completer.AutoCompleter(
            self.parser, completers=[mock_complete])

        results = auto_complete.autocomplete('aws e')
        self.assertEqual(results, expected)
        self.parser.parse.assert_called_with('aws e', None)
        mock_complete.complete.assert_called_with(self.parsed_result)

    def test_stops_processing_when_list_returned(self):
        first = mock.Mock(spec=completer.BaseCompleter)
        second = mock.Mock(spec=completer.BaseCompleter)

        first.complete.return_value = None
        expected = [
            CompletionResult('ec2', -1),
            CompletionResult('ecs', -1)
        ]
        second.complete.return_value = expected

        auto_complete = completer.AutoCompleter(
            self.parser, completers=[first, second])
        self.assertEqual(auto_complete.autocomplete('aws e'), expected)

        first.complete.assert_called_with(self.parsed_result)
        second.complete.assert_called_with(self.parsed_result)

    def test_returns_empty_list_if_no_completers_have_results(self):
        first = mock.Mock(spec=completer.BaseCompleter)
        second = mock.Mock(spec=completer.BaseCompleter)

        first.complete.return_value = None
        second.complete.return_value = None

        auto_complete = completer.AutoCompleter(
            self.parser, completers=[first, second])
        self.assertEqual(auto_complete.autocomplete('aws e'), [])

        first.complete.assert_called_with(self.parsed_result)
        second.complete.assert_called_with(self.parsed_result)

    def test_first_result_wins(self):
        first = mock.Mock(spec=completer.BaseCompleter)
        second = mock.Mock(spec=completer.BaseCompleter)

        first.complete.return_value = [CompletionResult('ec2', -1)]
        second.complete.return_value = [CompletionResult('ecs', -1)]

        auto_complete = completer.AutoCompleter(
            self.parser, completers=[first, second])
        self.assertEqual(
            auto_complete.autocomplete('aws e'),
            [CompletionResult('ec2', -1)]
        )

        first.complete.assert_called_with(self.parsed_result)
        self.assertFalse(second.complete.called)

    def test_strip_html_tags_and_newlines(self):
        STARTING_TOKEN_HELP = """
<p>A token to specify where to start paginating.  This is the
<code>NextToken</code> from a previously truncated response.</p>
"""
        help_text = basic.strip_html_tags_and_newlines(STARTING_TOKEN_HELP)
        self.assertEqual(
            help_text,
            'A token to specify where to start paginating.  This is the'
            'NextToken from a previously truncated response.'
        )


class TestModelIndexCompleter(unittest.TestCase):
    def setUp(self):
        self.index = InMemoryIndex({
            'command_names': {
                '': [('aws', None)],
                'aws': [('ec2', 'Amazon Elastic Compute Cloud'),
                        ('ecs', 'Amazon EC2 Container Registry'),
                        ('s3', 'Amazon Simple Storage Service'),
                        ('s3api', 'Amazon Simple Storage Service')],
                'aws.ec2': [('describe-instances', None)],
                'aws.s3api': [('get-object', None)],
            },
            'arg_names': {
                '': {
                    'aws': ['region', 'endpoint-url'],
                },
                'aws.ec2': {
                    'describe-instances': [
                        'instance-ids', 'reserve', 'positional'],
                },
                'aws.s3api': {
                    'get-object': ['outfile', 'bucket', 'key'],
                },
            },
            'arg_data': {
                '': {
                    'aws': {
                        'endpoint-url': ('endpoint-url', 'string', 'aws', '',
                                         None, False, False),
                        'region': ('region', 'string', 'aws', '', None, False,
                                   False),
                    }
                },
                'aws.ec2': {
                    'describe-instances': {
                        'instance-ids': (
                            'instance-ids', 'string', 'describe-instances',
                            'aws.ec2.', None, False, False),
                        'reserve': (
                            'reserve', 'string', 'describe-instances',
                            'aws.ec2.', None, False, False),
                        'positional': (
                            'positional', 'string', 'describe-instances',
                            'aws.ec2.', None, True, False),
                    }
                },
                'aws.s3api': {
                    'get-object': {
                        'outfile': (
                            'outfile', 'string', 'get-object', 'aws.s3api.',
                            None,
                            False, False),
                        'bucket': (
                            'bucket', 'string', 'get-object', 'aws.s3api.',
                            None,
                            False, False),
                        'key': (
                            'key', 'string', 'get-object', 'aws.s3api.', None,
                            False, False),
                    }
                }
            }
        })
        self.parser = parser.CLIParser(self.index)
        self.completer = basic.ModelIndexCompleter(self.index)

    def test_does_not_complete_if_unparsed_items(self):
        parsed = self.parser.parse('aws foo ')
        self.assertIsNone(self.completer.complete(parsed))

    def test_does_complete_if_current_fragment_is_none(self):
        parsed = self.parser.parse('aws')
        self.assertIsNone(self.completer.complete(parsed))

    def test_can_prefix_match_services(self):
        parsed = self.parser.parse('aws e')
        expected = [
            # The -1 is because we need to replace the string starting
            # 1 character back  (the last fragment is the string 'e').
            CompletionResult('ec2', starting_index=-1),
            CompletionResult('ecs', starting_index=-1),
        ]
        self.assertEqual(self.completer.complete(parsed), expected)

    def test_returns_all_results_when_current_fragment_empty(self):
        parsed = self.parser.parse('aws ')
        expected = [
            # The -1 is because we need to replace the string starting
            # 1 character back  (the last fragment is the string 'e').
            CompletionResult('ec2', starting_index=0),
            CompletionResult('ecs', starting_index=0),
            CompletionResult('s3', starting_index=0),
            CompletionResult('s3api', starting_index=0),
        ]
        self.assertEqual(self.completer.complete(parsed), expected)

    def test_can_autocomplete_global_param(self):
        parsed = self.parser.parse('aws --re')
        self.assertEqual(
            self.completer.complete(parsed),
            [CompletionResult('--region', -4)]
        )

    def test_can_autocomplete_dashes(self):
        parsed = self.parser.parse('aws --')
        self.assertTrue(
            len(self.completer.complete(parsed)) > 0
        )

    def test_keep_suggesting_if_there_are_longer_completions(self):
        parsed = self.parser.parse('aws s3')
        self.assertEqual(
            self.completer.complete(parsed),
            [CompletionResult('s3', -2, False, None,
                              'Amazon Simple Storage Service', ),
             CompletionResult('s3api', -2, False, None,
                              'Amazon Simple Storage Service', )]
        )

    def test_retain_option_order_on_dashes(self):
        parsed = self.parser.parse('aws ec2 describe-instances --region '
                                   'us-west-2 --')
        self.assertEqual(
            self.completer.complete(parsed),
            [CompletionResult('--instance-ids', -2, False, 'string',),
             CompletionResult('--reserve', -2, False, 'string',),
             CompletionResult('--endpoint-url', -2, False, 'string',)]
        )

    def test_can_combine_global_and_command_params(self):
        parsed = self.parser.parse('aws ec2 describe-instances --r')
        self.assertEqual(
            self.completer.complete(parsed),
            [CompletionResult('--reserve', -3, False, 'string', ),
             CompletionResult('--region', -3, False, 'string', )]
        )

    def test_not_suggest_entered_options(self):
        parsed = self.parser.parse('aws ec2 describe-instances '
                                   '--region us-west-2 --re')
        self.assertEqual(
            self.completer.complete(parsed),
            [CompletionResult('--reserve', -4, False, 'string', )]
        )

    def test_no_autocompletions_if_nothing_matches(self):
        parsed = self.parser.parse('aws --foo')
        self.assertEqual(self.completer.complete(parsed), [])

    def test_no_complete_positional_arguments(self):
        parsed = self.parser.parse('aws ec2 describe-instances --pos')
        self.assertEqual(self.completer.complete(parsed), [])

    def test_get_documentation_if_fetcher_provided(self):
        fake_cli_fetcher = mock.Mock()
        fake_cli_fetcher.get_argument_documentation.\
            return_value = '<p>Arg doc</p>'
        fake_cli_fetcher.get_global_arg_documentation\
            .return_value = '<p>Global arg doc</p>'
        completer = basic.ModelIndexCompleter(self.index, fake_cli_fetcher)
        parsed = self.parser.parse('aws ec2 describe-instances --r')
        self.assertEqual(
            completer.complete(parsed),
            [CompletionResult('--reserve', -3, False, 'string', 'Arg doc'),
             CompletionResult('--region', -3, False, 'string', 'Global arg doc')]
        )

    def test_return_service_full_name(self):
        parsed = self.parser.parse('aws ec')
        self.assertEqual(
            self.completer.complete(parsed),
            [CompletionResult('ec2', -2, False, None,
                              'Amazon Elastic Compute Cloud', None),
             CompletionResult('ecs', -2, False, None,
                              'Amazon EC2 Container Registry', None)]
        )

    def test_can_handle_outfile(self):
        parsed = self.parser.parse('aws s3api get-object filename ')
        self.assertEqual(
            self.completer.complete(parsed),
            [CompletionResult('--bucket', 0, False, 'string', None, None),
             CompletionResult('--key', 0, False, 'string', None, None),
             CompletionResult('--endpoint-url', 0, False, 'string', None, None),
             CompletionResult('--region', 0, False, 'string', None, None)]
        )

    def test_can_handle_outfile_with_options(self):
        parsed = self.parser.parse('aws s3api get-object --bucket foo '
                                   'filename --region us-west-2 ')
        self.assertEqual(
            self.completer.complete(parsed),
            [CompletionResult('--key', 0, False, 'string', None, None),
             CompletionResult('--endpoint-url', 0, False, 'string', None, None)]
        )

    def test_can_suggest_outfile(self):
        parsed = self.parser.parse('aws s3api get-object --bucket foo '
                                   '--key bar --region us-west-2 ')
        self.assertEqual(
            self.completer.complete(parsed),
            [CompletionResult('outfile', 0, False, 'string',
                              None, 'outfile (required)'),
             CompletionResult('--endpoint-url', 0, False, 'string', None, None)]
        )


class TestRegionCompleter(unittest.TestCase):
    def setUp(self):
        self.index = InMemoryIndex({
            'command_names': {
                '': ['aws'],
                'aws': []
            },
            'arg_names': {
                '': {'aws': ['region']}
            },
            'arg_data': {
                '': {
                    'aws': {
                        'region': ('region', 'string', 'aws', '', None, False,
                                   False),
                    }
                }
            }
        })
        self.parser = parser.CLIParser(self.index)
        self.completer = basic.RegionCompleter()

    def test_return_none_if_it_is_not_region_option(self):
        parsed = self.parser.parse('aws --foo')
        self.assertIsNone(self.completer.complete(parsed))

    def test_no_autocompletions_if_nothing_matches(self):
        parsed = self.parser.parse('aws --region foo')
        self.assertEqual(list(self.completer.complete(parsed)), [])

    def test_autocompletes_if_matches(self):
        parsed = self.parser.parse('aws --region us-west-')
        self.assertEqual(list(self.completer.complete(parsed)),
                         [CompletionResult('us-west-1', 0, False),
                          CompletionResult('us-west-2', 0, False)])

    def test_not_autocomplete_wo_trailing_space(self):
        parsed = self.parser.parse('aws --region')
        self.assertIsNone(self.completer.complete(parsed))

    def test_autocomplete_with_trailing_space(self):
        parsed = self.parser.parse('aws --region ')
        self.assertIsNotNone(self.completer.complete(parsed))


class TestProfileCompleter(unittest.TestCase):
    def setUp(self):
        self.index = InMemoryIndex({
            'command_names': {
                '': ['aws'],
                'aws': []
            },
            'arg_names': {
                '': {'aws': ['profile']}
            },
            'arg_data': {
                '': {
                    'aws': {
                        'profile': ('profile', 'string', 'aws', '', None, False,
                                   False),
                    }
                }
            }
        })
        fake_session = mock.Mock()
        fake_session.available_profiles = ['default', 'profile1', 'profile2']
        self.parser = parser.CLIParser(self.index)
        self.completer = basic.ProfileCompleter(session=fake_session)

    def test_return_none_if_it_is_not_profile_option(self):
        parsed = self.parser.parse('aws --foo')
        self.assertIsNone(self.completer.complete(parsed))

    def test_no_autocompletions_if_nothing_matches(self):
        parsed = self.parser.parse('aws --profile foo')
        self.assertEqual(list(self.completer.complete(parsed)), [])

    def test_not_autocomplete_wo_trailing_space(self):
        parsed = self.parser.parse('aws --profile')
        self.assertIsNone(self.completer.complete(parsed))

    def test_autocomplete_with_trailing_space(self):
        parsed = self.parser.parse('aws --profile ')
        self.assertIsNotNone(self.completer.complete(parsed))

    def test_autocompletes_if_matches(self):
        parsed = self.parser.parse('aws --profile prof')
        self.assertEqual(list(self.completer.complete(parsed)),
                         [CompletionResult('profile1', 0, False),
                          CompletionResult('profile2', 0, False)])


class TestFilePathCompleter(unittest.TestCase):
    def setUp(self):
        self.index = InMemoryIndex({
            'command_names': {
                '': ['aws'],
                'aws': []
            },
            'arg_names': {
                '': {'aws': ['profile']}
            },
            'arg_data': {
                '': {
                    'aws': {
                        'profile': ('profile', 'string', 'aws', '', None, False,
                                   False),
                    }
                }
            }
        })
        fake_completer = mock.Mock()
        fake_completer.get_completions.return_value = [
            Completion(text='', display=[('', 'file')]),
            Completion(text='', display=[('', 'folder/')])
        ]
        self.parser = parser.CLIParser(self.index)
        self.completer = basic.FilePathCompleter(path_completer=fake_completer)

    def test_return_none_if_it_is_not_file_prefix(self):
        parsed = self.parser.parse('aws --foo')
        self.assertIsNone(self.completer.complete(parsed))

    def test_complete_lonely_tilda_with_slash(self):
        parsed = self.parser.parse('aws --profile file://~')
        self.assertEqual(list(self.completer.complete(parsed)),
                         [CompletionResult('file://~%s' % os.sep, 0, False)])

    def test_complete_pass_correct_prefix(self):
        parsed = self.parser.parse('aws --profile fileb://')
        self.assertEqual(
            list(self.completer.complete(parsed)),
            [CompletionResult('fileb://file', 0, False, None, None, 'file'),
             CompletionResult('fileb://folder/', 0, False, None, None, 'folder/')]
        )
