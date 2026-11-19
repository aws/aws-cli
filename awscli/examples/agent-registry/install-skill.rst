**Example 1: To install a skill for every detected AI coding agent**

The following ``install-skill`` example downloads the specified skill record's package, verifies its SHA-256 digest, and installs the skill for every AI coding agent detected on this computer. ::

    aws agent-registry install-skill \
        --registry-id a1b2c3d4e5f6g7h8 \
        --record-id r1s2t3u4v5w6

Output::

    Downloading pdf-extract from https://artifact-123456789012-us-west-2.s3.us-west-2.amazonaws.com...
    Verified SHA-256 9805b8de5b0b745ea24ce17dccaea04aee7ac0347980c6d624466f7f977e24d6
    Claude Code: Installed pdf-extract to /home/user/.claude/skills/pdf-extract
    Kiro: Installed pdf-extract to /home/user/.kiro/skills/pdf-extract

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.

**Example 2: To install a skill for a specific AI coding agent**

The following ``install-skill`` example installs the specified skill only for Claude Code. ::

    aws agent-registry install-skill \
        --registry-id a1b2c3d4e5f6g7h8 \
        --record-id r1s2t3u4v5w6 \
        --agent claude-code

Output::

    Downloading pdf-extract from https://artifact-123456789012-us-west-2.s3.us-west-2.amazonaws.com...
    Verified SHA-256 9805b8de5b0b745ea24ce17dccaea04aee7ac0347980c6d624466f7f977e24d6
    Claude Code: Installed pdf-extract to /home/user/.claude/skills/pdf-extract

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.

**Example 3: To install a skill into a specific directory**

The following ``install-skill`` example installs the specified skill into a subdirectory of the specified directory, instead of the skills folders of the detected AI coding agents. ::

    aws agent-registry install-skill \
        --registry-id a1b2c3d4e5f6g7h8 \
        --record-id r1s2t3u4v5w6 \
        --target-directory /home/user/my-project/skills

Output::

    Downloading pdf-extract from https://artifact-123456789012-us-west-2.s3.us-west-2.amazonaws.com...
    Verified SHA-256 9805b8de5b0b745ea24ce17dccaea04aee7ac0347980c6d624466f7f977e24d6
    Installed pdf-extract to /home/user/my-project/skills/pdf-extract

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.

**Example 4: To install a skill from a registry that uses a custom JWT authorizer**

The following ``install-skill`` example signs in to a registry that uses a ``CUSTOM_JWT`` authorizer and installs the specified skill. If there is no cached sign-in for the registry, the command opens the identity provider's sign-in page in your browser first. ::

    aws agent-registry install-skill \
        --registry-id a1b2c3d4e5f6g7h8 \
        --record-id r1s2t3u4v5w6 \
        --authorizer JWT \
        --client-id 0oa1b2c3d4e5f6g7h8i9

Output::

    Registry a1b2c3d4e5f6g7h8 trusts: https://example.us.auth0.com/
    Detected identity provider: generic OIDC provider
    Attempting to open your default browser. If the browser does not open, open the following URL.

    https://example.us.auth0.com/authorize?response_type=code&client_id=0oa1b2c3d4e5f6g7h8i9&...

    Waiting for sign-in to complete (up to 10 minutes)...
    Signed in.

    Downloading pdf-extract from https://artifact-123456789012-us-west-2.s3.us-west-2.amazonaws.com...
    Verified SHA-256 9805b8de5b0b745ea24ce17dccaea04aee7ac0347980c6d624466f7f977e24d6
    Claude Code: Installed pdf-extract to /home/user/.claude/skills/pdf-extract
    Kiro: Installed pdf-extract to /home/user/.kiro/skills/pdf-extract

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.

**Example 5: To reinstall a skill that is already up to date**

The following ``install-skill`` example uses ``--force`` to reinstall a skill whose installed copy already matches the package published on the record. Without ``--force``, the command leaves an up-to-date copy as it is. ::

    aws agent-registry install-skill \
        --registry-id a1b2c3d4e5f6g7h8 \
        --record-id r1s2t3u4v5w6 \
        --force

Output::

    Downloading pdf-extract from https://artifact-123456789012-us-west-2.s3.us-west-2.amazonaws.com...
    Verified SHA-256 9805b8de5b0b745ea24ce17dccaea04aee7ac0347980c6d624466f7f977e24d6
    Claude Code: Reinstalled pdf-extract at /home/user/.claude/skills/pdf-extract.
    Kiro: Reinstalled pdf-extract at /home/user/.kiro/skills/pdf-extract.

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.

**Example 6: To install a skill whose record has only SKILL.md text**

The following ``install-skill`` example installs a skill whose record has no downloadable package but holds the text of its ``SKILL.md``. The command writes that text as the skill's ``SKILL.md`` and downloads nothing, so the installed skill has no other files. ::

    aws agent-registry install-skill \
        --registry-id a1b2c3d4e5f6g7h8 \
        --record-id r1s2t3u4v5w6

Output::

    Installing the SKILL.md text published on record r1s2t3u4v5w6; the record has no package, so only SKILL.md is installed.
    Claude Code: Installed pdf-extract to /home/user/.claude/skills/pdf-extract
    Kiro: Installed pdf-extract to /home/user/.kiro/skills/pdf-extract

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.

**Example 7: To install a skill whose record is named differently from the skill**

The following ``install-skill`` example installs a skill from a record named ``pdf_processing_skill`` whose ``SKILL.md`` names the skill ``pdf-processing-skill``. The command names the skill's folder after the ``name`` in its ``SKILL.md``, and says so when the record's name differs. ::

    aws agent-registry install-skill \
        --registry-id a1b2c3d4e5f6g7h8 \
        --record-id r1s2t3u4v5w6

Output::

    Downloading pdf_processing_skill from https://artifact-123456789012-us-west-2.s3.us-west-2.amazonaws.com...
    Verified SHA-256 9805b8de5b0b745ea24ce17dccaea04aee7ac0347980c6d624466f7f977e24d6
    Record 'pdf_processing_skill' installs as skill 'pdf-processing-skill'.
    Claude Code: Installed pdf-processing-skill to /home/user/.claude/skills/pdf-processing-skill
    Kiro: Installed pdf-processing-skill to /home/user/.kiro/skills/pdf-processing-skill

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.

**Example 8: To keep an installed package when the record offers only SKILL.md text**

The following ``install-skill`` example runs against a record that now returns only its ``SKILL.md`` text, for a skill that was installed earlier from the record's package. The command keeps the installed package rather than replacing it with the text alone. Pass ``--force`` to replace it. ::

    aws agent-registry install-skill \
        --registry-id a1b2c3d4e5f6g7h8 \
        --record-id r1s2t3u4v5w6

Output::

    Claude Code: pdf-extract at /home/user/.claude/skills/pdf-extract holds the record's package; the record now publishes no downloadable package, so it was left as it is. Pass --force to replace it with the SKILL.md text only.
    Kiro: pdf-extract at /home/user/.kiro/skills/pdf-extract holds the record's package; the record now publishes no downloadable package, so it was left as it is. Pass --force to replace it with the SKILL.md text only.

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.

**Example 9: To install a skill by its record name**

The following ``install-skill`` example installs the skill whose record is named ``pdf-extract``, as ``list-skills`` shows it in ``name``, instead of giving the record ID. The command looks the name up among every page of the registry's skill records, which also needs the ``agent-registry:ListDiscoverableRegistryRecords`` permission, says which record ID it resolved to, and then installs that record. ``--record-name`` is the record's own name, matched exactly; the name in the skill's ``SKILL.md``, which ``list-skills`` shows in ``skillName``, is not matched. If more than one skill record has the name, the command installs nothing and lists their record IDs, so that you can choose one with ``--record-id``. ::

    aws agent-registry install-skill \
        --registry-id a1b2c3d4e5f6g7h8 \
        --record-name pdf-extract

Output::

    Record 'pdf-extract' is r1s2t3u4v5w6.
    Downloading pdf-extract from https://artifact-123456789012-us-west-2.s3.us-west-2.amazonaws.com...
    Verified SHA-256 9805b8de5b0b745ea24ce17dccaea04aee7ac0347980c6d624466f7f977e24d6
    Claude Code: Installed pdf-extract to /home/user/.claude/skills/pdf-extract
    Kiro: Installed pdf-extract to /home/user/.kiro/skills/pdf-extract

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.
