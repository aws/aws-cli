**To describe the tags for a WorkSpace**

The following ``describe-tags`` example lists the tag key names and their values for the specified WorkSpace. ::

    aws workspaces describe-tags \
        --resource-id ws-12345678

Output::

    {
        "TagList": [
            {
                "Key": "username",
                "Value": "jane1234"
            }
        ]
    }
