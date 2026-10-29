**To get information about a Profile association**

The following ``get-profile-association`` example returns information about the specified Profile association. ::

    aws route53profiles get-profile-association \
        --profile-association-id rpassoc-489ce212fexample

Output::

    {
        "ProfileAssociation": {
            "CreationTime": 1709338817.148,
            "Id": "rrpassoc-489ce212fexample",
            "ModificationTime": 1709338974.772,
            "Name": "test-association",
            "OwnerId": "123456789012",
            "ProfileId": "rp-4987774726example",
            "ResourceId": "vpc-0af3b96b3example",
            "Status": "COMPLETE",
            "StatusMessage": "Created Profile Association"
        }
    }

For more information, see `Viewing VPCs associated to an Amazon Route 53 Profile <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/profiles-vpcs-editing.html>`__ in the *Amazon Route 53 Developer Guide*.
