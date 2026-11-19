**Example 1: To uninstall a skill from every detected AI coding agent**

The following ``uninstall-skill`` example uninstalls the pdf-extract skill from every detected AI coding agent that it was installed for. The ``--yes`` option skips the confirmation prompt. ::

    aws agent-registry uninstall-skill \
        --name pdf-extract \
        --yes

Output::

    Claude Code: Uninstalled pdf-extract from /home/user/.claude/skills (installed from registry a1b2c3d4e5f6g7h8, record r1s2t3u4v5w6)
    Kiro: Uninstalled pdf-extract from /home/user/.kiro/skills (installed from registry a1b2c3d4e5f6g7h8, record r1s2t3u4v5w6)

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.

**Example 2: To uninstall a skill from a specific AI coding agent**

The following ``uninstall-skill`` example uninstalls the pdf-extract skill only from Kiro, after asking for confirmation. ::

    aws agent-registry uninstall-skill \
        --name pdf-extract \
        --agent kiro

Output::

    Remove /home/user/.kiro/skills/pdf-extract (from registry a1b2c3d4e5f6g7h8, record r1s2t3u4v5w6)? [y/N]: y
    Kiro: Uninstalled pdf-extract from /home/user/.kiro/skills (installed from registry a1b2c3d4e5f6g7h8, record r1s2t3u4v5w6)

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.

**Example 3: To uninstall a skill from a specific directory**

The following ``uninstall-skill`` example uninstalls the pdf-extract skill from a directory that it was installed into with ``install-skill --target-directory``. ::

    aws agent-registry uninstall-skill \
        --name pdf-extract \
        --target-directory /home/user/my-project/skills \
        --yes

Output::

    Uninstalled pdf-extract from /home/user/my-project/skills (installed from registry a1b2c3d4e5f6g7h8, record r1s2t3u4v5w6)

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.
