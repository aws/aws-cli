**To disassociate a Profile**

The following ``disassociate-profile`` example disassociates a Profile from a VPC. ::

    aws route53profiles disassociate-profile \
        --profile-id rp-4987774726example \
        --resource-id vpc-0af3b96b3example

Output::

    {
        "ProfileAssociation": {
            "CreationTime": 1710851336.527,
            "Id": "rpassoc-489ce212fexample",
            "ModificationTime": 1710851401.362,
            "Name": "test-association",
            "OwnerId": "123456789012",
            "ProfileId": "rp-4987774726example",
            "ResourceId": "vpc-0af3b96b3example",
            "Status": "DELETING",
            "StatusMessage": "Deleting Profile Association"
        }
    }

For more information, see `Viewing VPCs associated to an Amazon Route 53 Profile <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/profiles-vpcs-editing.html>`__ in the *Amazon Route 53 Developer Guide*.
