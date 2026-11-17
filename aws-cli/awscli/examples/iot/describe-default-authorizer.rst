**To get information about the default custom authorizer**

The following ``describe-default-authorizer`` example displays details for the default custom authorizer. ::

    aws iot describe-default-authorizer

Output::

    {
        "authorizerDescription": {
            "authorizerName": "CustomAuthorizer",
            "authorizerArn": "arn:aws:iot:us-west-2:123456789012:authorizer/CustomAuthorizer"
        }
    }

For more information, see `Creating and managing custom authorizers (CLI) <https://docs.aws.amazon.com/iot/latest/developerguide/config-custom-auth.html>`__ in the *AWS IoT Developer Guide*.
