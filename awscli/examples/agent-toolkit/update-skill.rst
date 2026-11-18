**Example 1: To update an installed skill**

The following ``update-skill`` example updates the aws-serverless skill to the latest version across all agents where it is installed. Without ``--project`` or ``--global``, both global skills and the skills of the current directory are updated. ::

    aws agent-toolkit update-skill \
        --skill-name aws-serverless

Output::

    Updated aws-serverless (v1) to Kiro.

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 2: To update a skill for a specific agent**

The following ``update-skill`` example updates the aws-serverless skill only for Kiro. ::

    aws agent-toolkit update-skill \
        --skill-name aws-serverless \
        --agent kiro

Output::

    Updated aws-serverless (v2) to Kiro.

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 3: To update a skill that is already up to date**

The following ``update-skill`` example shows the output when the installed skill is already at the latest version. ::

    aws agent-toolkit update-skill \
        --skill-name aws-serverless

Output::

    aws-serverless is already up to date (v2).

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 4: To update every installed skill**

The following ``update-skill`` example updates all installed skills that are out of date. Skills that are already at the latest version are left alone. ::

    aws agent-toolkit update-skill \
        --all

Output::

    Updated aws-cloudformation (v2) to Kiro.
    Updated aws-serverless (v2) to Kiro.

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 5: To update every installed skill for a specific agent**

The following ``update-skill`` example updates all out-of-date skills, but only for Kiro. ::

    aws agent-toolkit update-skill \
        --all \
        --agent kiro

Output::

    Updated aws-serverless (v2) to Kiro.

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 6: To update every installed skill when all skills are already up to date**

The following ``update-skill`` example shows the output when every installed skill is already at the latest version. ::

    aws agent-toolkit update-skill \
        --all

Output::

    All installed AWS skills are already up to date.

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 7: To update the skills of the current project only**

The following ``update-skill`` example uses ``--project`` to update only the skills of the current directory. Use ``--global`` to update only global skills. ::

    aws agent-toolkit update-skill \
        --all \
        --project

Output::

    Updated aws-serverless (v2) to Kiro - ~/my-project/.kiro/skills.

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.
