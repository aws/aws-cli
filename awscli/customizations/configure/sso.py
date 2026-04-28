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
import collections
import itertools
import json
import logging
import re

from botocore.utils import is_valid_endpoint_url
from prompt_toolkit import prompt as ptk_prompt
from prompt_toolkit.application import get_app
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import ValidationError, Validator

from awscli.customizations.sso.utils import (
    parse_sso_registration_scopes,
)

logger = logging.getLogger(__name__)


class ValidatorWithDefault(Validator):
    def __init__(self, default=None):
        super(ValidatorWithDefault, self).__init__()
        self._default = default

    def _raise_validation_error(self, document, message):
        index = len(document.text)
        raise ValidationError(index, message)


class StartUrlValidator(ValidatorWithDefault):
    def validate(self, document):
        # If there's a default, allow an empty prompt
        if not document.text and self._default:
            return
        if not is_valid_endpoint_url(document.text):
            self._raise_validation_error(document, 'Not a valid Start URL')


class RequiredInputValidator(ValidatorWithDefault):
    def validate(self, document):
        if document.text or self._default:
            return
        self._raise_validation_error(document, 'A value is required')


class ScopesValidator(ValidatorWithDefault):
    def validate(self, document):
        # If there's a default, allow an empty prompt
        if not document.text and self._default:
            return
        if not self._is_comma_separated_list(document.text):
            self._raise_validation_error(
                document, 'Scope values must be separated by commas'
            )

    def _is_comma_separated_list(self, value):
        scopes = value.split(',')
        for scope in scopes:
            if re.findall(r'\s', scope.strip()):
                return False
        return True


class PTKPrompt:
    _DEFAULT_PROMPT_FORMAT = '{prompt_text} [{current_value}]: '

    def __init__(self, prompter=None):
        if prompter is None:
            prompter = ptk_prompt
        self._prompter = prompter

    def _create_completer(self, completions):
        if completions is None:
            completions = []
        completer_kwargs = {
            'words': completions,
            'pattern': re.compile(r'\S+'),
        }
        if isinstance(completions, dict):
            completer_kwargs['meta_dict'] = completions
            completer_kwargs['words'] = list(completions.keys())
        return WordCompleter(**completer_kwargs)

    def get_value(
        self,
        current_value,
        prompt_text='',
        completions=None,
        validator=None,
        toolbar=None,
        prompt_fmt=None,
    ):
        if prompt_fmt is None:
            prompt_fmt = self._DEFAULT_PROMPT_FORMAT
        prompt_string = prompt_fmt.format(
            prompt_text=prompt_text, current_value=current_value
        )
        prompter_kwargs = {
            'validator': validator,
            'validate_while_typing': False,
            'completer': self._create_completer(completions),
            'complete_while_typing': True,
            'style': self._get_prompt_style(),
        }
        if toolbar:
            prompter_kwargs['bottom_toolbar'] = toolbar
            prompter_kwargs['refresh_interval'] = 0.2
        response = self._prompter(prompt_string, **prompter_kwargs)
        # Strip any extra white space
        response = response.strip()
        if not response:
            # If the user hits enter, we return the current/default value
            response = current_value
        return response

    def _get_prompt_style(self):
        return Style.from_dict(
            {
                'bottom-toolbar': 'noreverse',
            }
        )


class SSOSessionConfigurationPrompter:
    _DEFAULT_SSO_SCOPE = 'sso:account:access'
    _KNOWN_SSO_SCOPES = {
        'sso:account:access': (
            'Grants access to AWS IAM Identity Center accounts and permission '
            'sets'
        )
    }

    def __init__(self, botocore_session, prompter):
        self._botocore_session = botocore_session
        self._prompter = prompter
        self._sso_sessions = self._botocore_session.full_config.get(
            'sso_sessions', {}
        )
        self._sso_session = None
        self.sso_session_config = {}

    @property
    def sso_session(self):
        return self._sso_session

    @sso_session.setter
    def sso_session(self, value):
        self._sso_session = value
        self.sso_session_config = self._sso_sessions.get(
            self._sso_session, {}
        ).copy()

    def prompt_for_sso_session(self, required=True):
        prompt_text = 'SSO session name'
        prompt_fmt = None
        validator_cls = None
        if required:
            validator_cls = RequiredInputValidator
        if not self.sso_session:
            prompt_fmt = f'{prompt_text}: '
            if not required:
                prompt_fmt = f'{prompt_text} (Recommended): '
        sso_session = self._prompt_for(
            'sso_session',
            prompt_text,
            completions=sorted(self._sso_sessions),
            toolbar=self._get_sso_session_toolbar,
            validator_cls=validator_cls,
            prompt_fmt=prompt_fmt,
            current_value=self.sso_session,
        )
        self.sso_session = sso_session
        return sso_session

    def prompt_for_sso_start_url(self):
        return self._prompt_for(
            'sso_start_url',
            'SSO start URL',
            completions=self._get_potential_start_urls(),
            validator_cls=StartUrlValidator,
        )

    def prompt_for_sso_region(self):
        return self._prompt_for(
            'sso_region',
            'SSO region',
            completions=self._get_potential_sso_regions(),
            validator_cls=RequiredInputValidator,
        )

    def prompt_for_sso_registration_scopes(self):
        if 'sso_registration_scopes' not in self.sso_session_config:
            self.sso_session_config['sso_registration_scopes'] = (
                self._DEFAULT_SSO_SCOPE
            )
        raw_scopes = self._prompt_for(
            'sso_registration_scopes',
            'SSO registration scopes',
            completions=self._get_potential_sso_registrations_scopes(),
            validator_cls=ScopesValidator,
        )
        return parse_sso_registration_scopes(raw_scopes)

    def _prompt_for(
        self,
        config_name,
        text,
        completions=None,
        validator_cls=None,
        toolbar=None,
        prompt_fmt=None,
        current_value=None,
    ):
        if current_value is None:
            current_value = self.sso_session_config.get(config_name)
        validator = None
        if validator_cls:
            validator = validator_cls(current_value)
        value = self._prompter.get_value(
            current_value,
            text,
            completions=completions,
            validator=validator,
            toolbar=toolbar,
            prompt_fmt=prompt_fmt,
        )
        if value:
            self.sso_session_config[config_name] = value
        return value

    def _get_sso_session_toolbar(self):
        current_input = get_app().current_buffer.document.text
        if current_input in self._sso_sessions:
            selected_sso_config = self._sso_sessions[current_input]
            return FormattedText(
                [
                    ('', self._get_toolbar_border()),
                    ('', '\n'),
                    (
                        'bold',
                        f'Configuration for SSO session: {current_input}\n\n',
                    ),
                    ('', json.dumps(selected_sso_config, indent=2)),
                ]
            )

    def _get_toolbar_border(self):
        horizontal_line_char = '\u2500'
        return horizontal_line_char * get_app().output.get_size().columns

    def _get_potential_start_urls(self):
        profiles = self._botocore_session.full_config.get('profiles', {})
        configs_to_search = itertools.chain(
            profiles.values(), self._sso_sessions.values()
        )
        potential_start_urls = set()
        for config_to_search in configs_to_search:
            if 'sso_start_url' in config_to_search:
                start_url = config_to_search['sso_start_url']
                potential_start_urls.add(start_url)
        return list(potential_start_urls)

    def _get_potential_sso_regions(self):
        return self._botocore_session.get_available_regions('sso-oidc')

    def _get_potential_sso_registrations_scopes(self):
        potential_scopes = self._KNOWN_SSO_SCOPES.copy()
        scopes_to_sessions = self._get_previously_used_scopes_to_sso_sessions()
        for scope, sso_sessions in scopes_to_sessions.items():
            if scope not in potential_scopes:
                potential_scopes[scope] = (
                    f'Used in SSO sessions: {", ".join(sso_sessions)}'
                )
        return potential_scopes

    def _get_previously_used_scopes_to_sso_sessions(self):
        scopes_to_sessions = collections.defaultdict(list)
        for sso_session, sso_session_config in self._sso_sessions.items():
            if 'sso_registration_scopes' in sso_session_config:
                parsed_scopes = parse_sso_registration_scopes(
                    sso_session_config['sso_registration_scopes']
                )
                for parsed_scope in parsed_scopes:
                    scopes_to_sessions[parsed_scope].append(sso_session)
        return scopes_to_sessions
