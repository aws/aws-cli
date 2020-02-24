**To list the configuration profiles for an AppConfig application**

This ``list-configuration-profiles`` example lists the configuration profiles for an application. ::

    aws appconfig list-configuration-profiles \
        --application-id abc1234

Output::

    {
        "Items": [
            {
                "ValidatorTypes": [
                    "JSON_SCHEMA"
                ],
                "ApplicationId": "abc1234",
                "Id": "9x8y7z6",
                "LocationUri": "ssm-parameter:///blogapp/featureX_switch",
                "Name": "TestConfigurationProfile"
            },
            {
                "ValidatorTypes": [
                    "JSON_SCHEMA"
                ],
                "ApplicationId": "abc1234",
                "Id": "hijklmn",
                "LocationUri": "ssm-parameter:///testapp/featureX_switch",
                "Name": "TestAppConfigurationProfile"
            }
        ]
    }  

For more information, see `Create a Configuration and a Configuration Profile <https://docs.aws.amazon.com/systems-manager/latest/userguide/appconfig-creating-configuration-and-profile.html>`__ in the *AWS Systems Manager User Guide*.
