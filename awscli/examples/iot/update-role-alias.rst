**To update a role alias**

The following ``update-role-alias`` example updates the ``LightBulbRole`` role alias. ::

    aws iot update-role-alias \
        --role-alias LightBulbRole \
        --role-arn arn:aws:iam::123456789012:role/lightbulbrole-001

Output::

    {
        "roleAlias": "LightBulbRole",
        "roleAliasArn": "arn:aws:iot:us-west-2:123456789012:rolealias/LightBulbRole"
    }

For more information, see `Authorizing direct calls to AWS services using AWS IoT Core credential provider <https://docs.aws.amazon.com/iot/latest/developerguide/authorizing-direct-aws.html>`__ in the *AWS IoT Core Developer Guide*.
