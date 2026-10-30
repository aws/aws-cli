**To update an identity pool**

The following ``update-identity-pool`` example updates an identity pool. It sets the name to MyIdentityPool. It adds Cognito as an identity provider.
It disallows unauthenticated identities. ::

    aws cognito-identity update-identity-pool \
        --identity-pool-id "us-west-2:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --identity-pool-name "MyIdentityPool" \
        --no-allow-unauthenticated-identities \
        --cognito-identity-providers ProviderName="cognito-idp.us-west-2.amazonaws.com/us-west-2_111111111",ClientId="3n4b5urk1ft4fl3mg5e62d9ado",ServerSideTokenCheck=false

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
