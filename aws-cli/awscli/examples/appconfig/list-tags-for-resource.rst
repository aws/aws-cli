**To list the tags of an application**

The following ``list-tags-for-resource`` example lists the tags of a specified application. ::

    aws appconfig list-tags-for-resource \
        --resource-arn arn:aws:appconfig:us-west-2:123456789012:application/339ohji

Output::

    {
        "Tags": {
            "group1": "1"
        }
    }

For more information, see `Creating a namespace for your application in AWS AppConfig <https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-namespace.html>`__ in the *AWS AppConfig User Guide*.