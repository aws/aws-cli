"""Elastic Beanstalk commands' requests (upstream
tests/functional/elasticbeanstalk)."""

from typing import Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

# Upstream's new_keypair_config.json, tab indents included.
OPTION_SETTINGS_JSON: Final = (
    "[\n"
    "    {\n"
    '\t"Namespace": "aws:autoscaling:launchconfiguration",\n'
    '\t"OptionName": "EC2KeyName",\n'
    '\t"Value": "webapps"\n'
    "    },\n"
    "    {\n"
    '\t"Namespace": "aws:elasticbeanstalk:container:tomcat:jvmoptions",\n'
    '\t"OptionName": "Xms",\n'
    '\t"Value": "1256m"\n'
    "    }\n"
    "]\n"
)


async def test_create_application(api: ApiSession) -> None:
    await api.assert_params_for_cmd(
        "elasticbeanstalk create-application --application-name FooBar",
        {"ApplicationName": "FooBar"},
    )


async def test_update_configuration_template_from_file(
    api: ApiSession,
) -> None:
    settings = api.cwd / "new_keypair_config.json"
    settings.write_text(OPTION_SETTINGS_JSON, encoding="utf-8")
    await api.assert_params_for_cmd(
        [
            "elasticbeanstalk",
            "update-configuration-template",
            "--application-name",
            "FooBar",
            "--template-name",
            "x86_64_m1_medium_config",
            "--option-settings",
            f"file://{settings}",
            "--description",
            "This_is_a_test",
        ],
        {
            "ApplicationName": "FooBar",
            "TemplateName": "x86_64_m1_medium_config",
            "Description": "This_is_a_test",
            "OptionSettings": [
                {
                    "Namespace": "aws:autoscaling:launchconfiguration",
                    "OptionName": "EC2KeyName",
                    "Value": "webapps",
                },
                {
                    "Namespace": (
                        "aws:elasticbeanstalk:container:tomcat:jvmoptions"
                    ),
                    "OptionName": "Xms",
                    "Value": "1256m",
                },
            ],
        },
    )
