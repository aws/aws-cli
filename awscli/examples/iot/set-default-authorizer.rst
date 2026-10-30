**To set a default authorizer**

The following ``set-default-authorizer`` example sets the custom authorizer named ``CustomAuthorizer`` as the default authorizer. ::

    aws iot set-default-authorizer \
        --authorizer-name CustomAuthorizer

Output::

    {
        "authorizerName": "CustomAuthorizer",
        "authorizerArn": "arn:aws:iot:us-west-2:123456789012:authorizer/CustomAuthorizer"
    }

For more information, see `Creating and managing custom authorizers (CLI) <https://docs.aws.amazon.com/iot/latest/developerguide/config-custom-auth.html>`__ in the *AWS IoT Core Developer Guide*.
