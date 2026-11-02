**To update a custom authorizer**

The following ``update-authorizer`` example he state of ``CustomAuthorizer2`` to ``INACTIVE``. ::

    aws iot update-authorizer \
        --authorizer-name CustomAuthorizer2 \
        --status INACTIVE

Output::

    {
        "authorizerName": "CustomAuthorizer2",
        "authorizerArn": "arn:aws:iot:us-west-2:123456789012:authorizer/CustomAuthorizer2"
    }

For more information, see `Creating and managing custom authorizers (CLI) <https://docs.aws.amazon.com/iot/latest/developerguide/config-custom-auth.html>`__ in the *AWS IoT Core Developer Guide*.
