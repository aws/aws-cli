**Example 1: To remove an installed skill**

The following ``remove-skill`` example removes the aws-serverless skill from all detected agents. ::

    aws agent-toolkit remove-skill \
        --skill-name aws-serverless

Output::

    Removed aws-serverless from Kiro.

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 2: To remove a skill from a specific agent**

The following ``remove-skill`` example removes the aws-cdk skill only from Kiro. ::

    aws agent-toolkit remove-skill \
        --skill-name aws-cdk \
        --agent kiro

Output::

    Removed aws-cdk from Kiro.

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.
