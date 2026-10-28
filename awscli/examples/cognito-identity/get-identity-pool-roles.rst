**To get identity pool roles**

The following ``get-identity-pool-roles`` example gets the roles for the specified identity pool. ::

    aws cognito-identity get-identity-pool-roles --identity-pool-id "us-west-2:11111111-1111-1111-1111-111111111111"

Output::

    {
        "IdentityPoolId": "us-west-2:11111111-1111-1111-1111-111111111111",
        "Roles": {
            "authenticated": "arn:aws:iam::111111111111:role/Cognito_MyIdentityPoolAuth_Role",
            "unauthenticated": "arn:aws:iam::111111111111:role/Cognito_MyIdentityPoolUnauth_Role"
        }
    }