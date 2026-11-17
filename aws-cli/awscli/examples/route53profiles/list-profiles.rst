**To list Profiles**

The following ``list-profiles`` example lists the Profiles in your AWS account and displays additional information about them. ::

    aws route53profiles list-profiles

Output::

    {
        "ProfileSummaries": [
            {
                "Arn": "arn:aws:route53profiles:us-west-2:123456789012:profile/rp-4987774726example",
                "Id": "rp-4987774726example",
                "Name": "test",
                "ShareStatus": "NOT_SHARED"
            }
        ]
    }

For more information, see `Viewing and updating Amazon Route 53 Profiles <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/profiles-editing.html>`__ in the *Amazon Route 53 Developer Guide*.
