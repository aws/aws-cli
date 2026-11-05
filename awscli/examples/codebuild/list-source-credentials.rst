**To view a list of sourceCredentialsObjects**

The following ``list-source-credentials`` example lists tokens for an AWS account connected to one Bitbucket account and one GitHub account. Each ``sourceCredentialsInfos`` object in the response contains connected source credentials information. ::

    aws codebuild list-source-credentials
    
Output::

    {
        "sourceCredentialsInfos": [
            {
                "serverType": "BITBUCKET",
                "arn": "arn:aws:codebuild:us-west-2:123456789012:token/bitbucket",
                "authType": "BASIC_AUTH"
            },
            {
                "serverType": "GITHUB",
                "arn": "arn:aws:codebuild:us-west-2:123456789012:token/github",
                "authType": "OAUTH"
            }
        ]
    }

For more information, see `Access your source provider in CodeBuild <https://docs.aws.amazon.com/codebuild/latest/userguide/access-tokens.html>`__ in the *AWS CodeBuild User Guide*.
