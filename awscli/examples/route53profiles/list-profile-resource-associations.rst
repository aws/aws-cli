**To list Profile resource associations**

The following ``list-profile-resource-associations`` example lists the Profile resource associations for the specified Profile. ::

    aws route53profiles list-profile-resource-associations \
        --profile-id rp-4987774726example

Output::

    {
        "ProfileResourceAssociations": [
            {
                "CreationTime": 1710851216.613,
                "Id": "rpr-001913120a7example",
                "ModificationTime": 1710851216.613,
                "Name": "test-resource-association",
                "OwnerId": "123456789012",
                "ProfileId": "rp-4987774726example",
                "ResourceArn": "arn:aws:route53resolver:us-west-2:123456789012:firewall-rule-group/rslvr-frg-cfe7f72example",
                "ResourceProperties": "{\"priority\":102}",
                "ResourceType": "FIREWALL_RULE_GROUP",
                "Status": "COMPLETE",
                "StatusMessage": "Completed creation of Profile to DNS Firewall rule group association"
            }
        ]
    }

For more information, see `Viewing and updating Route 53 resources associated to an Amazon Route 53 Profile <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/profiles-resources-editing.html>`__ in the *Amazon Route 53 Developer Guide*.
