**To list the available applications**

The following ``list-applications`` example lists the available applications in your AWS account. ::

    aws appconfig list-applications

Output::

    {
        "Items": [
            {
                "Id": "339ohji",
                "Name": "test-application",
                "Description": "An application used for creating an example."
            },
            {
                "Id": "rwalwu7",
                "Name": "Test-Application"
            }
        ]
    }

For more information, see `Creating a namespace for your application in AWS AppConfig <https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-namespace.html>`__ in the *AWS AppConfig User Guide*.