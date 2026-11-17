**To create a role alias**

The following ``create-role-alias`` example creates a role alias called ``LightBulbRole`` for the specified role. ::

    aws iot create-role-alias \
        --role-alias LightBulbRole \
        --role-arn arn:aws:iam::123456789012:role/lightbulbrole-001

Output::

    {
        "roleAlias": "LightBulbRole",
        "roleAliasArn": "arn:aws:iot:us-west-2:123456789012:rolealias/LightBulbRole"
    }

For more information, see `Authorizing direct calls to AWS services using AWS IoT Core credential provider <https://docs.aws.amazon.com/iot/latest/developerguide/authorizing-direct-aws.html>`__ in the *AWS IoT Developer Guide*.
