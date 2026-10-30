**Example 1: To fetch a file from a skill**

The following ``get-skill-file`` example retrieves the SKILL.md file from the aws-serverless skill. ::

    aws agent-toolkit get-skill-file \
        --skill-name aws-serverless \
        --file-path SKILL.md

Output::

    # AWS Serverless

    Build, deploy, and manage serverless applications on AWS using Lambda,
    API Gateway, Step Functions, EventBridge, and SAM/CDK.

    ## When to use this skill
    ...

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 2: To fetch a specific version of a skill file**

The following ``get-skill-file`` example retrieves a reference file from a specific version of the aws-serverless skill. ::

    aws agent-toolkit get-skill-file \
        --skill-name aws-serverless \
        --file-path references/architecture.md \
        --skill-version v1

Output::

    # Architecture Reference

    ## Lambda Function Patterns
    ...

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.
