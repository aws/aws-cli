**To describe a user pool client**

The following ``describe-user-pool-domain`` example describes a user pool domain named my-domain. ::

    aws cognito-idp describe-user-pool-domain \
        --domain my-domain

Output::

    {
        "DomainDescription": {
            "UserPoolId": "us-west-2_aaaaaaaaa",
            "AWSAccountId": "123456789012",
            "Domain": "my-domain",
            "S3Bucket": "aws-cognito-prod-pdx-assets",
            "CloudFrontDistribution": "aaaaaaaaaaaaa.cloudfront.net",
            "Version": "20190128175402",
            "Status": "ACTIVE",
            "CustomDomainConfig": {}
        }
    }

For more information, see `Configuring a user pool domain <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-assign-domain.html>`__ in the *Amazon Cognito Developer Guide*.
