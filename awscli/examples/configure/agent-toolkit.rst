**Example 1: To set up AI coding agents with AWS skills and the AWS MCP Server**

The following ``agent-toolkit`` example runs the interactive setup wizard globally. It detects installed AI coding agents, installs default AWS skills into their configuration directories in the home directory, and configures the AWS MCP Server connection. When run in a directory other than the home directory without ``--project`` or ``--global``, the wizard first asks whether to set up the current directory only. ::

    aws configure agent-toolkit

Output::

    Detecting installed AI coding agents...
      [x] Kiro
      [ ] Claude Code (not found)
      [ ] Cursor (not found)

    Select agents to configure
    > [x] Kiro

    Fetching default AWS skills...
      Found: aws-serverless, aws-cdk, aws-iam

    Install 3 default AWS skills? [Y/n]: Y

    Installing 3 default AWS skills...
      [1/3] aws-serverless
      [2/3] aws-cdk
      [3/3] aws-iam

    Skills installed to:
      Kiro: /Users/username/.kiro/skills

    Configure AWS MCP server connection? [Y/n]: Y

    AWS MCP server configured for:
      [x] Kiro: updated /Users/username/.kiro/settings/mcp.json

    You can discover additional skills with 'aws agent-toolkit search-skills --search-query <query>'

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.

**Example 2: To set up the AWS skills and the AWS MCP Server for the current project**

The following ``agent-toolkit`` example uses ``--project`` to install the default AWS skills into the skills directories of the current directory and to configure the AWS MCP Server in each agent's project MCP config. ``--yes`` accepts the defaults without prompting. Automatic update hooks are only added to the global configuration of each agent. ::

    aws configure agent-toolkit \
        --project \
        --yes

Output::

    Setting up the agent toolkit for ~/my-project.

    Detecting installed AI coding agents...
      [x] Kiro - ~/my-project/.kiro/skills
      [ ] Claude Code (not found)
      [ ] Cursor (not found)

    Fetching default AWS skills...
      Found: aws-serverless, aws-cdk, aws-iam

    Installing 3 default AWS skills...
      [1/3] aws-serverless
      [2/3] aws-cdk
      [3/3] aws-iam

    Skills installed to:
      Kiro - ~/my-project/.kiro/skills

    AWS MCP server configured for:
      [x] Kiro - ~/my-project/.kiro/settings/mcp.json: updated

    You can discover additional skills with 'aws agent-toolkit search-skills --search-query <text>'
    Add them to this project with 'aws agent-toolkit add-skill --skill-name <name> --project'

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/quick-start.html>`__ in the *AWS Agent Toolkit User Guide*.
