**To create an identity pool with Cognito identity pool provider**

The following ``create-identity-pool`` example creates an identity pool named MyIdentityPool. It has a Cognito identity pool provider.
Unauthenticated identities are not allowed. ::

    aws cognito-identity create-identity-pool \
        --identity-pool-name MyIdentityPool \
        --no-allow-unauthenticated-identities \
        --cognito-identity-providers ProviderName="cognito-idp.us-west-2.amazonaws.com/us-west-2_aaaaaaaaa",ClientId="3n4b5urk1ft4fl3mg5e62d9ado",ServerSideTokenCheck=false

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

For more information, see `Getting started with Amazon Cognito identity pools <https://docs.aws.amazon.com/cognito/latest/developerguide/getting-started-with-identity-pools.html>`__ in the *Amazon Cognito Developer Guide*.
