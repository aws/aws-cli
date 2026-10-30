**To create a Profile**

The following ``create-profile`` example creates a Profile. ::

    aws route53profiles create-profile \
        --name test

Output::

    {
        "Profile": {
            "Arn": "arn:aws:route53profiles:us-west-2:123456789012:profile/rp-6ffe47d5example",
            "ClientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "CreationTime": 1710850903.578,
            "Id": "rp-6ffe47d5example",
            "ModificationTime": 1710850903.578,
            "Name": "test",
            "OwnerId": "123456789012",
            "ShareStatus": "NOT_SHARED",
            "Status": "COMPLETE",
            "StatusMessage": "Created Profile"
        }
    }

For more information, see `Creating Route 53 Profiles <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/profile-create.html>`__ in the *Amazon Route 53 Developer Guide*.
