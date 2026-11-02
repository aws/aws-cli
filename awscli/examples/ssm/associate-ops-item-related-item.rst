**To associate a related item**

The following ``associate-ops-item-related-item`` example associates a related item to the OpsItem. ::

    aws ssm associate-ops-item-related-item \
        --ops-item-id "oi-649fExample" \
        --association-type "RelatesTo" \
        --resource-type "AWS::SSMIncidents::IncidentRecord" \
        --resource-uri "arn:aws:ssm-incidents::123456789012:incident-record/Example-Response-Plan/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Creating an incident for an OpsItem <https://docs.aws.amazon.com/systems-manager/latest/userguide/OpsCenter-working-with-OpsItems-create-an-incident.html>`__ in the *AWS Systems Manager User Guide*.
