**Example 1: To add tags to a maintenance window**

The following ``add-tags-to-resource`` example adds a tag to a maintenance window.

Command::

    aws ssm add-tags-to-resource \
        --resource-type "MaintenanceWindow" \
        --resource-id "mw-03eb9db42890fb82d" \
        --tags "Key=Stack,Value=Production"

This command produces no output.

**Example 2: To add tags to a parameter**

The following ``add-tags-to-resource`` example adds two tags to a parameter.

Command::

    aws ssm add-tags-to-resource \
        --resource-type "Parameter" \
        --resource-id "My-Parameter" \
        --tags '[{"Key":"Region","Value":"East"},{"Key":"Environment", "Value":"Production"}]'

This command produces no output.

For more information, see `Tagging Systems Manager Parameters <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-su-tag.html>`__ in the *AWS Systems Manager User Guide*.
