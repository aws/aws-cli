# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import argparse
import dataclasses
import json
import typing

from datetime import datetime, timedelta

import prompt_toolkit
import pytest
from dateutil.tz import tzlocal

from prompt_toolkit import prompt as ptk_prompt
from prompt_toolkit.document import Document
from prompt_toolkit.validation import Validator
from prompt_toolkit.validation import DummyValidator
from prompt_toolkit.validation import ValidationError

from botocore.stub import Stubber

from awscli.testutils import mock, unittest
from awscli.customizations.configure.sso import display_account
from awscli.customizations.configure.sso import PTKPrompt
from awscli.customizations.configure.sso import SSOSessionConfigurationPrompter
from awscli.customizations.configure.sso import ConfigureSSOCommand
from awscli.customizations.configure.sso import ConfigureSSOSessionCommand
from awscli.customizations.configure.sso import StartUrlValidator
from awscli.customizations.configure.sso import RequiredInputValidator
from awscli.customizations.configure.sso import ScopesValidator
from awscli.customizations.sso.utils import parse_sso_registration_scopes
from awscli.customizations.sso.utils import do_sso_login, PrintOnlyHandler
from awscli.formatter import CLI_OUTPUT_FORMATS

from tests import StubbedSession


@pytest.fixture
def aws_config(tmp_path):
    return tmp_path / "config"


@pytest.fixture
def env(aws_config):
    env_vars = {
        "AWS_DEFAULT_REGION": "us-west-2",
        "AWS_ACCESS_KEY_ID": "access_key",
        "AWS_SECRET_ACCESS_KEY": "secret_key",
        "AWS_CONFIG_FILE": aws_config,
        "AWS_SHARED_CREDENTIALS_FILE": "",
    }
    with mock.patch("os.environ", env_vars):
        yield env_vars


@pytest.fixture
def access_token():
    return "access.token.string"


@pytest.fixture
def account_id():
    return "0123456789"


@pytest.fixture
def role_name():
    return "roleA"


@pytest.fixture
def sso_session_name():
    return "dev"


@pytest.fixture
def scopes():
    return "scope-1, scope-2"


@pytest.fixture
def default_sso_scope():
    return "sso:account:access"


@pytest.fixture
def existing_profile_name():
    return "existing-profile"


@pytest.fixture
def existing_sso_session():
    return "existing-sso-session"


@pytest.fixture
def existing_start_url():
    return "https://existing-start-url"


@pytest.fixture
def existing_sso_region():
    return "existing-sso-region"


@pytest.fixture
def existing_scopes():
    return "existing-scope-1, existing-scope-2"


@pytest.fixture
def existing_region():
    return "existing-region"


@pytest.fixture
def existing_output():
    return "existing-output"


@pytest.fixture
def botocore_session(env):
    return StubbedSession()


@pytest.fixture
def all_sso_oidc_regions(botocore_session):
    return botocore_session.get_available_regions("sso-oidc")


@pytest.fixture
def sso_stubber_factory(env, botocore_session):
    def create_sso_stubber(session=None):
        if session is None:
            session = botocore_session
        sso_client = session.create_client("sso")
        stubber = Stubber(sso_client)
        stubber.activate()
        return stubber

    return create_sso_stubber


@pytest.fixture
def sso_stubber(sso_stubber_factory):
    return sso_stubber_factory()


@pytest.fixture
def stub_sso_list_accounts(sso_stubber, access_token):
    def _do_stub_list_accounts(accounts, override_sso_stubber=None):
        stubber = sso_stubber
        if override_sso_stubber is not None:
            stubber = override_sso_stubber
        stubber.add_response(
            "list_accounts",
            service_response={
                "accountList": accounts,
            },
            expected_params={"accessToken": access_token},
        )

    return _do_stub_list_accounts


@pytest.fixture
def stub_sso_list_roles(sso_stubber, access_token):
    def _do_stub_list_accounts(
        role_names, expected_account_id, override_sso_stubber=None
    ):
        stubber = sso_stubber
        if override_sso_stubber is not None:
            stubber = override_sso_stubber
        stubber.add_response(
            "list_account_roles",
            service_response={
                "roleList": [
                    {"roleName": role_name} for role_name in role_names
                ],
            },
            expected_params={
                "accountId": expected_account_id,
                "accessToken": access_token,
            },
        )

    return _do_stub_list_accounts


@pytest.fixture
def stub_simple_single_item_sso_responses(
    sso_stubber, access_token, stub_sso_list_accounts, stub_sso_list_roles
):
    def _do_stub_simple_single_item_sso_responses(
        account_id, role_name, override_sso_stubber=None
    ):
        stub_sso_list_accounts(
            accounts=[
                {
                    "accountId": account_id,
                    "emailAddress": "account@site.com",
                }
            ],
            override_sso_stubber=override_sso_stubber,
        )
        stub_sso_list_roles(
            role_names=[role_name],
            expected_account_id=account_id,
            override_sso_stubber=override_sso_stubber,
        )

    return _do_stub_simple_single_item_sso_responses


@pytest.fixture
def stub_sso_authorization_error(sso_stubber):
    def _do_stub_authorization_error(override_sso_stubber=None):
        stubber = sso_stubber
        if override_sso_stubber is not None:
            stubber = override_sso_stubber
        stubber.add_client_error(
            "list_accounts", service_error_code="UnauthorizedException"
        )

    return _do_stub_authorization_error


@pytest.fixture()
def ptk_stubber():
    return PTKStubber()


@pytest.fixture
def prompter(ptk_stubber):
    return PTKPrompt(prompter=ptk_stubber.prompt)


@pytest.fixture
def sso_config_prompter_factory(env, botocore_session, prompter):
    def create_sso_config_prompter(session=None, prompt=None):
        if session is None:
            session = botocore_session
        if prompt is None:
            prompt = prompter
        return SSOSessionConfigurationPrompter(
            botocore_session=session, prompter=prompt
        )

    return create_sso_config_prompter


@pytest.fixture
def sso_config_prompter(sso_config_prompter_factory):
    return sso_config_prompter_factory()


@pytest.fixture
def selector(ptk_stubber):
    return ptk_stubber.select_menu


@pytest.fixture
def mock_ptk_app():
    mock_app = mock.Mock(spec=prompt_toolkit.application.DummyApplication())
    with prompt_toolkit.application.current.set_app(mock_app):
        yield mock_app


@pytest.fixture
def mock_do_sso_login():
    login_mock = mock.Mock(spec=do_sso_login)
    login_mock.return_value = {
        "accessToken": "access.token.string",
        "expiresAt": datetime.now(tzlocal()) + timedelta(hours=24),
    }
    return login_mock


@pytest.fixture
def sso_cmd_factory(
    env, botocore_session, prompter, mock_do_sso_login, selector
):
    def create_sso_cmd(**override_kwargs):
        kwargs = {
            "session": botocore_session,
            "prompter": prompter,
            "sso_login": mock_do_sso_login,
            "selector": selector,
        }
        kwargs.update(**override_kwargs)
        return ConfigureSSOCommand(**kwargs)

    return create_sso_cmd


@pytest.fixture
def sso_cmd(sso_cmd_factory):
    return sso_cmd_factory()


@pytest.fixture
def sso_session_cmd_factory(env, botocore_session, prompter):
    def create_sso_session_cmd(**override_kwargs):
        kwargs = {"session": botocore_session, "prompter": prompter}
        kwargs.update(**override_kwargs)
        return ConfigureSSOSessionCommand(**kwargs)

    return create_sso_session_cmd


@pytest.fixture
def sso_session_cmd(sso_session_cmd_factory):
    return sso_session_cmd_factory()


@pytest.fixture
def args():
    return []


@pytest.fixture
def parsed_globals():
    return argparse.Namespace()


@pytest.fixture
def start_url_prompt():
    return StartUrlPrompt(answer="https://starturl", expected_default=None)


@pytest.fixture
def sso_region_prompt():
    return SSORegionPrompt(answer="us-west-2", expected_default=None)


@pytest.fixture
def scopes_prompt(scopes, default_sso_scope):
    return ScopesPrompt(answer=scopes, expected_default=default_sso_scope)


@pytest.fixture
def account_id_select(account_id):
    selected_account = {
        "accountId": account_id,
        "emailAddress": "account@site.com",
    }
    return SelectMenu(
        answer=selected_account,
        expected_choices=[
            selected_account,
            {"accountId": "1234567890", "emailAddress": "account2@site.com"},
        ],
    )


@pytest.fixture
def role_name_select(role_name):
    return SelectMenu(answer=role_name, expected_choices=[role_name, "roleB"])


@pytest.fixture
def region_prompt():
    return RegionPrompt(answer="us-west-2", expected_default=None)


@pytest.fixture
def output_prompt():
    return OutputPrompt(answer="json", expected_default=None)


@pytest.fixture
def profile_prompt(role_name, account_id):
    return ProfilePrompt(
        answer="dev", expected_default=f"{role_name}-{account_id}"
    )


@pytest.fixture
def configure_sso_legacy_inputs(
    start_url_prompt,
    sso_region_prompt,
    account_id_select,
    role_name_select,
    region_prompt,
    output_prompt,
    profile_prompt,
):
    return UserInputs(
        session_prompt=RecommendedSessionPrompt(answer=""),
        start_url_prompt=start_url_prompt,
        sso_region_prompt=sso_region_prompt,
        account_id_select=account_id_select,
        role_name_select=role_name_select,
        region_prompt=region_prompt,
        output_prompt=output_prompt,
        profile_prompt=profile_prompt,
    )


@pytest.fixture
def configure_sso_legacy_with_existing_defaults_inputs(
    configure_sso_legacy_inputs,
    existing_start_url,
    existing_sso_region,
    existing_region,
    existing_output,
):
    inputs = configure_sso_legacy_inputs
    inputs.start_url_prompt.expected_default = existing_start_url
    inputs.sso_region_prompt.expected_default = existing_sso_region
    inputs.region_prompt.expected_default = existing_region
    inputs.output_prompt.expected_default = existing_output
    return inputs


@pytest.fixture
def configure_sso_using_new_session_inputs(
    start_url_prompt,
    sso_region_prompt,
    scopes_prompt,
    account_id_select,
    role_name_select,
    region_prompt,
    output_prompt,
    profile_prompt,
    sso_session_name,
):
    return UserInputs(
        session_prompt=RecommendedSessionPrompt(answer=sso_session_name),
        start_url_prompt=start_url_prompt,
        sso_region_prompt=sso_region_prompt,
        scopes_prompt=scopes_prompt,
        account_id_select=account_id_select,
        role_name_select=role_name_select,
        region_prompt=region_prompt,
        output_prompt=output_prompt,
        profile_prompt=profile_prompt,
    )


@pytest.fixture()
def configure_sso_using_existing_session_inputs(
    account_id_select,
    role_name_select,
    region_prompt,
    output_prompt,
    profile_prompt,
    existing_sso_session,
):
    return UserInputs(
        session_prompt=RecommendedSessionPrompt(answer=existing_sso_session),
        account_id_select=account_id_select,
        role_name_select=role_name_select,
        region_prompt=region_prompt,
        output_prompt=output_prompt,
        profile_prompt=profile_prompt,
    )


@pytest.fixture
def configure_sso_with_existing_defaults_inputs(
    configure_sso_using_existing_session_inputs,
    existing_sso_session,
    existing_region,
    existing_output,
    sso_session_name,
):
    inputs = configure_sso_using_existing_session_inputs
    inputs.session_prompt = SessionWithDefaultPrompt(
        answer=sso_session_name, expected_default=existing_sso_session
    )
    inputs.region_prompt.expected_default = existing_region
    inputs.output_prompt.expected_default = existing_output
    return inputs


@pytest.fixture
def configure_sso_using_new_session_from_legacy_profile_inputs(
    configure_sso_using_new_session_inputs,
    sso_session_name,
    existing_start_url,
    existing_sso_region,
    existing_region,
    existing_output,
):
    inputs = configure_sso_using_new_session_inputs
    inputs.clear_answers()
    inputs.session_prompt.answer = sso_session_name
    inputs.start_url_prompt.expected_default = existing_start_url
    inputs.sso_region_prompt.expected_default = existing_sso_region
    inputs.region_prompt.expected_default = existing_region
    inputs.output_prompt.expected_default = existing_output
    return inputs


@pytest.fixture()
def configure_sso_session_inputs(
    sso_session_name, start_url_prompt, sso_region_prompt, scopes_prompt
):
    return UserInputs(
        session_prompt=RequiredSessionPrompt(answer=sso_session_name),
        start_url_prompt=start_url_prompt,
        sso_region_prompt=sso_region_prompt,
        scopes_prompt=scopes_prompt,
    )


@pytest.fixture
def configure_sso_session_with_existing_defaults_inputs(
    configure_sso_session_inputs,
    existing_start_url,
    existing_sso_region,
    existing_scopes,
):
    inputs = configure_sso_session_inputs
    inputs.start_url_prompt.expected_default = existing_start_url
    inputs.sso_region_prompt.expected_default = existing_sso_region
    inputs.scopes_prompt.expected_default = existing_scopes
    return inputs


@pytest.fixture
def aws_config_lines_for_existing_legacy_profile(
    existing_profile_name,
    existing_start_url,
    existing_sso_region,
    existing_region,
    existing_output,
    account_id,
    role_name,
):
    return [
        f"[profile {existing_profile_name}]",
        f"sso_start_url = {existing_start_url}",
        f"sso_region = {existing_sso_region}",
        f"sso_account_id = {account_id}",
        f"sso_role_name = {role_name}",
        f"region = {existing_region}",
        f"output = {existing_output}",
    ]


@pytest.fixture
def aws_config_lines_for_existing_sso_session(
    existing_sso_session,
    existing_start_url,
    existing_sso_region,
    existing_scopes,
):
    return [
        f"[sso-session {existing_sso_session}]",
        f"sso_start_url = {existing_start_url}",
        f"sso_region = {existing_sso_region}",
        f"sso_registration_scopes = {existing_scopes}",
    ]


@pytest.fixture
def aws_config_lines_for_existing_profile_and_session(
    existing_profile_name,
    existing_sso_session,
    existing_region,
    existing_output,
    account_id,
    role_name,
    aws_config_lines_for_existing_sso_session,
):
    return [
        f"[profile {existing_profile_name}]",
        f"sso_session = {existing_sso_session}",
        f"sso_account_id = {account_id}",
        f"sso_role_name = {role_name}",
        f"region = {existing_region}",
        f"output = {existing_output}",
    ] + aws_config_lines_for_existing_sso_session


@dataclasses.dataclass
class UserInput:
    answer: typing.Any


@dataclasses.dataclass
class Prompt(UserInput):
    expected_validator_cls: typing.Optional[Validator] = None
    expected_completions: typing.Optional[typing.List[str]] = None
    _expected_message: typing.Optional[str] = dataclasses.field(
        init=False, repr=False, default=None
    )

    @property
    def expected_message(self):
        return self._expected_message

    @expected_message.setter
    def expected_message(self, value):
        self._expected_message = value


@dataclasses.dataclass
class PromptWithDefault(Prompt):
    expected_default: typing.Any = None
    msg_format: str = dataclasses.field(init=False)

    @property
    def expected_message(self):
        if self._expected_message is None:
            self._expected_message = self.msg_format.format(
                default=self.expected_default
            )
        return self._expected_message


@dataclasses.dataclass
class StartUrlPrompt(PromptWithDefault):
    msg_format: str = dataclasses.field(
        init=False, default="SSO start URL [{default}]: "
    )
    expected_validator_cls: typing.Optional[Validator] = StartUrlValidator


@dataclasses.dataclass
class SSORegionPrompt(PromptWithDefault):
    msg_format: str = dataclasses.field(
        init=False, default="SSO region [{default}]: "
    )
    expected_validator_cls: typing.Optional[Validator] = RequiredInputValidator


@dataclasses.dataclass
class ScopesPrompt(PromptWithDefault):
    msg_format: str = dataclasses.field(
        init=False, default="SSO registration scopes [{default}]: "
    )
    expected_validator_cls: typing.Optional[Validator] = ScopesValidator


@dataclasses.dataclass
class RequiredSessionPrompt(Prompt):
    expected_validator_cls: typing.Optional[Validator] = RequiredInputValidator

    def __post_init__(self):
        super().__init__(
            answer=self.answer,
            expected_validator_cls=self.expected_validator_cls,
        )
        self.expected_message = "SSO session name: "


@dataclasses.dataclass
class RecommendedSessionPrompt(Prompt):
    def __post_init__(self):
        super().__init__(answer=self.answer)
        self.expected_message = "SSO session name (Recommended): "


@dataclasses.dataclass
class SessionWithDefaultPrompt(PromptWithDefault):
    msg_format: str = dataclasses.field(
        init=False, default="SSO session name [{default}]: "
    )


@dataclasses.dataclass
class RegionPrompt(PromptWithDefault):
    msg_format: str = dataclasses.field(
        init=False, default="Default client Region [{default}]: "
    )


@dataclasses.dataclass
class OutputPrompt(PromptWithDefault):
    msg_format: str = dataclasses.field(
        init=False, default="CLI default output format [{default}]: "
    )


@dataclasses.dataclass
class ProfilePrompt(PromptWithDefault):
    msg_format: str = dataclasses.field(
        init=False, default="Profile name [{default}]: "
    )
    expected_validator_cls: typing.Optional[Validator] = RequiredInputValidator


@dataclasses.dataclass
class SelectMenu(UserInput):
    expected_choices: typing.Optional[typing.List[typing.Any]] = None


@dataclasses.dataclass
class UserInputs:
    session_prompt: typing.Optional[Prompt] = None
    start_url_prompt: typing.Optional[StartUrlPrompt] = None
    sso_region_prompt: typing.Optional[SSORegionPrompt] = None
    scopes_prompt: typing.Optional[ScopesPrompt] = None
    account_id_select: typing.Optional[SelectMenu] = None
    role_name_select: typing.Optional[SelectMenu] = None
    region_prompt: typing.Optional[RegionPrompt] = None
    output_prompt: typing.Optional[OutputPrompt] = None
    profile_prompt: typing.Optional[ProfilePrompt] = None

    def get_expected_inputs(self):
        expected_inputs = []
        for possible_input_field in dataclasses.fields(self):
            possible_input = getattr(self, possible_input_field.name)
            if possible_input is not None:
                expected_inputs.append(possible_input)
        return expected_inputs

    def clear_answers(self):
        for user_input in self.get_expected_inputs():
            user_input.answer = ""

    def skip_account_and_role_selection(self):
        self.account_id_select = None
        self.role_name_select = None

    def skip_profile_prompt(self):
        self.profile_prompt = None


class PTKStubber:
    _ALLOWED_PROMPT_KWARGS = {
        "validator",
        "validate_while_typing",
        "completer",
        "complete_while_typing",
        "bottom_toolbar",
        "refresh_interval",
        "style",
    }
    _ALLOWED_SELECT_MENU_KWARGS = {
        "display_format",
        "max_height",
    }

    def __init__(self, user_inputs=None):
        if user_inputs is None:
            user_inputs = UserInputs()
        self.user_inputs = user_inputs
        self._expected_inputs = None

    def prompt(self, message, **kwargs):
        self._initialize_expected_inputs_if_needed()
        self._validate_kwargs(kwargs, self._ALLOWED_PROMPT_KWARGS)
        if not self._expected_inputs:
            raise AssertionError(
                f'Received prompt with no stubbed answer: "{message}"'
            )
        prompt = self._expected_inputs.pop(0)
        assert isinstance(
            prompt, Prompt
        ), f'Did not receive user input of type Prompt for: "{message}"'
        if prompt.expected_message is not None:
            assert message == prompt.expected_message, (
                f"Prompt does not match expected "
                f'prompt for answer: "{prompt}"'
            )
        if prompt.expected_validator_cls:
            assert isinstance(
                kwargs.get("validator"), prompt.expected_validator_cls
            )
        if prompt.expected_completions is not None:
            provided_completer = kwargs.get("completer")
            assert provided_completer is not None, (
                f"Expected completions but no completer was provided for "
                f"prompt: {prompt}"
            )
            assert provided_completer.words == prompt.expected_completions
        return prompt.answer

    def select_menu(self, items, **kwargs):
        self._initialize_expected_inputs_if_needed()
        self._validate_kwargs(kwargs, self._ALLOWED_SELECT_MENU_KWARGS)
        if not self._expected_inputs:
            raise AssertionError(
                f'Received select_menu with no stubbed answer: "{items}"'
            )
        select_menu = self._expected_inputs.pop(0)
        assert isinstance(
            select_menu, SelectMenu
        ), f'Did not receive user input of type SelectMenu for: "{items}"'
        if select_menu.expected_choices is not None:
            assert items == select_menu.expected_choices, (
                f"Choices does not match expected select_menu choices "
                f'for answer: "{select_menu.answer}"'
            )
        return select_menu.answer

    def _initialize_expected_inputs_if_needed(self):
        if self._expected_inputs is None:
            self._expected_inputs = self.user_inputs.get_expected_inputs()

    def _validate_kwargs(self, provided_kwargs, allowed_kwargs):
        assert set(provided_kwargs).issubset(
            allowed_kwargs
        ), "Arguments provided does not matched allowed keyword arguments"


def write_aws_config(aws_config, lines):
    with open(aws_config, "w") as f:
        content = "\n".join(lines)
        f.write(content + "\n")


def assert_aws_config(aws_config, expected_lines):
    with open(aws_config, "r") as f:
        assert f.read().splitlines() == expected_lines


class TestConfigureSSOCommand:
    def assert_do_sso_login_call(
        self,
        mock_do_sso_login,
        botocore_session,
        expected_sso_region,
        expected_start_url,
        expected_use_device_code=False,
        expected_session_name=None,
        expected_scopes=None,
        expected_auth_handler_cls=None,
        expected_force_refresh=None,
    ):
        expected_kwargs = {
            "sso_region": expected_sso_region,
            "parsed_globals": mock.ANY,
            "start_url": expected_start_url,
            "on_pending_authorization": None,
            "token_cache": None,
            "use_device_code": expected_use_device_code,
        }
        if expected_session_name is not None:
            expected_kwargs["session_name"] = expected_session_name
        if expected_scopes is not None:
            expected_kwargs["registration_scopes"] = expected_scopes
        if expected_auth_handler_cls:
            expected_kwargs["on_pending_authorization"] = mock.ANY
        if expected_force_refresh is not None:
            expected_kwargs["force_refresh"] = expected_force_refresh

        mock_do_sso_login.assert_called_with(
            botocore_session, **expected_kwargs
        )

        if expected_auth_handler_cls:
            _, _, login_kwargs = mock_do_sso_login.mock_calls[0]
            auth_handler = login_kwargs["on_pending_authorization"]
            assert isinstance(auth_handler, expected_auth_handler_cls)

    def test_legacy_configure_sso_flow(
        self,
        sso_cmd,
        ptk_stubber,
        aws_config,
        stub_sso_list_roles,
        stub_sso_list_accounts,
        mock_do_sso_login,
        botocore_session,
        args,
        parsed_globals,
        configure_sso_legacy_inputs,
        capsys,
    ):
        inputs = configure_sso_legacy_inputs
        selected_account_id = inputs.account_id_select.answer["accountId"]
        ptk_stubber.user_inputs = inputs
        stub_sso_list_accounts(inputs.account_id_select.expected_choices)
        stub_sso_list_roles(
            inputs.role_name_select.expected_choices,
            expected_account_id=selected_account_id,
        )

        sso_cmd(args, parsed_globals)
        self.assert_do_sso_login_call(
            mock_do_sso_login,
            botocore_session,
            expected_sso_region=inputs.sso_region_prompt.answer,
            expected_start_url=inputs.start_url_prompt.answer,
        )
        assert_aws_config(
            aws_config,
            expected_lines=[
                f"[profile {inputs.profile_prompt.answer}]",
                f"sso_start_url = {inputs.start_url_prompt.answer}",
                f"sso_region = {inputs.sso_region_prompt.answer}",
                f"sso_account_id = {selected_account_id}",
                f"sso_role_name = {inputs.role_name_select.answer}",
                f"region = {inputs.region_prompt.answer}",
                f"output = {inputs.output_prompt.answer}",
            ],
        )
        stdout = capsys.readouterr().out
        assert "WARNING: Configuring using legacy format" in stdout
        assert f"aws s3 ls --profile {inputs.profile_prompt.answer}" in stdout

    def test_single_account_single_role_flow_no_browser(
        self,
        sso_cmd,
        ptk_stubber,
        aws_config,
        stub_simple_single_item_sso_responses,
        mock_do_sso_login,
        botocore_session,
        parsed_globals,
        configure_sso_legacy_inputs,
        account_id,
        role_name,
    ):
        inputs = configure_sso_legacy_inputs
        inputs.skip_account_and_role_selection()
        ptk_stubber.user_inputs = inputs
        stub_simple_single_item_sso_responses(account_id, role_name)

        sso_cmd(["--no-browser"], parsed_globals)
        self.assert_do_sso_login_call(
            mock_do_sso_login,
            botocore_session,
            expected_sso_region=inputs.sso_region_prompt.answer,
            expected_start_url=inputs.start_url_prompt.answer,
            expected_auth_handler_cls=PrintOnlyHandler,
        )
        assert_aws_config(
            aws_config,
            expected_lines=[
                f"[profile {inputs.profile_prompt.answer}]",
                f"sso_start_url = {inputs.start_url_prompt.answer}",
                f"sso_region = {inputs.sso_region_prompt.answer}",
                f"sso_account_id = {account_id}",
                f"sso_role_name = {role_name}",
                f"region = {inputs.region_prompt.answer}",
                f"output = {inputs.output_prompt.answer}",
            ],
        )

    def test_single_account_single_role_flow(
        self,
        sso_cmd,
        ptk_stubber,
        aws_config,
        stub_simple_single_item_sso_responses,
        mock_do_sso_login,
        botocore_session,
        args,
        parsed_globals,
        configure_sso_legacy_inputs,
        account_id,
        role_name,
    ):
        inputs = configure_sso_legacy_inputs
        inputs.skip_account_and_role_selection()
        ptk_stubber.user_inputs = inputs
        stub_simple_single_item_sso_responses(account_id, role_name)

        sso_cmd(args, parsed_globals)
        self.assert_do_sso_login_call(
            mock_do_sso_login,
            botocore_session,
            expected_sso_region=inputs.sso_region_prompt.answer,
            expected_start_url=inputs.start_url_prompt.answer,
        )
        assert_aws_config(
            aws_config,
            expected_lines=[
                f"[profile {inputs.profile_prompt.answer}]",
                f"sso_start_url = {inputs.start_url_prompt.answer}",
                f"sso_region = {inputs.sso_region_prompt.answer}",
                f"sso_account_id = {account_id}",
                f"sso_role_name = {role_name}",
                f"region = {inputs.region_prompt.answer}",
                f"output = {inputs.output_prompt.answer}",
            ],
        )

    def test_no_accounts_flow_raises_error(
        self,
        sso_cmd,
        ptk_stubber,
        sso_stubber,
        stub_sso_list_accounts,
        args,
        parsed_globals,
        configure_sso_legacy_inputs,
    ):
        ptk_stubber.user_inputs = configure_sso_legacy_inputs
        stub_sso_list_accounts([])
        with pytest.raises(RuntimeError):
            sso_cmd(args, parsed_globals)
        sso_stubber.assert_no_pending_responses()

    def test_no_roles_flow_raises_error(
        self,
        sso_cmd,
        ptk_stubber,
        sso_stubber,
        stub_sso_list_accounts,
        stub_sso_list_roles,
        args,
        parsed_globals,
        configure_sso_legacy_inputs,
    ):
        only_account = configure_sso_legacy_inputs.account_id_select.answer
        configure_sso_legacy_inputs.account_id_select = None
        ptk_stubber.user_inputs = configure_sso_legacy_inputs
        stub_sso_list_accounts([only_account])
        stub_sso_list_roles([], expected_account_id=only_account["accountId"])
        with pytest.raises(RuntimeError):
            sso_cmd(args, parsed_globals)
        sso_stubber.assert_no_pending_responses()

    def test_defaults_to_scoped_config(
        self,
        sso_cmd_factory,
        ptk_stubber,
        aws_config,
        sso_stubber_factory,
        stub_simple_single_item_sso_responses,
        mock_do_sso_login,
        args,
        parsed_globals,
        configure_sso_legacy_with_existing_defaults_inputs,
        aws_config_lines_for_existing_legacy_profile,
        account_id,
        role_name,
        existing_profile_name,
    ):
        write_aws_config(
            aws_config, lines=aws_config_lines_for_existing_legacy_profile
        )
        session = StubbedSession(profile=existing_profile_name)

        inputs = configure_sso_legacy_with_existing_defaults_inputs
        inputs.skip_account_and_role_selection()
        inputs.skip_profile_prompt()
        inputs.clear_answers()
        ptk_stubber.user_inputs = inputs

        sso_stubber = sso_stubber_factory(session)
        stub_simple_single_item_sso_responses(
            account_id, role_name, sso_stubber
        )

        sso_cmd = sso_cmd_factory(session=session)
        sso_cmd(args, parsed_globals)
        self.assert_do_sso_login_call(
            mock_do_sso_login,
            session,
            expected_sso_region=inputs.sso_region_prompt.expected_default,
            expected_start_url=inputs.start_url_prompt.expected_default,
        )
        assert_aws_config(
            aws_config,
            expected_lines=aws_config_lines_for_existing_legacy_profile,
        )

    def test_handles_non_existent_profile(
        self,
        sso_cmd_factory,
        ptk_stubber,
        aws_config,
        botocore_session,
        stub_simple_single_item_sso_responses,
        mock_do_sso_login,
        args,
        parsed_globals,
        configure_sso_legacy_inputs,
        account_id,
        role_name,
    ):
        inputs = configure_sso_legacy_inputs
        inputs.skip_account_and_role_selection()
        inputs.skip_profile_prompt()
        ptk_stubber.user_inputs = inputs
        stub_simple_single_item_sso_responses(account_id, role_name)

        new_session = StubbedSession(profile="new-profile")
        # We use the default session to create the stubbed clients because
        # if we create the stubbed clients with a non-existent profile, we will
        # get a ProfileNotFound error. So after the clients' creation we
        # assign them to be used in the session using the new profile.
        new_session.cached_clients.update(botocore_session.cached_clients)
        new_session.client_stubs.update(botocore_session.client_stubs)

        sso_cmd = sso_cmd_factory(session=new_session)
        sso_cmd(args, parsed_globals)
        self.assert_do_sso_login_call(
            mock_do_sso_login,
            new_session,
            expected_sso_region=inputs.sso_region_prompt.answer,
            expected_start_url=inputs.start_url_prompt.answer,
        )
        assert_aws_config(
            aws_config,
            expected_lines=[
                f"[profile new-profile]",
                f"sso_start_url = {inputs.start_url_prompt.answer}",
                f"sso_region = {inputs.sso_region_prompt.answer}",
                f"sso_account_id = {account_id}",
                f"sso_role_name = {role_name}",
                f"region = {inputs.region_prompt.answer}",
                f"output = {inputs.output_prompt.answer}",
            ],
        )

    def test_cli_config_is_none_not_written(
        self,
        sso_cmd,
        ptk_stubber,
        aws_config,
        botocore_session,
        stub_simple_single_item_sso_responses,
        args,
        parsed_globals,
        configure_sso_legacy_inputs,
        account_id,
        role_name,
    ):
        inputs = configure_sso_legacy_inputs
        inputs.skip_account_and_role_selection()
        inputs.region_prompt.answer = ""
        inputs.output_prompt.answer = ""
        ptk_stubber.user_inputs = inputs
        stub_simple_single_item_sso_responses(account_id, role_name)

        sso_cmd(args, parsed_globals)

        assert_aws_config(
            aws_config,
            expected_lines=[
                f"[profile {inputs.profile_prompt.answer}]",
                f"sso_start_url = {inputs.start_url_prompt.answer}",
                f"sso_region = {inputs.sso_region_prompt.answer}",
                f"sso_account_id = {account_id}",
                f"sso_role_name = {role_name}",
            ],
        )

    def test_prompts_suggest_values_from_profiles(
        self,
        sso_cmd_factory,
        ptk_stubber,
        aws_config,
        sso_stubber_factory,
        stub_simple_single_item_sso_responses,
        aws_config_lines_for_existing_legacy_profile,
        existing_start_url,
        args,
        parsed_globals,
        configure_sso_legacy_inputs,
        account_id,
        role_name,
        all_sso_oidc_regions,
    ):
        write_aws_config(
            aws_config, lines=aws_config_lines_for_existing_legacy_profile
        )
        session = StubbedSession()

        inputs = configure_sso_legacy_inputs
        inputs.skip_account_and_role_selection()
        inputs.start_url_prompt.expected_completions = [existing_start_url]
        inputs.sso_region_prompt.expected_completions = all_sso_oidc_regions
        inputs.output_prompt.expected_completions = list(
            CLI_OUTPUT_FORMATS.keys()
        )
        ptk_stubber.user_inputs = inputs

        sso_stubber = sso_stubber_factory(session)
        stub_simple_single_item_sso_responses(
            account_id, role_name, sso_stubber
        )
        sso_cmd = sso_cmd_factory(session=session)
        assert sso_cmd(args, parsed_globals) == 0

    def test_configure_sso_with_new_sso_session(
        self,
        sso_cmd,
        ptk_stubber,
        aws_config,
        stub_sso_list_roles,
        stub_sso_list_accounts,
        mock_do_sso_login,
        botocore_session,
        args,
        parsed_globals,
        configure_sso_using_new_session_inputs,
        capsys,
    ):
        inputs = configure_sso_using_new_session_inputs
        selected_account_id = inputs.account_id_select.answer["accountId"]
        ptk_stubber.user_inputs = inputs

        stub_sso_list_accounts(inputs.account_id_select.expected_choices)
        stub_sso_list_roles(
            inputs.role_name_select.expected_choices,
            expected_account_id=selected_account_id,
        )

        sso_cmd(args, parsed_globals)
        self.assert_do_sso_login_call(
            mock_do_sso_login,
            botocore_session,
            expected_session_name=inputs.session_prompt.answer,
            expected_sso_region=inputs.sso_region_prompt.answer,
            expected_start_url=inputs.start_url_prompt.answer,
            expected_scopes=parse_sso_registration_scopes(
                inputs.scopes_prompt.answer
            ),
            expected_force_refresh=True,
        )
        assert_aws_config(
            aws_config,
            expected_lines=[
                f"[profile {inputs.profile_prompt.answer}]",
                f"sso_session = {inputs.session_prompt.answer}",
                f"sso_account_id = {selected_account_id}",
                f"sso_role_name = {inputs.role_name_select.answer}",
                f"region = {inputs.region_prompt.answer}",
                f"output = {inputs.output_prompt.answer}",
                f"[sso-session {inputs.session_prompt.answer}]",
                f"sso_start_url = {inputs.start_url_prompt.answer}",
                f"sso_region = {inputs.sso_region_prompt.answer}",
                f"sso_registration_scopes = {inputs.scopes_prompt.answer}",
            ],
        )
        stdout = capsys.readouterr().out
        assert "WARNING: Configuring using legacy format" not in stdout
        assert f"aws s3 ls --profile {inputs.profile_prompt.answer}" in stdout

    def test_configure_sso_with_existing_sso_session(
        self,
        sso_cmd_factory,
        ptk_stubber,
        aws_config,
        sso_stubber_factory,
        stub_simple_single_item_sso_responses,
        mock_do_sso_login,
        args,
        parsed_globals,
        configure_sso_using_existing_session_inputs,
        aws_config_lines_for_existing_sso_session,
        account_id,
        role_name,
        existing_start_url,
        existing_sso_region,
        existing_scopes,
    ):
        write_aws_config(
            aws_config, lines=aws_config_lines_for_existing_sso_session
        )
        session = StubbedSession()

        inputs = configure_sso_using_existing_session_inputs
        inputs.skip_account_and_role_selection()
        ptk_stubber.user_inputs = inputs

        sso_stubber = sso_stubber_factory(session)
        stub_simple_single_item_sso_responses(
            account_id, role_name, sso_stubber
        )
        sso_cmd = sso_cmd_factory(session=session)
        sso_cmd(args, parsed_globals)

        self.assert_do_sso_login_call(
            mock_do_sso_login,
            session,
            expected_session_name=inputs.session_prompt.answer,
            expected_sso_region=existing_sso_region,
            expected_start_url=existing_start_url,
            expected_scopes=parse_sso_registration_scopes(existing_scopes),
        )
        assert_aws_config(
            aws_config,
            expected_lines=aws_config_lines_for_existing_sso_session
            + [
                f"[profile {inputs.profile_prompt.answer}]",
                f"sso_session = {inputs.session_prompt.answer}",
                f"sso_account_id = {account_id}",
                f"sso_role_name = {role_name}",
                f"region = {inputs.region_prompt.answer}",
                f"output = {inputs.output_prompt.answer}",
            ],
        )

    def test_configure_sso_reusing_existing_configuration(
        self,
        sso_cmd_factory,
        ptk_stubber,
        aws_config,
        sso_stubber_factory,
        stub_simple_single_item_sso_responses,
        mock_do_sso_login,
        args,
        parsed_globals,
        configure_sso_with_existing_defaults_inputs,
        aws_config_lines_for_existing_profile_and_session,
        account_id,
        role_name,
        existing_profile_name,
        existing_start_url,
        existing_sso_region,
        existing_scopes,
    ):
        write_aws_config(
            aws_config, lines=aws_config_lines_for_existing_profile_and_session
        )
        session = StubbedSession(profile=existing_profile_name)

        inputs = configure_sso_with_existing_defaults_inputs
        inputs.skip_account_and_role_selection()
        inputs.clear_answers()
        ptk_stubber.user_inputs = inputs

        sso_stubber = sso_stubber_factory(session)
        stub_simple_single_item_sso_responses(
            account_id, role_name, sso_stubber
        )
        sso_cmd = sso_cmd_factory(session=session)
        sso_cmd(args, parsed_globals)

        self.assert_do_sso_login_call(
            mock_do_sso_login,
            session,
            expected_session_name=inputs.session_prompt.expected_default,
            expected_sso_region=existing_sso_region,
            expected_start_url=existing_start_url,
            expected_scopes=parse_sso_registration_scopes(existing_scopes),
        )
        assert_aws_config(
            aws_config,
            expected_lines=aws_config_lines_for_existing_profile_and_session,
        )

    def test_configure_sso_skips_account_role_config_when_no_access(
        self,
        sso_cmd,
        ptk_stubber,
        aws_config,
        stub_sso_authorization_error,
        mock_do_sso_login,
        botocore_session,
        args,
        parsed_globals,
        configure_sso_using_new_session_inputs,
        capsys,
    ):
        inputs = configure_sso_using_new_session_inputs
        inputs.skip_account_and_role_selection()
        inputs.profile_prompt.expected_default = None
        ptk_stubber.user_inputs = inputs

        stub_sso_authorization_error()

        sso_cmd(args, parsed_globals)
        assert_aws_config(
            aws_config,
            expected_lines=[
                f"[profile {inputs.profile_prompt.answer}]",
                f"sso_session = {inputs.session_prompt.answer}",
                f"region = {inputs.region_prompt.answer}",
                f"output = {inputs.output_prompt.answer}",
                f"[sso-session {inputs.session_prompt.answer}]",
                f"sso_start_url = {inputs.start_url_prompt.answer}",
                f"sso_region = {inputs.sso_region_prompt.answer}",
                f"sso_registration_scopes = {inputs.scopes_prompt.answer}",
            ],
        )
        stdout = capsys.readouterr().out
        profile_answer = inputs.profile_prompt.answer
        assert "Unable to list AWS accounts" in stdout
        assert f"configured SSO for profile: {profile_answer}" in stdout

    def test_configure_sso_uses_profile_values_when_making_new_session(
        self,
        sso_cmd_factory,
        ptk_stubber,
        aws_config,
        sso_stubber_factory,
        stub_simple_single_item_sso_responses,
        mock_do_sso_login,
        args,
        parsed_globals,
        configure_sso_using_new_session_from_legacy_profile_inputs,
        aws_config_lines_for_existing_legacy_profile,
        account_id,
        role_name,
        existing_profile_name,
        default_sso_scope,
    ):
        write_aws_config(
            aws_config, lines=aws_config_lines_for_existing_legacy_profile
        )
        session = StubbedSession(profile=existing_profile_name)

        inputs = configure_sso_using_new_session_from_legacy_profile_inputs
        inputs.skip_account_and_role_selection()
        ptk_stubber.user_inputs = inputs

        sso_stubber = sso_stubber_factory(session)
        stub_simple_single_item_sso_responses(
            account_id, role_name, sso_stubber
        )
        sso_cmd = sso_cmd_factory(session=session)
        sso_cmd(args, parsed_globals)

        self.assert_do_sso_login_call(
            mock_do_sso_login,
            session,
            expected_session_name=inputs.session_prompt.answer,
            expected_sso_region=inputs.sso_region_prompt.expected_default,
            expected_start_url=inputs.start_url_prompt.expected_default,
            expected_scopes=[default_sso_scope],
            expected_force_refresh=True,
        )
        assert_aws_config(
            aws_config,
            expected_lines=aws_config_lines_for_existing_legacy_profile
            + [
                f"sso_session = {inputs.session_prompt.answer}",
                f"[sso-session {inputs.session_prompt.answer}]",
                f"sso_start_url = {inputs.start_url_prompt.expected_default}",
                f"sso_region = {inputs.sso_region_prompt.expected_default}",
                f"sso_registration_scopes = {default_sso_scope}",
            ],
        )

    def test_configure_sso_suggests_values_from_sessions(
        self,
        sso_cmd_factory,
        ptk_stubber,
        aws_config,
        sso_stubber_factory,
        stub_simple_single_item_sso_responses,
        aws_config_lines_for_existing_sso_session,
        existing_sso_session,
        existing_start_url,
        args,
        parsed_globals,
        configure_sso_using_new_session_inputs,
        account_id,
        role_name,
        all_sso_oidc_regions,
    ):
        write_aws_config(
            aws_config, lines=aws_config_lines_for_existing_sso_session
        )
        session = StubbedSession()

        inputs = configure_sso_using_new_session_inputs
        inputs.skip_account_and_role_selection()
        inputs.session_prompt.expected_completions = [existing_sso_session]
        inputs.start_url_prompt.expected_completions = [existing_start_url]
        inputs.sso_region_prompt.expected_completions = all_sso_oidc_regions
        inputs.output_prompt.expected_completions = list(
            CLI_OUTPUT_FORMATS.keys()
        )
        ptk_stubber.user_inputs = inputs

        sso_stubber = sso_stubber_factory(session)
        stub_simple_single_item_sso_responses(
            account_id, role_name, sso_stubber
        )
        sso_cmd = sso_cmd_factory(session=session)
        assert sso_cmd(args, parsed_globals) == 0

    def test_single_account_single_role_device_code_fallback(
        self,
        sso_cmd,
        ptk_stubber,
        aws_config,
        stub_simple_single_item_sso_responses,
        mock_do_sso_login,
        botocore_session,
        args,
        parsed_globals,
        configure_sso_legacy_inputs,
        account_id,
        role_name,
    ):
        inputs = configure_sso_legacy_inputs
        inputs.skip_account_and_role_selection()
        ptk_stubber.user_inputs = inputs
        stub_simple_single_item_sso_responses(account_id, role_name)

        sso_cmd(["--use-device-code"], parsed_globals)
        self.assert_do_sso_login_call(
            mock_do_sso_login,
            botocore_session,
            expected_sso_region=inputs.sso_region_prompt.answer,
            expected_start_url=inputs.start_url_prompt.answer,
            expected_use_device_code=True,
        )
        assert_aws_config(
            aws_config,
            expected_lines=[
                f"[profile {inputs.profile_prompt.answer}]",
                f"sso_start_url = {inputs.start_url_prompt.answer}",
                f"sso_region = {inputs.sso_region_prompt.answer}",
                f"sso_account_id = {account_id}",
                f"sso_role_name = {role_name}",
                f"region = {inputs.region_prompt.answer}",
                f"output = {inputs.output_prompt.answer}",
            ],
        )

class TestPrintConclusion:
    def test_print_conclusion_default_profile_with_credentials(self, sso_cmd, capsys):
        sso_cmd._print_conclusion(True, 'default')
        captured = capsys.readouterr()
        assert "The AWS CLI is now configured to use the default profile." in captured.out
        assert "aws sts get-caller-identity" in captured.out

    def test_print_conclusion_named_profile_with_credentials(self, sso_cmd, capsys):
        profile_name = "test-profile"
        sso_cmd._print_conclusion(True, profile_name)
        captured = capsys.readouterr()
        assert f"To use this profile, specify the profile name using --profile" in captured.out
        assert f"aws sts get-caller-identity --profile {profile_name}" in captured.out

    def test_print_conclusion_sso_configuration(self, sso_cmd, capsys):
        profile_name = "test-profile"
        sso_cmd._print_conclusion(False, profile_name)
        captured = capsys.readouterr()
        assert f"Successfully configured SSO for profile: {profile_name}" in captured.out

    def test_print_conclusion_default_profile_case_insensitive(selfself, sso_cmd, capsys):
        sso_cmd._print_conclusion(True, 'DEFAULT')
        captured = capsys.readouterr()
        assert "The AWS CLI is now configured to use the default profile." in captured.out
        assert "aws sts get-caller-identity" in captured.out

    def test_print_conclusion_empty_profile_name(self, sso_cmd, capsys):
        sso_cmd._print_conclusion(True, '')
        captured = capsys.readouterr()
        assert "To use this profile, specify the profile name using --profile" in captured.out
        assert "aws sts get-caller-identity --profile" in captured.out

class TestConfigureSSOSessionCommand:
    def test_new_sso_session(
        self,
        sso_session_cmd,
        ptk_stubber,
        aws_config,
        configure_sso_session_inputs,
        args,
        parsed_globals,
        capsys,
    ):
        inputs = configure_sso_session_inputs
        ptk_stubber.user_inputs = inputs
        sso_session_cmd(args, parsed_globals)
        assert_aws_config(
            aws_config,
            expected_lines=[
                f"[sso-session {inputs.session_prompt.answer}]",
                f"sso_start_url = {inputs.start_url_prompt.answer}",
                f"sso_region = {inputs.sso_region_prompt.answer}",
                f"sso_registration_scopes = {inputs.scopes_prompt.answer}",
            ],
        )
        expected_login = (
            f"aws sso login --sso-session {inputs.session_prompt.answer}"
        )
        assert expected_login in capsys.readouterr().out

    def test_can_used_default_scope_for_new_session(
        self,
        sso_session_cmd,
        ptk_stubber,
        aws_config,
        configure_sso_session_inputs,
        args,
        parsed_globals,
        default_sso_scope,
    ):
        inputs = configure_sso_session_inputs
        inputs.scopes_prompt.answer = ""
        ptk_stubber.user_inputs = inputs
        sso_session_cmd(args, parsed_globals)
        assert_aws_config(
            aws_config,
            expected_lines=[
                f"[sso-session {inputs.session_prompt.answer}]",
                f"sso_start_url = {inputs.start_url_prompt.answer}",
                f"sso_region = {inputs.sso_region_prompt.answer}",
                f"sso_registration_scopes = {default_sso_scope}",
            ],
        )

    def test_reuse_existing_sso_session_configurations(
        self,
        sso_session_cmd_factory,
        ptk_stubber,
        aws_config,
        aws_config_lines_for_existing_sso_session,
        configure_sso_session_with_existing_defaults_inputs,
        args,
        parsed_globals,
        existing_sso_session,
    ):
        write_aws_config(
            aws_config, lines=aws_config_lines_for_existing_sso_session
        )
        inputs = configure_sso_session_with_existing_defaults_inputs
        inputs.clear_answers()
        inputs.session_prompt.answer = existing_sso_session
        ptk_stubber.user_inputs = inputs

        sso_session_cmd = sso_session_cmd_factory(session=StubbedSession())
        sso_session_cmd(args, parsed_globals)
        assert_aws_config(
            aws_config, expected_lines=aws_config_lines_for_existing_sso_session
        )

    def test_override_existing_sso_session_configurations(
        self,
        sso_session_cmd_factory,
        ptk_stubber,
        aws_config,
        aws_config_lines_for_existing_sso_session,
        configure_sso_session_with_existing_defaults_inputs,
        args,
        parsed_globals,
        existing_sso_session,
    ):
        write_aws_config(
            aws_config, lines=aws_config_lines_for_existing_sso_session
        )
        inputs = configure_sso_session_with_existing_defaults_inputs
        inputs.session_prompt.answer = existing_sso_session
        ptk_stubber.user_inputs = inputs

        sso_session_cmd = sso_session_cmd_factory(session=StubbedSession())
        sso_session_cmd(args, parsed_globals)
        assert_aws_config(
            aws_config,
            expected_lines=[
                f"[sso-session {existing_sso_session}]",
                f"sso_start_url = {inputs.start_url_prompt.answer}",
                f"sso_region = {inputs.sso_region_prompt.answer}",
                f"sso_registration_scopes = {inputs.scopes_prompt.answer}",
            ],
        )


class TestPTKPrompt(unittest.TestCase):
    def setUp(self):
        self.mock_prompter = mock.Mock(spec=ptk_prompt)
        self.prompter = PTKPrompt(prompter=self.mock_prompter)

    def test_returns_input(self):
        self.mock_prompter.return_value = "new_value"
        response = self.prompter.get_value("default_value", "Prompt Text")
        self.assertEqual(response, "new_value")

    def test_user_hits_enter_returns_current(self):
        self.mock_prompter.return_value = ""
        response = self.prompter.get_value("default_value", "Prompt Text")
        # We convert the empty string to the default value
        self.assertEqual(response, "default_value")

    def assert_expected_completions(self, completions):
        # The order of the completion list can vary becuase it comes from the
        # dict's keys. Asserting that each expected completion is in the list
        _, kwargs = self.mock_prompter.call_args_list[0]
        completer = kwargs["completer"]
        self.assertEqual(len(completions), len(completer.words))
        for completion in completions:
            self.assertIn(completion, completer.words)

    def assert_expected_meta_dict(self, meta_dict):
        _, kwargs = self.mock_prompter.call_args_list[0]
        self.assertEqual(kwargs["completer"].meta_dict, meta_dict)

    def assert_expected_validator(self, validator):
        _, kwargs = self.mock_prompter.call_args_list[0]
        self.assertEqual(kwargs["validator"], validator)

    def assert_expected_toolbar(self, expected_toolbar):
        _, kwargs = self.mock_prompter.call_args_list[0]
        self.assertEqual(kwargs["bottom_toolbar"], expected_toolbar)

    def assert_expected_prompt_message(self, expected_message):
        args, _ = self.mock_prompter.call_args_list[0]
        self.assertEqual(args[0], expected_message)

    def test_handles_list_completions(self):
        completions = ["a", "b"]
        self.prompter.get_value("", "", completions=completions)
        self.assert_expected_completions(completions)

    def test_handles_dict_completions(self):
        descriptions = {
            "a": "the letter a",
            "b": "the letter b",
        }
        expected_completions = ["a", "b"]
        self.prompter.get_value("", "", completions=descriptions)
        self.assert_expected_completions(expected_completions)
        self.assert_expected_meta_dict(descriptions)

    def test_passes_validator(self):
        validator = DummyValidator()
        self.prompter.get_value("", "", validator=validator)
        self.assert_expected_validator(validator)

    def test_strips_extra_whitespace(self):
        self.mock_prompter.return_value = "  no_whitespace \t  "
        response = self.prompter.get_value("default_value", "Prompt Text")
        self.assertEqual(response, "no_whitespace")

    def test_can_provide_toolbar(self):
        toolbar = "Toolbar content"
        self.prompter.get_value("default_value", "Prompt Text", toolbar=toolbar)
        self.assert_expected_toolbar(toolbar)

    def test_can_provide_prompt_format(self):
        self.prompter.get_value(
            "default_value",
            "Prompt Text",
            prompt_fmt="{prompt_text} [default: {current_value}]: ",
        )
        self.assert_expected_prompt_message(
            "Prompt Text [default: default_value]: "
        )


class TestSSOSessionConfigurationPrompter:
    def get_toolbar_content(self, toolbar_render):
        formatted_text = toolbar_render()
        content_lines = [line for _, line in formatted_text]
        return "".join(content_lines)

    def test_prompt_for_session_name(self, sso_config_prompter, ptk_stubber):
        ptk_stubber.user_inputs = UserInputs(
            session_prompt=RequiredSessionPrompt("dev")
        )
        assert sso_config_prompter.prompt_for_sso_session() == "dev"
        assert sso_config_prompter.sso_session == "dev"

    def test_prompt_for_session_name_opt_out_of_required(
        self, sso_config_prompter, ptk_stubber
    ):
        ptk_stubber.user_inputs = UserInputs(
            session_prompt=RecommendedSessionPrompt("")
        )
        answer = sso_config_prompter.prompt_for_sso_session(required=False)
        assert answer is None
        assert sso_config_prompter.sso_session is None

    def test_manually_set_session_name(self, sso_config_prompter):
        sso_config_prompter.sso_session = "override"
        assert sso_config_prompter.sso_session == "override"

    def test_setting_session_name_updates_sso_config(
        self,
        sso_config_prompter_factory,
        aws_config,
        aws_config_lines_for_existing_sso_session,
        existing_sso_session,
        existing_sso_region,
        existing_start_url,
        existing_scopes,
    ):
        write_aws_config(aws_config, aws_config_lines_for_existing_sso_session)
        session = StubbedSession()
        sso_config_prompter = sso_config_prompter_factory(session=session)
        sso_config_prompter.sso_session = existing_sso_session
        assert sso_config_prompter.sso_session_config == {
            "sso_region": existing_sso_region,
            "sso_start_url": existing_start_url,
            "sso_registration_scopes": existing_scopes,
        }

    def test_prompt_for_session_suggests_existing_sessions(
        self,
        sso_config_prompter_factory,
        ptk_stubber,
        aws_config,
        aws_config_lines_for_existing_sso_session,
        existing_sso_session,
    ):
        write_aws_config(aws_config, aws_config_lines_for_existing_sso_session)
        session = StubbedSession()
        sso_config_prompter = sso_config_prompter_factory(session=session)

        ptk_stubber.user_inputs = UserInputs(
            session_prompt=RequiredSessionPrompt(
                "dev", expected_completions=[existing_sso_session]
            ),
        )
        assert sso_config_prompter.prompt_for_sso_session() == "dev"

    def test_prompt_for_session_name_shows_session_config_in_toolbar(
        self,
        sso_config_prompter_factory,
        ptk_stubber,
        mock_ptk_app,
        aws_config,
        aws_config_lines_for_existing_sso_session,
        existing_sso_session,
        existing_start_url,
        existing_sso_region,
        existing_scopes,
    ):
        write_aws_config(aws_config, aws_config_lines_for_existing_sso_session)
        session = StubbedSession()
        mock_ptk_prompt = mock.Mock(ptk_prompt)
        prompter = PTKPrompt(mock_ptk_prompt)
        sso_config_prompter = sso_config_prompter_factory(
            session=session,
            prompt=prompter,
        )
        sso_config_prompter.prompt_for_sso_session()
        toolbar_render = mock_ptk_prompt.call_args_list[0][1]["bottom_toolbar"]
        mock_ptk_app.current_buffer.document.text = existing_sso_session
        mock_ptk_app.output.get_size.return_value.columns = 1
        actual_toolbar_content = self.get_toolbar_content(toolbar_render)
        expected_sso_config_in_toolbar = json.dumps(
            {
                "sso_start_url": existing_start_url,
                "sso_region": existing_sso_region,
                "sso_registration_scopes": existing_scopes,
            },
            indent=2,
        )
        assert expected_sso_config_in_toolbar in actual_toolbar_content

    def test_prompt_for_start_url(self, sso_config_prompter, ptk_stubber):
        url = "https://start.here"
        ptk_stubber.user_inputs = UserInputs(
            start_url_prompt=StartUrlPrompt(url)
        )
        assert sso_config_prompter.prompt_for_sso_start_url() == url
        assert sso_config_prompter.sso_session_config == {"sso_start_url": url}

    def test_prompt_for_start_url_reuse_existing_configuration(
        self, sso_config_prompter, ptk_stubber, existing_start_url
    ):
        sso_config_prompter.sso_session_config[
            "sso_start_url"
        ] = existing_start_url
        ptk_stubber.user_inputs = UserInputs(
            start_url_prompt=StartUrlPrompt(
                "", expected_default=existing_start_url
            )
        )
        answer = sso_config_prompter.prompt_for_sso_start_url()
        assert answer == existing_start_url
        assert sso_config_prompter.sso_session_config == {
            "sso_start_url": existing_start_url
        }

    def test_prompt_for_start_url_suggests_previously_used_start_urls(
        self,
        sso_config_prompter_factory,
        ptk_stubber,
        aws_config,
        aws_config_lines_for_existing_sso_session,
        existing_start_url,
    ):
        write_aws_config(aws_config, aws_config_lines_for_existing_sso_session)
        session = StubbedSession()
        url = "https://start.here"
        ptk_stubber.user_inputs = UserInputs(
            start_url_prompt=StartUrlPrompt(
                answer=url, expected_completions=[existing_start_url]
            )
        )
        sso_config_prompter = sso_config_prompter_factory(session=session)
        answer = sso_config_prompter.prompt_for_sso_start_url()
        assert answer == url

    def test_prompt_for_sso_region(self, sso_config_prompter, ptk_stubber):
        sso_region = "us-west-2"
        ptk_stubber.user_inputs = UserInputs(
            sso_region_prompt=SSORegionPrompt(sso_region)
        )
        assert sso_config_prompter.prompt_for_sso_region() == sso_region
        assert sso_config_prompter.sso_session_config == {
            "sso_region": sso_region
        }

    def test_prompt_for_sso_region_reuse_existing_configuration(
        self, sso_config_prompter, ptk_stubber, existing_sso_region
    ):
        sso_config_prompter.sso_session_config[
            "sso_region"
        ] = existing_sso_region
        ptk_stubber.user_inputs = UserInputs(
            sso_region_prompt=SSORegionPrompt(
                "", expected_default=existing_sso_region
            )
        )
        answer = sso_config_prompter.prompt_for_sso_region()
        assert answer == existing_sso_region
        assert sso_config_prompter.sso_session_config == {
            "sso_region": existing_sso_region
        }

    def test_prompt_for_sso_region_suggests_all_valid_sso_oidc_regions(
        self, sso_config_prompter, ptk_stubber, all_sso_oidc_regions
    ):
        sso_region = "us-west-2"
        ptk_stubber.user_inputs = UserInputs(
            sso_region_prompt=SSORegionPrompt(
                sso_region, expected_completions=all_sso_oidc_regions
            ),
        )
        assert sso_config_prompter.prompt_for_sso_region() == sso_region

    def test_prompt_for_scopes(
        self, sso_config_prompter, ptk_stubber, default_sso_scope
    ):
        scopes = "scope-1, scope-2"
        parsed_scopes = ["scope-1", "scope-2"]
        ptk_stubber.user_inputs = UserInputs(
            scopes_prompt=ScopesPrompt(
                scopes, expected_default=default_sso_scope
            )
        )
        answer = sso_config_prompter.prompt_for_sso_registration_scopes()
        assert answer == parsed_scopes
        assert sso_config_prompter.sso_session_config == {
            "sso_registration_scopes": scopes
        }

    def test_prompt_for_scopes_reuse_existing_configuration(
        self, sso_config_prompter, ptk_stubber, existing_scopes
    ):
        sso_config_prompter.sso_session_config[
            "sso_registration_scopes"
        ] = existing_scopes
        ptk_stubber.user_inputs = UserInputs(
            scopes_prompt=ScopesPrompt("", expected_default=existing_scopes)
        )
        answer = sso_config_prompter.prompt_for_sso_registration_scopes()
        assert answer == parse_sso_registration_scopes(existing_scopes)
        assert sso_config_prompter.sso_session_config == {
            "sso_registration_scopes": existing_scopes
        }

    def test_prompt_for_scopes_used_defaults_account_scope(
        self, sso_config_prompter, ptk_stubber, default_sso_scope
    ):
        ptk_stubber.user_inputs = UserInputs(
            scopes_prompt=ScopesPrompt("", expected_default=default_sso_scope)
        )
        answer = sso_config_prompter.prompt_for_sso_registration_scopes()
        assert answer == [default_sso_scope]
        assert sso_config_prompter.sso_session_config == {
            "sso_registration_scopes": default_sso_scope
        }

    def test_prompt_for_scopes_suggest_known_and_previously_used_scopes(
        self,
        sso_config_prompter_factory,
        ptk_stubber,
        aws_config,
        aws_config_lines_for_existing_sso_session,
        default_sso_scope,
        existing_scopes,
    ):
        write_aws_config(aws_config, aws_config_lines_for_existing_sso_session)
        session = StubbedSession()
        ptk_stubber.user_inputs = UserInputs(
            scopes_prompt=ScopesPrompt(
                "",
                expected_default=default_sso_scope,
                expected_completions=[default_sso_scope]
                + parse_sso_registration_scopes(existing_scopes),
            )
        )
        sso_config_prompter = sso_config_prompter_factory(session=session)
        answer = sso_config_prompter.prompt_for_sso_registration_scopes()
        assert answer == [default_sso_scope]


def passes_validator(validator, text):
    document = mock.Mock(spec=Document)
    document.text = text
    try:
        validator.validate(document)
    except ValidationError:
        return False
    return True


@pytest.mark.parametrize(
    "validator_cls,input_value,default,is_valid",
    [
        # StartUrlValidator cases
        (StartUrlValidator, "https://d-abc123.awsapps.com/start", None, True),
        (StartUrlValidator, "https://d-abc123.awsapps.com/start#", None, True),
        (StartUrlValidator, "https://d-abc123.awsapps.com/start/", None, True),
        (
            StartUrlValidator,
            "https://d-abc123.awsapps.com/start-beta",
            None,
            True,
        ),
        (StartUrlValidator, "https://start.url", None, True),
        (StartUrlValidator, "", "https://some.default", True),
        (StartUrlValidator, "", None, False),
        (StartUrlValidator, "d-abc123", None, False),
        (StartUrlValidator, "foo bar baz", None, False),
        # RequiredInputValidator cases
        (RequiredInputValidator, "input-value", "default-value", True),
        (RequiredInputValidator, "input-value", None, True),
        (RequiredInputValidator, "", "default-value", True),
        (RequiredInputValidator, "", None, False),
        # ScopesValidator cases
        (ScopesValidator, "sso:account:access", "sso:account:access", True),
        (ScopesValidator, "", "sso:account:access", True),
        (ScopesValidator, "value-1, value-2", None, True),
        (ScopesValidator, " value-1, value-2 ", None, True),
        (ScopesValidator, "value-1 value-2", None, False),
        (ScopesValidator, "value-1, value-2 value3", None, False),
    ],
)
def test_validators(validator_cls, input_value, default, is_valid):
    validator = validator_cls(default)
    assert passes_validator(validator, input_value) == is_valid


class TestDisplayAccount(unittest.TestCase):
    def setUp(self):
        self.account_id = "1234"
        self.email_address = "test@test.com"
        self.account_name = "FooBar"
        self.account = {
            "accountId": self.account_id,
            "emailAddress": self.email_address,
            "accountName": self.account_name,
        }

    def test_display_account_all_fields(self):
        account_str = display_account(self.account)
        self.assertIn(self.account_name, account_str)
        self.assertIn(self.email_address, account_str)
        self.assertIn(self.account_id, account_str)

    def test_display_account_missing_email(self):
        del self.account["emailAddress"]
        account_str = display_account(self.account)
        self.assertIn(self.account_name, account_str)
        self.assertNotIn(self.email_address, account_str)
        self.assertIn(self.account_id, account_str)

    def test_display_account_missing_name(self):
        del self.account["accountName"]
        account_str = display_account(self.account)
        self.assertNotIn(self.account_name, account_str)
        self.assertIn(self.email_address, account_str)
        self.assertIn(self.account_id, account_str)

    def test_display_account_missing_name_and_email(self):
        del self.account["accountName"]
        del self.account["emailAddress"]
        account_str = display_account(self.account)
        self.assertNotIn(self.account_name, account_str)
        self.assertNotIn(self.email_address, account_str)
        self.assertIn(self.account_id, account_str)
