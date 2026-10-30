**To list the related-item resources of an OpsItem**

The following ``list-ops-item-related-items`` example lists the related-item resources of an OpsItem. ::

    aws ssm list-ops-item-related-items \
        --ops-item-id "oi-f99f2EXAMPLE"

Output::

    {
        "Summaries": [
            {
                "OpsItemId": "oi-f99f2EXAMPLE",
                "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "ResourceType": "AWS::SSMIncidents::IncidentRecord",
                "AssociationType": "IsParentOf",
                "ResourceUri": "arn:aws:ssm-incidents::123456789012:incident-record/example-response/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "CreatedBy": {
                    "Arn": "arn:aws:sts::123456789012:assumed-role/AWSServiceRoleForIncidentManager/IncidentResponse"
                },
                "CreatedTime": "2021-08-11T18:47:14.994000+00:00",
                "LastModifiedBy": {
                    "Arn": "arn:aws:sts::123456789012:assumed-role/AWSServiceRoleForIncidentManager/IncidentResponse"
                },
                "LastModifiedTime": "2021-08-11T18:47:14.994000+00:00"
            }
        ]
    }

For more information, see `Creating an incident for an OpsItem <https://docs.aws.amazon.com/systems-manager/latest/userguide/OpsCenter-working-with-OpsItems-create-an-incident.html>`__ in the *AWS Systems Manager User Guide*.