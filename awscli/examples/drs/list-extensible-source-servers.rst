**To list extensible source servers**

The following ``list-extensible-source-servers`` example lists source servers that can be extended into the specified staging account. ::

    aws drs list-extensible-source-servers \
        --staging-account-id 123456789012

Output::

    {
        "items": [
            {
                "arn": "arn:aws:drs:us-west-2:123456789012:source-server/s-1234567890abcdef0",
                "hostname": "ip-10-0-0-1",
                "sourceServerID": "s-1234567890abcdef0",
                "tags": {}
            }
        ]
    }

For more information, see `AWS Elastic Disaster Recovery cross-Region and cross-account failback <https://docs.aws.amazon.com/drs/latest/userguide/failback-cross.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
