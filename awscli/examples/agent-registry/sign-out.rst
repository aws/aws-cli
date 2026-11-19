**Example 1: To sign out of a registry**

The following ``sign-out`` example revokes the refresh token of the cached sign-in for the specified registry at its identity provider, and then deletes the sign-in from this computer. ::

    aws agent-registry sign-out \
        --registry-id a1b2c3d4e5f6g7h8

Output::

    Registry a1b2c3d4e5f6g7h8 at https://agent-registry.us-west-2.api.aws: revoked the refresh token; removed the sign-in.

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.

**Example 2: To sign out of every registry**

The following ``sign-out`` example signs out of every registry that has a cached sign-in on this computer. ::

    aws agent-registry sign-out \
        --all

Output::

    Registry a1b2c3d4e5f6g7h8 at https://agent-registry.us-west-2.api.aws: revoked the refresh token; removed the sign-in.
    Registry b9c8d7e6f5g4h3i2 at https://agent-registry.us-west-2.api.aws: revoked the refresh token; removed the sign-in.

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.

**Example 3: To retry a revocation that failed**

The following ``sign-out`` example signs out of a registry when the request to revoke the refresh token fails. The command still deletes the sign-in, keeps the refresh token so that the revocation can be retried, and exits with status 1. ::

    aws agent-registry sign-out \
        --registry-id a1b2c3d4e5f6g7h8

Output::

    Registry a1b2c3d4e5f6g7h8 at https://agent-registry.us-west-2.api.aws: could not revoke the refresh token (HTTP 503 from the identity provider). Removed the sign-in from this machine and kept the refresh token so the revocation can be retried: run aws agent-registry sign-out --registry-id a1b2c3d4e5f6g7h8 again.

Running the same command again retries the revocation. When it succeeds, the command deletes the kept refresh token and exits with status 0. ::

    aws agent-registry sign-out \
        --registry-id a1b2c3d4e5f6g7h8

Output::

    Registry a1b2c3d4e5f6g7h8 at https://agent-registry.us-west-2.api.aws: revoked a refresh token that an earlier sign-out could not revoke.

For more information, see `AWS Agent Registry <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry.html>`__ in the *Amazon Bedrock AgentCore Developer Guide*.
