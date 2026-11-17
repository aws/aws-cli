**To describe an identity pool**

The following ``describe-identity-pool`` example describes the specified identity pool. ::

    aws cognito-identity describe-identity-pool \
        --identity-pool-id "us-west-2:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "IdentityPoolId": "us-west-2:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "IdentityPoolName": "MyIdentityPool",
        "AllowUnauthenticatedIdentities": false,
        "CognitoIdentityProviders": [
            {
                "ProviderName": "cognito-idp.us-west-2.amazonaws.com/us-west-2_111111111",
                "ClientId": "3n4b5urk1ft4fl3mg5e62d9ado",
                "ServerSideTokenCheck": false
            }
        ]
    }

For more information, see `Amazon Cognito identity pools <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-identity.html>`__ in the *Amazon Cognito Developer Guide*.
