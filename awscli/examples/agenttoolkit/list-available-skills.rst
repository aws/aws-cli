**Example 1: To list all available skills**

The following ``list-available-skills`` example lists all skills available in the remote catalog. ::

    aws agent-toolkit list-available-skills

Output::

    {
        "skills": [
            {
                "name": "aws-serverless",
                "description": "Build, deploy, and manage serverless applications on AWS.",
                "version": "v1",
                "categories": [
                    "aws-core"
                ]
            },
            {
                "name": "aws-cdk",
                "description": "Author, deploy, and troubleshoot AWS infrastructure using CDK.",
                "version": "v1",
                "categories": [
                    "aws-core"
                ]
            },
            {
                "name": "aws-cleanrooms",
                "description": "Troubleshoot AWS Clean Rooms collaboration issues.",
                "version": "v1",
                "categories": []
            }
        ]
    }

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 2: To list available skills filtered by category**

The following ``list-available-skills`` example lists only skills in the aws-core category. ::

    aws agent-toolkit list-available-skills \
        --category-filter aws-core

Output::

    {
        "skills": [
            {
                "name": "aws-serverless",
                "description": "Build, deploy, and manage serverless applications on AWS.",
                "version": "v1",
                "categories": [
                    "aws-core"
                ]
            },
            {
                "name": "aws-cdk",
                "description": "Author, deploy, and troubleshoot AWS infrastructure using CDK.",
                "version": "v1",
                "categories": [
                    "aws-core"
                ]
            }
        ]
    }

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.
