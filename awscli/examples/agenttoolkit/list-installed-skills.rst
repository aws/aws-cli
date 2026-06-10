**Example 1: To list installed skills**

The following ``list-installed-skills`` example lists all AWS skills installed on detected agents. ::

    aws agent-toolkit list-installed-skills

Output::

    {
        "skills": [
            {
                "agent": "Kiro",
                "name": "aws-serverless",
                "path": "/Users/username/.kiro/skills/aws-serverless/SKILL.md"
            },
            {
                "agent": "Cursor",
                "name": "aws-serverless",
                "path": "/Users/username/.cursor/skills/aws-serverless/SKILL.md"
            }
        ]
    }

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 2: To list installed skills for a specific agent**

The following ``list-installed-skills`` example lists skills installed only in Kiro. ::

    aws agent-toolkit list-installed-skills \
        --agent kiro

Output::

    {
        "skills": [
            {
                "agent": "Kiro",
                "name": "aws-serverless",
                "path": "/Users/username/.kiro/skills/aws-serverless/SKILL.md"
            }
        ]
    }

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.
