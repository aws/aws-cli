**To remove a tag from an application**

The following ``untag-resource`` example removes the group1 tag from the specified application. ::

    aws appconfig untag-resource \
        --resource-arn arn:aws:appconfig:us-west-2:123456789012:application/339ohji \
        --tag-keys '["group1"]'

This command produces no output.

For more information, see `Creating a namespace for your application in AWS AppConfig <https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-namespace.html>`__ in the *AWS AppConfig User Guide*.