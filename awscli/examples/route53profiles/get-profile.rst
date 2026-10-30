**To get information about a Profile**

The following ``get-profile`` example returns information about the specified Profile. ::

    aws route53profiles get-profile \
        --profile-id rp-4987774726example

Output::

    {
        "Profile": {
            "Arn": "arn:aws:route53profiles:us-west-2:123456789012:profile/rp-4987774726example",
            "ClientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "CreationTime": 1710851044.288,
            "Id": "rp-4987774726example",
            "ModificationTime": 1710851044.288,
            "Name": "test",
            "OwnerId": "123456789012",
            "ShareStatus": "NOT_SHARED",
            "Status": "COMPLETE",
            "StatusMessage": "Created Profile"
        }
    }

For more information, see `Viewing and updating Amazon Route 53 Profiles <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/profiles-editing.html>`__ in the *Amazon Route 53 Developer Guide*.
