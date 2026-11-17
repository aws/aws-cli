**To update an application**

The following ``update-application`` example updates the name of the specified application. ::

    aws appconfig update-application \
        --application-id 339ohji \
        --name "Example-Application"

Output::

    {
        "Id": "339ohji",
        "Name": "Example-Application",
        "Description": "An application used for creating an example."
    }

For more information, see `Creating a namespace for your application in AWS AppConfig <https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-namespace.html>`__ in the *AWS AppConfig User Guide*.