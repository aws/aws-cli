**To list environments for an AppConfig application**

This ``list-environments`` example lists the environments that exist for an application. ::

    aws appconfig list-environments \
        --application-id abc1234

Output::

    {
        "Items": [
            {
                "Description": "My AppConfig environment",
                "Id": "2d4e6f8",
                "State": "ReadyForDeployment",
                "ApplicationId": "abc1234",
                "Monitors": [],
                "Name": "TestEnvironment"
            }
        ]
    }

For more information, see `Create an Environment  <https://docs.aws.amazon.com/systems-manager/latest/userguide/appconfig-creating-environment.html>`__ in the *AWS Systems Manager User Guide*.
