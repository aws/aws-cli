# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import pytest

from awscli.customizations.exceptions import ConfigurationError
from awscli.testutils import mock


class TestConfigureSSOVanityUrlResolution:
    def _create_command(self):
        from awscli.customizations.configure.sso_commands import (
            ConfigureSSOCommand,
        )

        session = mock.Mock()
        session.full_config = {'sso_sessions': {}}
        cmd = ConfigureSSOCommand(session)
        cmd._sso_session_prompter = mock.Mock()
        return cmd

    def test_vanity_url_skips_region_prompt(self):
        cmd = self._create_command()
        cmd._sso_session_prompter.prompt_for_sso_start_url.return_value = (
            'https://aws.mycompany.com'
        )
        cmd._sso_session_prompter.sso_session_config = {}
        with (
            mock.patch(
                'awscli.customizations.configure.sso_commands.is_aws_owned_domain',
                return_value=False,
            ),
            mock.patch(
                'awscli.customizations.configure.sso_commands.resolve_start_url',
                return_value=(
                    'https://ssoins-abc.portal.us-east-1.app.aws',
                    'us-east-1',
                ),
            ),
        ):
            start_url, region, resolved_url = (
                cmd._prompt_for_sso_start_url_and_sso_region()
            )

        assert start_url == 'https://aws.mycompany.com'
        assert region == 'us-east-1'
        assert resolved_url == 'https://ssoins-abc.portal.us-east-1.app.aws'
        cmd._sso_session_prompter.prompt_for_sso_region.assert_not_called()

    def test_vanity_url_resolution_failure_falls_back_to_prompt(self):
        cmd = self._create_command()
        cmd._sso_session_prompter.prompt_for_sso_start_url.return_value = (
            'https://aws.mycompany.com'
        )
        cmd._sso_session_prompter.prompt_for_sso_region.return_value = (
            'eu-west-1'
        )
        with (
            mock.patch(
                'awscli.customizations.configure.sso_commands.is_aws_owned_domain',
                return_value=False,
            ),
            mock.patch(
                'awscli.customizations.configure.sso_commands.resolve_start_url',
                side_effect=ConfigurationError("Failed to resolve"),
            ),
        ):
            start_url, region, resolved_url = (
                cmd._prompt_for_sso_start_url_and_sso_region()
            )

        assert start_url == 'https://aws.mycompany.com'
        assert region == 'eu-west-1'
        assert resolved_url is None
        cmd._sso_session_prompter.prompt_for_sso_region.assert_called_once()

    def test_direct_url_prompts_for_region(self):
        cmd = self._create_command()
        cmd._sso_session_prompter.prompt_for_sso_start_url.return_value = (
            'https://ssoins-abc.portal.us-west-2.app.aws'
        )
        cmd._sso_session_prompter.prompt_for_sso_region.return_value = (
            'us-west-2'
        )
        with (
            mock.patch(
                'awscli.customizations.configure.sso_commands.is_aws_owned_domain',
                return_value=True,
            ),
            mock.patch(
                'awscli.customizations.configure.sso_commands.resolve_start_url',
            ) as mock_resolve,
        ):
            start_url, region, resolved_url = (
                cmd._prompt_for_sso_start_url_and_sso_region()
            )

        assert start_url == 'https://ssoins-abc.portal.us-west-2.app.aws'
        assert region == 'us-west-2'
        assert resolved_url is None
        cmd._sso_session_prompter.prompt_for_sso_region.assert_called_once()
        mock_resolve.assert_not_called()

    def test_vanity_url_persists_resolved_region_in_session_config(self):
        cmd = self._create_command()
        cmd._sso_session_prompter.prompt_for_sso_start_url.return_value = (
            'https://aws.mycompany.com'
        )
        cmd._sso_session_prompter.sso_session_config = {}
        with (
            mock.patch(
                'awscli.customizations.configure.sso_commands.is_aws_owned_domain',
                return_value=False,
            ),
            mock.patch(
                'awscli.customizations.configure.sso_commands.resolve_start_url',
                return_value=(
                    'https://ssoins-abc.portal.us-east-1.app.aws',
                    'us-east-1',
                ),
            ),
        ):
            cmd._prompt_for_sso_start_url_and_sso_region()

        assert (
            cmd._sso_session_prompter.sso_session_config['sso_region']
            == 'us-east-1'
        )


class TestConfigureSSOSessionVanityUrlResolution:
    def _create_command(self):
        from awscli.customizations.configure.sso_commands import (
            ConfigureSSOSessionCommand,
        )

        session = mock.Mock()
        session.full_config = {'sso_sessions': {}}
        cmd = ConfigureSSOSessionCommand(session)
        cmd._sso_session_prompter = mock.Mock()
        cmd._sso_session_prompter.sso_session_config = {}
        cmd._init_prompt_toolkit = mock.Mock()
        return cmd

    def test_vanity_url_skips_region_prompt(self):
        cmd = self._create_command()
        cmd._sso_session_prompter.prompt_for_sso_start_url.return_value = (
            'https://aws.mycompany.com'
        )
        with (
            mock.patch(
                'awscli.customizations.configure.sso_commands.is_aws_owned_domain',
                return_value=False,
            ),
            mock.patch(
                'awscli.customizations.configure.sso_commands.resolve_start_url',
                return_value=(
                    'https://ssoins-abc.portal.us-east-1.app.aws',
                    'us-east-1',
                ),
            ),
            mock.patch.object(cmd, '_write_sso_configuration'),
            mock.patch.object(cmd, '_print_configuration_success'),
        ):
            cmd._run_main(mock.Mock(), mock.Mock())

        cmd._sso_session_prompter.prompt_for_sso_region.assert_not_called()
        assert (
            cmd._sso_session_prompter.sso_session_config['sso_region']
            == 'us-east-1'
        )

    def test_vanity_url_failure_falls_back_to_prompt(self):
        cmd = self._create_command()
        cmd._sso_session_prompter.prompt_for_sso_start_url.return_value = (
            'https://aws.mycompany.com'
        )
        with (
            mock.patch(
                'awscli.customizations.configure.sso_commands.is_aws_owned_domain',
                return_value=False,
            ),
            mock.patch(
                'awscli.customizations.configure.sso_commands.resolve_start_url',
                side_effect=ConfigurationError("Failed to resolve"),
            ),
            mock.patch.object(cmd, '_write_sso_configuration'),
            mock.patch.object(cmd, '_print_configuration_success'),
        ):
            cmd._run_main(mock.Mock(), mock.Mock())

        cmd._sso_session_prompter.prompt_for_sso_region.assert_called_once()

    def test_direct_url_prompts_for_region(self):
        cmd = self._create_command()
        cmd._sso_session_prompter.prompt_for_sso_start_url.return_value = (
            'https://ssoins-abc.portal.us-west-2.app.aws'
        )
        with (
            mock.patch(
                'awscli.customizations.configure.sso_commands.is_aws_owned_domain',
                return_value=True,
            ),
            mock.patch(
                'awscli.customizations.configure.sso_commands.resolve_start_url',
            ) as mock_resolve,
            mock.patch.object(cmd, '_write_sso_configuration'),
            mock.patch.object(cmd, '_print_configuration_success'),
        ):
            cmd._run_main(mock.Mock(), mock.Mock())

        cmd._sso_session_prompter.prompt_for_sso_region.assert_called_once()
        mock_resolve.assert_not_called()
