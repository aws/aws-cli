**To remove a tag from a patch baseline**

The following ``remove-tags-from-resource`` example removes tags from a patch baseline. ::

    aws ssm remove-tags-from-resource \
        --resource-type "PatchBaseline" \
        --resource-id "pb-0123456789abcdef0" \
        --tag-keys "Region"

This command produces no output.

For more information, see `Working with Patch Manager resources using the AWS CLI <https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-cli-commands.html>`__ in the *AWS Systems Manager User Guide*.
