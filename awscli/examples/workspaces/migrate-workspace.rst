**To migrate a WorkSpace**

The following ``migrate-workspace`` example migrates the specified WorkSpace to the ``Standard with Windows 10 (English)`` public bundle type. ::

    aws workspaces migrate-workspace \
        --source-workspace-id ws-12345678 \
        --bundle-id wsb-8vbljg4r6

Output::

    {
        "SourceWorkspaceId": "ws-12345678",
        "TargetWorkspaceId": "ws-87654321"
    }

