import os
import pytest

from awscli.clidriver import create_clidriver
from awscli.testutils import mock, FileCreator


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


@pytest.mark.parametrize(
    "config,env_var,expected_result",
    [
        ('on', 'on', 'on'),
        ('on', 'off', 'off'),
        ('on', None, 'on'),
        ('off', 'on', 'on'),
        ('off', 'off', 'off'),
        ('off', None, 'off'),
        (None, 'on', 'on'),
        (None, 'off', 'off'),
        (None, None, 'off'),
    ]
)
def test_autoprompt_config_provider(config, env_var, expected_result):
    try:
        driver, environ_patch, files = set_up(config, env_var)
        _assert_auto_prompt_configures_as_expected(driver, expected_result)
    finally:
        environ_patch.stop()
        files.remove_all()


def _assert_auto_prompt_configures_as_expected(driver, expected_result):
    actual = driver.session.get_config_variable('cli_auto_prompt')
    assert actual == expected_result
