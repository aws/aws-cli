**To list identity pools**

The following ``list-identity-pools`` example lists identity pools. A maximum of 20 identity pools are listed. ::

    aws cognito-identity list-identity-pools \
        --max-results 20

Output::

    {
        "IdentityPools": [
            {
                "IdentityPoolId": "us-west-2:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "IdentityPoolName": "MyIdentityPool"
            },
            {
                "IdentityPoolId": "us-west-2:a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "IdentityPoolName": "AnotherIdentityPool"
            },
            {
                "IdentityPoolId": "us-west-2:a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "IdentityPoolName": "IdentityPoolRegionA"
            }
        ]
    }

For more information, see `Amazon Cognito identity pools <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-identity.html>`__ in the *Amazon Cognito Developer Guide*.
