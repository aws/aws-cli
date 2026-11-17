**To list your custom authorizer**

The following ``list-authorizers`` example lists the custom authorizers in your AWS account. ::

    aws iot list-authorizers
    
Output::

    {
        "authorizers": [
            {
                "authorizerName": "CustomAuthorizer",
                "authorizerArn": "arn:aws:iot:us-west-2:123456789012:authorizer/CustomAuthorizer"
            },
            {
                "authorizerName": "CustomAuthorizer2",
                "authorizerArn": "arn:aws:iot:us-west-2:123456789012:authorizer/CustomAuthorizer2"
            },
            {
                "authorizerName": "CustomAuthorizer3",
                "authorizerArn": "arn:aws:iot:us-west-2:123456789012:authorizer/CustomAuthorizer3"
            }
        ]
    }

For more information, see `Custom authentication and authorization <https://docs.aws.amazon.com/iot/latest/developerguide/custom-authentication.html>`__ in the *AWS IoT Core Developer Guide*.
