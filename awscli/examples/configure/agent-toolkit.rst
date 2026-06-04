**To set up AI coding agents with AWS skills and the AWS MCP Server**

The following ``agent-toolkit`` example runs the interactive setup wizard. It detects installed AI coding agents, installs default AWS skills, and configures the AWS MCP Server connection. ::

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

For more information, see `Getting started with the AWS Agent Toolkit <https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started.html>`__ in the *AWS Agent Toolkit User Guide*.
