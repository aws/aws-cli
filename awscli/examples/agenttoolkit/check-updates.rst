**Example 1: To check installed skills for updates**

The following ``check-updates`` example reports the installed and latest available version of each AWS skill installed on detected agents. ::

    aws agent-toolkit check-updates

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
            },
            {
                "agent": "Kiro",
                "name": "aws-cloudformation",
                "path": "/Users/username/.kiro/skills/aws-cloudformation/SKILL.md",
                "installedVersion": "v2",
                "latestVersion": "v2",
                "updateAvailable": false
            }
        ]
    }

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 2: To check skills for a specific agent**

The following ``check-updates`` example checks only the skills installed for Kiro. ::

    aws agent-toolkit check-updates \
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

**Example 3: To list only the skills that have an update available**

The following ``check-updates`` example uses ``--query`` to return just the skills that are out of date. ::

    aws agent-toolkit check-updates \
        --query 'skills[?updateAvailable].[name,installedVersion,latestVersion]' \
        --output table

Output::

    --------------------------------
    |         check-updates        |
    +-----------------+-----+------+
    |  aws-serverless |  v1 |  v2  |
    +-----------------+-----+------+

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.
