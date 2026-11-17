**To tag an application**

The following ``tag-resource`` example tags an application resource. ::

    aws appconfig tag-resource \
        --resource-arn arn:aws:appconfig:us-west-2:123456789012:application/339ohji \
        --tags '{"group1" : "1"}'

This command produces no output.

For more information, see `Creating a namespace for your application in AWS AppConfig <https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-namespace.html>`__ in the *AWS AppConfig User Guide*.