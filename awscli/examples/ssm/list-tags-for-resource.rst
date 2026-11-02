**To list the tags applied to a patch baseline**

The following ``list-tags-for-resource`` example lists the tags for a patch baseline. ::

    aws ssm list-tags-for-resource \
        --resource-type "PatchBaseline" \
        --resource-id "pb-0123456789abcdef0"

Output::

    {
        "TagList": [
            {
                "Key": "Environment",
                "Value": "Production"
            },
            {
                "Key": "Region",
                "Value": "EMEA"
            }
        ]
    }

For more information, see `Working with Patch Manager resources using the AWS CLI <https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-cli-commands.html>`__ in the *AWS Systems Manager User Guide*.
