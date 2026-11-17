**To create an application**

The following ``create-application`` example creates an application in AWS AppConfig. ::

    aws appconfig create-application \
        --name "example-application" \
        --description "An application used for creating an example."

Output::

    {
        "Description": "An application used for creating an example.",
        "Id": "339ohji",
        "Name": "example-application"
    }

For more information, see `Creating a namespace for your application in AWS AppConfig <https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-namespace.html>`__ in the *AWS AppConfig User Guide*.