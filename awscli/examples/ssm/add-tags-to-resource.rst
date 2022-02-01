**To add tags to a maintenance window**

The following ``add-tags-to-resource`` example adds a tag to the specified maintenance window. ::

    aws ssm add-tags-to-resource \
        --resource-type "MaintenanceWindow" \
        --resource-id "mw-03eb9db428EXAMPLE" \
        --tags "Key=Stack,Value=Production"

This command produces no output.

**To add tags to a parameter**

The following ``add-tags-to-resource`` example adds two tags to to the specified parameter. ::

    aws ssm add-tags-to-resource \
        --resource-type "Parameter" \
        --resource-id "My-Parameter" \
        --tags '[{"Key":"Region","Value":"East"},{"Key":"Environment", "Value":"Production"}]'

This command produces no output.

For more information, see `Tagging Systems Manager Parameters <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-su-tag.html>`__ in the *AWS Systems Manager User Guide*.
