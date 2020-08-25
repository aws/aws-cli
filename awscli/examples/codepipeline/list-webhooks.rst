**To view a list of webhooks**

The following ``list-webhooks`` example lists the available webhooks in your AWS account. ::

    aws codepipeline list-webhooks \
        --endpoint-url "https://codepipeline.eu-central-1.amazonaws.com" \
        --region "eu-central-1"

Output::

    {
        "webhooks": [
            {
                "url": "https://webhooks.domain.com/trigger111111111EXAMPLE11111111111111111": {
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
                "arn": "arn:aws:codepipeline:eu-central-1:ACCOUNT_ID:webhook:my-webhook"
            }
        ]
    }

For more information, see `List webhooks in your account <https://docs.aws.amazon.com/codepipeline/latest/userguide/pipelines-webhooks-view.html>`__ in the *AWS CodePipeline User Guide*.