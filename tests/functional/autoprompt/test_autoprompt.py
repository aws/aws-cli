import mock
import nose
import os
from contextlib import suppress

from awscli.customizations.exceptions import ParamValidationError
from awscli.clidriver import create_clidriver
from awscli.autoprompt.autoprompt_driver import AutoPromptDriver
from awscli.testutils import FileCreator


def set_up(config, env_var):
    files = FileCreator()
    environ = {
        'AWS_DATA_PATH': os.environ['AWS_DATA_PATH'],
        'AWS_DEFAULT_REGION': 'us-east-1',
        'AWS_ACCESS_KEY_ID': 'access_key',
        'AWS_SECRET_ACCESS_KEY': 'secret_key',
        'AWS_CONFIG_FILE': '',
    }
    environ = set_config_file_contents(environ=environ, config=config,
                                       files=files)
    environ = set_env_var(environ=environ, env_var=env_var)
    environ_patch = mock.patch('os.environ', environ)
    environ_patch.start()
    driver = create_clidriver()
    return driver, environ_patch, files


def set_config_file_contents(environ, files, config=None):
    config_contents = ('')
    if config is not None:
        config_contents = (
            '[default]\n'
            f'cli_auto_prompt = {config}\n'
        )
    environ['AWS_CONFIG_FILE'] = files.create_file(
        'config', config_contents
    )
    return environ


def set_env_var(environ, env_var=None):
    if env_var is not None:
        environ['AWS_CLI_AUTO_PROMPT'] = env_var
    return environ


def test_throws_error_if_cli_auto_prompt_and_no_cli_auto_prompt_set():
    # Mock an XML response from ec2 so that the CLI driver doesn't throw
    # an error during parsing.
    driver, _, _ = set_up(None, {})
    args = ['ec2', 'describe-instances',
            '--cli-auto-prompt', '--no-cli-auto-prompt']
    prompter = mock.Mock()
    prompter.prompt_for_values.return_value = args
    autoprompt_driver = AutoPromptDriver(driver, prompter=prompter)
    with nose.tools.assert_raises(ParamValidationError):
        autoprompt_driver.prompt_for_args(args)


def test_autoprompt_config_provider():
    # Each case is a 3-tuple with the following meaning:
    # First index is the config value. None means not specified.
    # Second index is the environment variable. None means not set.
    # The third index is the expected configuration value.
    cases = [
        ('on', 'on', 'on'),
        ('on', 'off', 'off'),
        ('on', None, 'on'),
        ('off', 'on', 'on'),
        ('off', 'off', 'off'),
        ('off', None, 'off'),
        (None, 'on', 'on'),
        (None, 'off', 'off'),
        (None, None, 'off'),
        (None, 'on-partial', 'on-partial'),
        ('on', 'on-partial', 'on-partial'),
        ('off', 'on-partial', 'on-partial'),
    ]
    for case in cases:
        config, env_var, expected_result = case
        try:
            driver, environ_patch, files = set_up(config, env_var)
            yield (_assert_auto_prompt_configures_as_expected, driver,
                   expected_result)
        finally:
            environ_patch.stop()
            files.remove_all()


def test_autoprompt_on_partial_config_provider():
    cases = [
        ('on-partial', ['foo'], 1),
        ('on-partial', ['ec2'], 1),
        ('on-partial', ['ec2', 'foo'], 1),
        ('on-partial', ['ec2', 'foo', '--foo'], 1),
        ('on-partial', ['ec2', 'describe-instances'], 0),
        ('on-partial', ['ec2', 'describe-instances', '--foo'], 1),
        ('on-partial', ['ec2', 'describe-instances', '--debug'], 0),
        ('on-partial', ['ec2', 'describe-instances', '--instance-ids'], 0),
        ('on-partial', ['ec2', 'describe-instances',
                        '--instance-ids', '--foo'], 1),
        ('on-partial', ['ec2', 'terminate-instances'], 1),
        ('on-partial', ['ec2', 'terminate-instances',
                        '--instance-ids', 'foo'], 0),
        ('on-partial', ['ec2', 'wait'], 1),
        ('on-partial', ['ec2', 'wait', 'instance-stopped'], 0),
        ('on-partial', ['configure', 'set'], 1),
    ]
    for case in cases:
        env_var, args, expected_calls_count = case
        try:
            driver, environ_patch, files = set_up(None, env_var)
            yield (_assert_auto_prompt_run_as_expected, driver, args,
                   expected_calls_count)
        finally:
            environ_patch.stop()
            files.remove_all()


def _assert_auto_prompt_configures_as_expected(driver, expected_result):
    actual = driver.session.get_config_variable('cli_auto_prompt')
    nose.tools.eq_(actual, expected_result)


def _assert_auto_prompt_run_as_expected(driver, args, expected_calls_count):
    prompter = mock.Mock()
    prompter.prompt_for_values.return_value = args
    autoprompt_driver = AutoPromptDriver(driver, prompter=prompter)
    with suppress(Exception):
        autoprompt_driver.prompt_for_args(args)
    assert prompter.prompt_for_values.call_count == expected_calls_count
