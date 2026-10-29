**To list webhooks**

The following ``list-webhooks`` example retrieves a list of all tags attached to the specified pipeline resource. ::

    aws codepipeline list-webhooks

Output::

    {
        "webhooks": [
            {
                "definition": {
                    "authenticationConfiguration": {
                        "SecretToken": "Secret"
                    },
                    "name": "my-webhook",
                    "authentication": "GITHUB_HMAC",
                    "targetPipeline": "my-Pipeline",
                    "targetAction": "Source",
                    "filters": [
                        {
                            "jsonPath": "$.ref",
                            "matchEquals": "refs/heads/{Branch}"
                        }
                    ]
                },
                "url": "https://webhooks.domain.com/trigger111111111EXAMPLE11111111111111111",
                "arn": "arn:aws:codepipeline:us-west-2:123456789012:webhook:my-webhook"
            }
        ]
    }

For more information, see `List webhooks in your account <https://docs.aws.amazon.com/codepipeline/latest/userguide/appendix-github-oauth.html>`__ in the *AWS CodePipeline User Guide*.