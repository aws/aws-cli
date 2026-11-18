**Example 1: To remove an installed skill**

The following ``remove-skill`` example removes the global aws-serverless skill from all detected agents. Without ``--project``, only global skills are removed, and a copy of the skill in the current directory is left in place. ::

    aws agent-toolkit remove-skill \
        --skill-name aws-serverless

Output::

    Removed aws-serverless from Kiro.

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 2: To remove a skill from a specific agent**

The following ``remove-skill`` example removes the aws-cdk skill only from Kiro. ::

    aws agent-toolkit remove-skill \
        --skill-name aws-cdk \
        --agent kiro

Output::

    Removed aws-cdk from Kiro.

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 3: To remove a skill from the current project**

The following ``remove-skill`` example uses ``--project`` to remove the aws-serverless skill from the current directory only. The global skill is left in place. ::

    aws agent-toolkit remove-skill \
        --skill-name aws-serverless \
        --project

Output::

    Removed aws-serverless from Kiro - ~/my-project/.kiro/skills.

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.
