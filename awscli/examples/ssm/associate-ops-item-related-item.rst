**To associate a related item**

The following ``associate-ops-item-related-item`` example associates a related item to the OpsItem. ::

    aws ssm associate-ops-item-related-item \
        --ops-item-id "oi-649fExample" \
        --association-type "RelatesTo" \
        --resource-type "AWS::SSMIncidents::IncidentRecord" \
        --resource-uri "arn:aws:ssm-incidents::111122223333:incident-record/Example-Response-Plan/c2bde883-f7d5-343a-b13a-bf5fe9ea689f"

Output::

    {
        "AssociationId": "61d7178d-a30d-4bc5-9b4e-a9e74EXAMPLE"
    }

For more information, see `Creating an incident for an OpsItem <https://docs.aws.amazon.com/systems-manager/latest/userguide/OpsCenter-working-with-OpsItems-create-an-incident.html>`__ in the *AWS Systems Manager User Guide*.
