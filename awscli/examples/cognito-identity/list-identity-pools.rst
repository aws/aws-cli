**To list identity pools**

The following ``list-identity-pools`` example lists identity pools. A maximum of 20 identity pools are listed. ::

    aws cognito-identity list-identity-pools \
        --max-results 20

Output::

    {
        "IdentityPools": [
            {
                "IdentityPoolId": "us-west-2:11111111-1111-1111-1111-111111111111",
                "IdentityPoolName": "MyIdentityPool"
            },
            {
                "IdentityPoolId": "us-west-2:11111111-1111-1111-1111-111111111111",
                "IdentityPoolName": "AnotherIdentityPool"
            },
            {
                "IdentityPoolId": "us-west-2:11111111-1111-1111-1111-111111111111",
                "IdentityPoolName": "IdentityPoolRegionA"
            }
        ]
    }
