**Example 1: To check installed skills for updates**

The following ``check-skill-updates`` example lists the installed AWS skills that have a newer version available. ::

    aws agent-toolkit check-skill-updates

Output::

    {
        "skills": [
            {
                "agent": "Kiro",
                "name": "aws-serverless",
                "path": "/Users/username/.kiro/skills/aws-serverless/SKILL.md",
                "installedVersion": "v1",
                "latestVersion": "v2",
                "updateAvailable": true
            }
        ]
    }

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 2: When every installed skill is up to date**

The following ``check-skill-updates`` example shows the output when no updates are available. ::

    aws agent-toolkit check-skill-updates

Output::

    {
        "skills": []
    }

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 3: To list every installed skill**

The following ``check-skill-updates`` example uses ``--all`` to include skills that are already up to date. ::

    aws agent-toolkit check-skill-updates \
        --all

Output::

    {
        "skills": [
            {
                "agent": "Kiro",
                "name": "aws-cloudformation",
                "path": "/Users/username/.kiro/skills/aws-cloudformation/SKILL.md",
                "installedVersion": "v2",
                "latestVersion": "v2",
                "updateAvailable": false
            },
            {
                "agent": "Kiro",
                "name": "aws-serverless",
                "path": "/Users/username/.kiro/skills/aws-serverless/SKILL.md",
                "installedVersion": "v1",
                "latestVersion": "v2",
                "updateAvailable": true
            }
        ]
    }

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 4: To check skills for a specific agent**

The following ``check-skill-updates`` example checks only the skills installed for Kiro. ::

    aws agent-toolkit check-skill-updates \
        --agent kiro

Output::

    {
        "skills": [
            {
                "agent": "Kiro",
                "name": "aws-serverless",
                "path": "/Users/username/.kiro/skills/aws-serverless/SKILL.md",
                "installedVersion": "v1",
                "latestVersion": "v2",
                "updateAvailable": true
            }
        ]
    }

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.
