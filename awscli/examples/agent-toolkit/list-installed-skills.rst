**Example 1: To list installed skills**

The following ``list-installed-skills`` example lists all AWS skills installed on detected agents. Without ``--project`` or ``--global``, both global skills and the skills of the current directory are listed, and ``scope`` tells them apart. ::

    aws agent-toolkit list-installed-skills

Output::

    {
        "skills": [
            {
                "agent": "Kiro",
                "scope": "global",
                "name": "aws-serverless",
                "path": "/Users/username/.kiro/skills/aws-serverless/SKILL.md"
            },
            {
                "agent": "Cursor",
                "scope": "global",
                "name": "aws-serverless",
                "path": "/Users/username/.cursor/skills/aws-serverless/SKILL.md"
            }
        ]
    }

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 2: To list installed skills for a specific agent**

The following ``list-installed-skills`` example lists skills installed only in Kiro. ::

    aws agent-toolkit list-installed-skills \
        --agent kiro

Output::

    {
        "skills": [
            {
                "agent": "Kiro",
                "scope": "global",
                "name": "aws-serverless",
                "path": "/Users/username/.kiro/skills/aws-serverless/SKILL.md"
            }
        ]
    }

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 3: To list the skills of the current project**

The following ``list-installed-skills`` example uses ``--project`` to list only the skills of the current directory. Use ``--global`` to list only global skills. ::

    aws agent-toolkit list-installed-skills \
        --project

Output::

    {
        "skills": [
            {
                "agent": "Kiro",
                "scope": "project",
                "name": "aws-serverless",
                "path": "/Users/username/my-project/.kiro/skills/aws-serverless/SKILL.md"
            }
        ]
    }

For more information, see `Getting started <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.
