**Example 1: To install a skill**

The following ``add-skill`` example downloads and installs the aws-serverless skill to all detected AI coding agents. Without ``--project``, skills are installed globally, in the home directory. ::

    aws agent-toolkit add-skill \
        --skill-name aws-serverless

Output::

    Installed aws-serverless (v1) to Kiro.

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 2: To install a skill to a specific agent**

The following ``add-skill`` example installs the aws-cdk skill only to Kiro. ::

    aws agent-toolkit add-skill \
        --skill-name aws-cdk \
        --agent kiro

Output::

    Installed aws-cdk (v1) to Kiro.

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 3: To install a specific version of a skill**

The following ``add-skill`` example installs version v1 of the aws-serverless skill. ::

    aws agent-toolkit add-skill \
        --skill-name aws-serverless \
        --skill-version v1

Output::

    Installed aws-serverless (v1) to Kiro.

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 4: To install a skill into the current project**

The following ``add-skill`` example installs the aws-serverless skill into the skills directories of the current directory, such as ``.kiro/skills``, instead of the home directory. These project-level skills only apply to that project and can be shared through source control. ::

    aws agent-toolkit add-skill \
        --skill-name aws-serverless \
        --project

Output::

    Installed aws-serverless (v1) to Kiro - ~/my-project/.kiro/skills.

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.
