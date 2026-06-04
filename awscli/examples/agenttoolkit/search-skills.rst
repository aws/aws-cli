**To search for available skills**

The following ``search-skills`` example searches for skills related to serverless development. ::

    aws agent-toolkit search-skills \
        --search-query serverless

Output::

    {
        "skills": [
            {
                "name": "aws-serverless",
                "description": "Build, deploy, and manage serverless applications on AWS using Lambda, API Gateway, Step Functions, and SAM/CDK.",
                "version": "v1",
                "categories": [
                    "aws-core"
                ]
            }
        ]
    }

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.
