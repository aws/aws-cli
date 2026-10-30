**To list tags**

The following ``list-tags-for-resource`` example retrieves a list of all tags attached to the specified connections resource. ::

    aws codestar-connections list-tags-for-resource \
        --resource-arn arn:aws:codestar-connections:us-west-2:123456789012:connection/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Tags": [
            {
                "Key": "Project",
                "Value": "ProjectA"
            },
            {
                "Key": "ReadOnly",
                "Value": "true"
            }
        ]
    }

For more information, see `View tags for a connections resource <https://docs.aws.amazon.com/dtconsole/latest/userguide/connections-tag.html#connections-tag-view>`__ in the *Developer Tools console User Guide*.