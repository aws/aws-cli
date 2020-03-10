**To list the AppConfig applications in your AWS account**

This ``list-applications`` example lists the applications in your account in the current Region. ::

    aws appconfig list-applications

Output::

    {
        "Items": [
            {
                "Description": "My first AppConfig application",
                "Id": "abc1234",
                "Name": "MyTestApp"
            }
        ]
    }  

For more information, see `Create an AppConfig Application <https://docs.aws.amazon.com/systems-manager/latest/userguide/appconfig-creating-application.html>`__ in the *AWS Systems Manager User Guide*.
