**Example 1: To get metadata for a skill**

The following ``get-skill-metadata`` example retrieves metadata for the aws-serverless skill, including its version and file list. ::

    aws agent-toolkit get-skill-metadata \
        --skill-name aws-serverless

Output::

    {
        "name": "aws-serverless",
        "version": "v1",
        "description": "Build, deploy, and manage serverless applications on AWS using Lambda, API Gateway, Step Functions, and SAM/CDK.",
        "categories": [
            "aws-core"
        ],
        "files": [
            "SKILL.md",
            "references/architecture.md",
            "references/best-practices.md"
        ]
    }

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 2: To get metadata for a specific skill version**

The following ``get-skill-metadata`` example retrieves metadata for version v1 of the aws-serverless skill. ::

    aws agent-toolkit get-skill-metadata \
        --skill-name aws-serverless \
        --skill-version v1

Output::

    {
        "name": "aws-serverless",
        "version": "v1",
        "description": "Build, deploy, and manage serverless applications on AWS using Lambda, API Gateway, Step Functions, and SAM/CDK.",
        "categories": [
            "aws-core"
        ],
        "files": [
            "SKILL.md",
            "references/architecture.md"
        ]
    }

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.
