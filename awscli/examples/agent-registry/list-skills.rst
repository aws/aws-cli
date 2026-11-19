**Example 1: To list the skills in a registry**

The following ``list-skills`` example lists the skills in the specified registry and the detected AI coding agents that each skill is installed for. ``skillName`` is the name in each skill's ``SKILL.md``, which ``install-skill`` names the skill's folder after; ``name`` is the record's name. ::

    aws agent-registry list-skills \
        --registry-id a1b2c3d4e5f6g7h8

Output::

    {
        "skills": [
            {
                "name": "pdf-extract",
                "skillName": "pdf-extract",
                "recordId": "r1s2t3u4v5w6",
                "description": "Extracts text and tables from PDF files.",
                "recordVersion": "1.2.0",
                "installedFor": [
                    {
                        "id": "claude-code",
                        "name": "Claude Code"
                    },
                    {
                        "id": "kiro",
                        "name": "Kiro"
                    }
                ]
            },
            {
                "name": "csv-tools",
                "skillName": "csv-tools",
                "recordId": "k7l8m9n0p1q2",
                "description": "Cleans, joins and summarizes CSV files.",
                "recordVersion": "0.3.1",
                "installedFor": []
            }
        ]
    }

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.

**Example 2: To list the skills in a registry that uses a custom JWT authorizer**

The following ``list-skills`` example signs in to a registry that uses a ``CUSTOM_JWT`` authorizer and lists its skills. The first time, the command opens the identity provider's sign-in page in your browser. Later commands for the same registry reuse and refresh the cached sign-in instead of opening the browser again. ::

    aws agent-registry list-skills \
        --registry-id a1b2c3d4e5f6g7h8 \
        --authorizer JWT \
        --client-id 0oa1b2c3d4e5f6g7h8i9

Output::

    Registry a1b2c3d4e5f6g7h8 trusts: https://example.us.auth0.com/
    Detected identity provider: generic OIDC provider
    Attempting to open your default browser. If the browser does not open, open the following URL.

    https://example.us.auth0.com/authorize?response_type=code&client_id=0oa1b2c3d4e5f6g7h8i9&...

    Waiting for sign-in to complete (up to 10 minutes)...
    Signed in.

    {
        "skills": [
            {
                "name": "pdf-extract",
                "skillName": "pdf-extract",
                "recordId": "r1s2t3u4v5w6",
                "description": "Extracts text and tables from PDF files.",
                "recordVersion": "1.2.0",
                "installedFor": []
            }
        ]
    }

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.

**Example 3: To list the skills in a registry as a table**

The following ``list-skills`` example lists the name, record ID, and version of each skill in the specified registry as a table. ::

    aws agent-registry list-skills \
        --registry-id a1b2c3d4e5f6g7h8 \
        --query 'skills[].{name:name,recordId:recordId,version:recordVersion}' \
        --output table

Output::

    --------------------------------------------
    |                list-skills               |
    +-------------+----------------+-----------+
    |    name     |   recordId     |  version  |
    +-------------+----------------+-----------+
    |  pdf-extract|  r1s2t3u4v5w6  |  1.2.0    |
    |  csv-tools  |  k7l8m9n0p1q2  |  0.3.1    |
    +-------------+----------------+-----------+

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.
