**To delete a related item association**

The following ``disassociate-ops-item-related-item`` example deletes the association between the OpsItem and a related item. ::

    aws ssm disassociate-ops-item-related-item \
        --ops-item-id "oi-f99f2EXAMPLE" \
        --association-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

This command produces no output.

For more information, see `Creating an incident for an OpsItem <https://docs.aws.amazon.com/systems-manager/latest/userguide/OpsCenter-working-with-OpsItems-create-an-incident.html>`__ in the *AWS Systems Manager User Guide*.