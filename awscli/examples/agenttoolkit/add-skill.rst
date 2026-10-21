**Example 1: To install a skill**

The following ``add-skill`` example downloads and installs the aws-serverless skill to all detected AI coding agents. ::

    aws agent-toolkit add-skill \
        --skill-name aws-serverless

Output::

      Installed aws-serverless (v1) to Kiro.

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 2: To install a skill to a specific agent**

The following ``add-skill`` example installs the aws-cdk skill only to Kiro. ::

    aws agent-toolkit add-skill \
        --skill-name aws-cdk \
        --agent kiro

Output::

      Installed aws-cdk (v1) to Kiro.

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 3: To install a specific version of a skill**

The following ``add-skill`` example installs version v1 of the aws-serverless skill. ::

    aws agent-toolkit add-skill \
        --skill-name aws-serverless \
        --skill-version v1

Output::

      Installed aws-serverless (v1) to Kiro.

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.
