**Example 1: To update an installed skill**

The following ``update-skill`` example updates the aws-serverless skill to the latest version across all agents where it is installed. ::

    aws agent-toolkit update-skill \
        --skill-name aws-serverless

Output::

      Updated aws-serverless (v1) to Kiro.

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 2: To update a skill for a specific agent**

The following ``update-skill`` example updates the aws-serverless skill only for Kiro. ::

    aws agent-toolkit update-skill \
        --skill-name aws-serverless \
        --agent kiro

Output::

      Updated aws-serverless (v2) to Kiro.

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 3: When a skill is already up to date**

The following ``update-skill`` example shows the output when the installed skill is already at the latest version. ::

    aws agent-toolkit update-skill \
        --skill-name aws-serverless

Output::

    aws-serverless is already up to date (v2).

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.
