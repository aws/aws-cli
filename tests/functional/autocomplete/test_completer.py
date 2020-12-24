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

from awscli.testutils import unittest
from awscli.autocomplete import parser, filters
from awscli.autocomplete.local import basic, fetcher
from awscli.clidriver import CLIDriver, create_clidriver
from awscli.autocomplete.completer import CompletionResult

from tests.unit.autocomplete import InMemoryIndex


class TestShorthandCompleter(unittest.TestCase):
    def setUp(self):
        cli_driver = create_clidriver()
        self.cli_fetcher = fetcher.CliDriverFetcher(cli_driver)
        self.index = InMemoryIndex({
            'command_names': {
                '': [('aws', None)],
                'aws': [('codebuild', None),
                        ('dynamodb', None),
                        ('s3', None),
                        ('ec2', None),
                        ('cloudformation', None)],
                'aws.codebuild': [('create-project', None)],
                'aws.dynamodb': [('put-item', None)],
                'aws.ec2': [('bundle-instance', None)],
                'aws.cloudformation': [('deploy', None)],
            },
            'arg_names': {
                '': {
                    'aws': ['region', 'output', 'debug'],
                },
                'aws.codebuild': {
                    'create-project': [
                        'source', 'secondary-sources'],
                },
                'aws.dynamodb': {
                    'put-item': ['item'],
                },
                'aws.ec2': {
                    'bundle-instance': ['storage']
                },
                'aws.cloudformation': {
                    'deploy': ['capabilities']
                }
            },
            'arg_data': {
                '': {
                    'aws': {
                        'region': ('region', 'string', 'aws', '', None, False,
                                   False),
                        'output': ('output', 'string', 'aws', '', None, False,
                                   False),
                        'debug': ('debug', 'string', 'aws', '', None, False,
                                  False),
                    }
                },
                'aws.codebuild': {
                    'create-project': {
                        'source': (
                            'source', 'structure', 'create-project',
                            'aws.codebuild.', None, False, False),
                        'secondary-sources': (
                            'secondary-sources', 'structure', 'create-project',
                            'aws.codebuild.', None, False, False)
                    }
                },
                'aws.dynamodb': {
                    'put-item': {
                        'item': (
                            'item', 'map', 'put-item',
                            'aws.dynamodb.', None, False, False),
                    }
                },
                'aws.ec2': {
                    'bundle-instance': {
                        'storage': (
                            'storage', 'structure', 'bundle-instance',
                            'aws.ec2.', None, False, False),
                    }
                },
                'aws.cloudformation': {
                    'deploy': {
                        'capabilities': (
                            'capabilities', 'list', 'deploy',
                            'aws.cloudformation.', None, False, False),
                    }
                }
            }
        })
        self.parser = parser.CLIParser(self.index)
        self.completer = basic.ShorthandCompleter(self.cli_fetcher)

    def assert_command_generates_suggestions(self, command_line,
                                             expected_suggestions):
        parsed = self.parser.parse(command_line)
        suggestions = self.completer.complete(parsed)
        if expected_suggestions is None:
            self.assertIsNone(suggestions)
        else:
            displayed_suggestions = [x.display_text
                                     for x in suggestions]
            self.assertTrue(all([suggest in expected_suggestions
                                 for suggest in displayed_suggestions]),
                            command_line)
            self.assertEqual(len(expected_suggestions),
                             len(displayed_suggestions), command_line)

    def test_return_none_if_it_does_not_have_shorthand_input(self):
        self.assert_command_generates_suggestions(
            'aws codebuild create-project --region', None)

    def test_return_suggestions_for_codebuild(self):
        self.assert_command_generates_suggestions(
            'aws codebuild create-project --source ',
            expected_suggestions=[
                'type=', 'location=', 'gitCloneDepth=',
                'gitSubmodulesConfig={', 'buildspec=',
                'auth={', 'reportBuildStatus=', 'buildStatusConfig={',
                'insecureSsl=', 'sourceIdentifier='])

        self.assert_command_generates_suggestions(
            'aws codebuild create-project --source foo --secondary-sources ',
            expected_suggestions=[
                'type=', 'location=', 'gitCloneDepth=',
                'gitSubmodulesConfig={', 'buildspec=',
                'auth={', 'reportBuildStatus=', 'buildStatusConfig={',
                'insecureSsl=', 'sourceIdentifier='])

        self.assert_command_generates_suggestions(
            'aws codebuild create-project --source bui',
            expected_suggestions=['buildspec=', 'buildStatusConfig={'])

        self.assert_command_generates_suggestions(
            'aws codebuild create-project --source auth=',
            expected_suggestions=None)

        self.assert_command_generates_suggestions(
            'aws codebuild create-project --source auth={',
            expected_suggestions=['type=', 'resource=', 'Autoclose brackets'])

        self.assert_command_generates_suggestions(
            'aws codebuild create-project --source auth={type=',
            expected_suggestions=['OAUTH', 'Autoclose brackets'])

        self.assert_command_generates_suggestions(
            'aws codebuild create-project '
            '--source auth={type=a},reportBuildStatus=',
            expected_suggestions=['true', 'false'])

        self.assert_command_generates_suggestions(
            'aws codebuild create-project '
            '--source auth={type=a},reportBuildStatus=t',
            expected_suggestions=['true'])

        self.assert_command_generates_suggestions(
            'aws codebuild create-project '
            '--source auth={type=a},reportBuildStatus=q',
            expected_suggestions=None)

        self.assert_command_generates_suggestions(
            'aws codebuild create-project --source auth={type=a},location=',
            expected_suggestions=None)

        self.assert_command_generates_suggestions(
            'aws codebuild create-project '
            '--source auth={type=a},location=foo,ty=',
            expected_suggestions=None)

        self.assert_command_generates_suggestions(
            'aws codebuild create-project '
            '--source auth={type=a},location="foo,ty',
            expected_suggestions=None)

        self.assert_command_generates_suggestions(
            'aws codebuild create-project '
            '--source auth={type=a},location=foo,type=',
            expected_suggestions=[
                'CODECOMMIT', 'CODEPIPELINE', 'GITHUB',
                'S3', 'BITBUCKET', 'GITHUB_ENTERPRISE', 'NO_SOURCE'])

        self.assert_command_generates_suggestions(
            'aws codebuild create-project '
            '--source auth={type=a},location=foo,type=CO',
            expected_suggestions=['CODECOMMIT', 'CODEPIPELINE'])

        self.assert_command_generates_suggestions(
            'aws codebuild create-project --source buildspec=foo,aut',
            expected_suggestions=['auth={'])

    def test_return_suggestions_for_dynamodb(self):
        self.assert_command_generates_suggestions(
            'aws dynamodb put-item --item ',
            expected_suggestions=None)

        self.assert_command_generates_suggestions(
            'aws dynamodb put-item --item key={',
            expected_suggestions=[
                'S=', 'N=', 'B=', 'SS=[', 'NS=[', 'BS=[', 'M={', 'L=[',
                'NULL=', 'BOOL=', 'Autoclose brackets'])

        self.assert_command_generates_suggestions(
            'aws dynamodb put-item --item key={SS',
            expected_suggestions=['SS=[', 'Autoclose brackets'])

        self.assert_command_generates_suggestions(
            'aws dynamodb put-item --item key={M={',
            expected_suggestions=['Autoclose brackets'])

        self.assert_command_generates_suggestions(
            'aws dynamodb put-item --item key={M={key1={',
            expected_suggestions=[
                'S=', 'N=', 'B=', 'SS=[', 'NS=[', 'BS=[', 'M={', 'L=[',
                'NULL=', 'BOOL=', 'Autoclose brackets'])

        self.assert_command_generates_suggestions(
            'aws dynamodb put-item --item key={M={key1={M={key2={',
            expected_suggestions=[
                'S=', 'N=', 'B=', 'SS=[', 'NS=[', 'BS=[', 'M={',
                'L=[', 'NULL=', 'BOOL=', 'Autoclose brackets'])

        self.assert_command_generates_suggestions(
            'aws dynamodb put-item --item key={M={key1={M={key2={B',
            expected_suggestions=['B=', 'BS=[', 'BOOL=', 'Autoclose brackets'])

        self.assert_command_generates_suggestions(
            'aws dynamodb put-item --item key={BS=[1,2',
            expected_suggestions=['Autoclose brackets'])

        self.assert_command_generates_suggestions(
            'aws dynamodb put-item --item key={BS=[1,2],',
            expected_suggestions=[
                'S=', 'N=', 'B=', 'SS=[', 'NS=[', 'M={', 'L=[',
                'NULL=', 'BOOL=', 'Autoclose brackets'])

        self.assert_command_generates_suggestions(
            'aws dynamodb put-item --item key={SS=[]}',
            expected_suggestions=None)

    def test_autoclose_brackets(self):
        parsed = self.parser.parse('aws dynamodb put-item --item '
                                   'key={M={key1={M={key2={BS=[1')
        suggestions = self.completer.complete(parsed)
        self.assertEqual(suggestions[-1].name,
                         'key={M={key1={M={key2={BS=[1]}}}}}')

        parsed = self.parser.parse('aws dynamodb put-item --item '
                                   'key={M=[key1={M=[key2={BS=[1')
        suggestions = self.completer.complete(parsed)
        self.assertEqual(suggestions[-1].name,
                         'key={M=[key1={M=[key2={BS=[1]}]}]}')

    def test_not_start_autocompletion_wo_trailing_space(self):
        parsed = self.parser.parse('aws ec2 bundle-instance --storage')
        suggestions = self.completer.complete(parsed)
        self.assertIsNone(suggestions)

    def test_un_closable_brackets(self):
        parsed = self.parser.parse('aws dynamodb put-item --item '
                                   'key={M={key1={M={key2=]{BS=[1')
        suggestions = self.completer.complete(parsed)
        self.assertIsNone(suggestions)

    def test_fuzzy_search(self):
        self.completer = basic.ShorthandCompleter(
            self.cli_fetcher,
            response_filter=filters.fuzzy_filter
        )
        self.assert_command_generates_suggestions(
            'aws codebuild create-project --source auth={type=a},'
            'location=foo,type=OI',
            ['CODEPIPELINE', 'CODECOMMIT']
        )

    def test_names_with_fuzzy_search(self):
        self.completer = basic.ShorthandCompleter(
            self.cli_fetcher,
            response_filter=filters.fuzzy_filter
        )
        parsed = self.parser.parse(
            'aws codebuild create-project --source buildspec=foo,at')
        suggestions = self.completer.complete(parsed)
        names = [s.name for s in suggestions]
        display_text = [s.display_text for s in suggestions]
        self.assertEqual(names, ['buildspec=foo,location=',
                                 'buildspec=foo,buildStatusConfig={',
                                 'buildspec=foo,reportBuildStatus=',
                                 'buildspec=foo,auth={'])
        self.assertEqual(display_text,
                         ['location=',
                          'buildStatusConfig={',
                          'reportBuildStatus=',
                          'auth={'])

    def test_names_with_startswith_search(self):
        self.completer = basic.ShorthandCompleter(
            self.cli_fetcher,
            response_filter=filters.startswith_filter
        )
        parsed = self.parser.parse(
            'aws codebuild create-project --source auth={},bui')
        suggestions = self.completer.complete(parsed)
        names = [s.name for s in suggestions]
        display_text = [s.display_text for s in suggestions]
        self.assertEqual(names, ['auth={},buildspec=',
                                 'auth={},buildStatusConfig={'])
        self.assertEqual(display_text,
                         ['buildspec=',
                          'buildStatusConfig={'])

    def test_return_suggestions_for_global_arg_with_choices(self):
        self.completer = basic.ShorthandCompleter(
            self.cli_fetcher,
            response_filter=filters.startswith_filter
        )
        parsed = self.parser.parse('aws --output ')
        suggestions = self.completer.complete(parsed)
        names = [s.name for s in suggestions]
        self.assertEqual(names, ['json', 'text', 'table',
                                 'yaml', 'yaml-stream'])

    def test_not_return_suggestions_for_global_arg_wo_trailing_space(self):
        self.completer = basic.ShorthandCompleter(
            self.cli_fetcher,
            response_filter=filters.startswith_filter
        )
        parsed = self.parser.parse('aws --output')
        suggestions = self.completer.complete(parsed)
        self.assertIsNone(suggestions)

    def test_not_return_suggestions_for_global_arg_wo_choices(self):
        self.completer = basic.ShorthandCompleter(
            self.cli_fetcher,
            response_filter=filters.startswith_filter
        )
        parsed = self.parser.parse('aws --debug ')
        suggestions = self.completer.complete(parsed)
        self.assertIsNone(suggestions)

    def test_return_suggestions_for_list_of_enum(self):
        self.completer = basic.ShorthandCompleter(
            self.cli_fetcher,
            response_filter=filters.fuzzy_filter
        )
        parsed = self.parser.parse('aws cloudformation deploy --capabilities ')
        suggestions = self.completer.complete(parsed)
        self.assertIn(
            CompletionResult('CAPABILITY_IAM', 0,
                             False, None, None, 'CAPABILITY_IAM'),
            suggestions)
        self.assertIn(
            CompletionResult('CAPABILITY_NAMED_IAM', 0,
                             False, None, None, 'CAPABILITY_NAMED_IAM'),
            suggestions)

    def test_return_suggestions_for_list_of_enum_with_prefix(self):
        self.completer = basic.ShorthandCompleter(
            self.cli_fetcher,
            response_filter=filters.fuzzy_filter
        )
        parsed = self.parser.parse(
            'aws cloudformation deploy --capabilities ca')
        suggestions = self.completer.complete(parsed)
        self.assertIn(
            CompletionResult('CAPABILITY_IAM', 0,
                             False, None, None, 'CAPABILITY_IAM'),
            suggestions)
        self.assertIn(
            CompletionResult('CAPABILITY_NAMED_IAM', 0,
                             False, None, None, 'CAPABILITY_NAMED_IAM'),
            suggestions)


class TestModelIndexCompleter(unittest.TestCase):
    def setUp(self):
        cli_driver = CLIDriver()
        self.cli_fetcher = fetcher.CliDriverFetcher(cli_driver)
        self.index = InMemoryIndex({
            'command_names': {
                '': [('aws', None)],
            },
            'arg_names': {
                '': {
                    'aws': ['region', 'endpoint-url'],
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
                }
            }
        })
        self.parser = parser.CLIParser(self.index)
        self.completer = basic.ModelIndexCompleter(
            self.index, cli_driver_fetcher=self.cli_fetcher)

    def test_returns_help_text_for_params_in_global_scope(self):
        parsed = self.parser.parse('aws --re')
        suggestions = self.completer.complete(parsed)
        self.assertIn('The region', suggestions[0].help_text)


class TestQueryCompleter(unittest.TestCase):
    def setUp(self):
        cli_driver = CLIDriver()
        self.cli_fetcher = fetcher.CliDriverFetcher(cli_driver)
        index = InMemoryIndex({
            'command_names': {
                '': [('aws', None)],
                'aws': [('ec2', None)],
                'aws.ec2': [('describe-instances', None)],
            },
            'arg_names': {
                '': {
                    'aws': ['query', 'output'],
                },
                'aws.ec2': {
                    'describe-instances': [],
                },
            },
            'arg_data': {
                '': {
                    'aws': {
                        'query': (
                            'query', 'string', 'aws', '', None, False,
                            False),
                        'output': (
                            'output', 'string', 'aws', '', None, False,
                            False),
                    }
                },
                'aws.ec2': {
                    'describe-instances': {}
                }
            }
        })
        self.parser = parser.CLIParser(index)
        self.completer = basic.QueryCompleter(
            self.cli_fetcher, response_filter=filters.fuzzy_filter)

    def _assert_in_completions(self, name, completions):
        self.assertIn(name, [completion.name for completion in completions])

    def _assert_not_in_completions(self, name, completions):
        self.assertNotIn(name, [completion.name for completion in completions])

    def test_get_completion(self):
        parsed = self.parser.parse('aws ec2 describe-instances --query ')
        completions = self.completer.complete(parsed)
        self._assert_in_completions('Reservations', completions)

    def test_complete_on_brackets(self):
        parsed = self.parser.parse(
            'aws ec2 describe-instances --query Reservations[].')
        completions = self.completer.complete(parsed)
        self._assert_in_completions('Reservations[].Groups', completions)

    def test_complete_on_brackets_with_content(self):
        parsed = self.parser.parse(
            'aws ec2 describe-instances --query Reservations[65].')
        completions = self.completer.complete(parsed)
        self._assert_in_completions('Reservations[65].Groups', completions)

    def test_filter_completions(self):
        parsed = self.parser.parse(
            'aws ec2 describe-instances --query Reservations[65].id')
        completions = self.completer.complete(parsed)
        self._assert_in_completions('Reservations[65].OwnerId', completions)
        self._assert_not_in_completions('Reservations[65].Groups', completions)

    def test_not_run_wo_cli_fetcher(self):
        parsed = self.parser.parse(
            'aws ec2 describe-instances --query Reservations[65].id')
        completer = basic.QueryCompleter()
        self.assertIsNone(completer.complete(parsed))

    def test_return_empty_list_when_query_invalid(self):
        parsed = self.parser.parse(
            'aws ec2 describe-instances --query Reservations{65].id')
        completions = self.completer.complete(parsed)
        self.assertEqual([], completions)

    def test_return_empty_list_if_output_is_list_and_expression_is_field(self):
        parsed = self.parser.parse(
            'aws ec2 describe-instances --query Reservations.')
        completions = self.completer.complete(parsed)
        self.assertEqual([], completions)

    def test_return_empty_list_if_output_is_list_and_last_child_is_field(self):
        parsed = self.parser.parse(
            'aws ec2 describe-instances --query Reservations[0].Groups.')
        completions = self.completer.complete(parsed)
        self.assertEqual([], completions)
