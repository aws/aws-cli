**To list principals with access to a resource**

The following ``list-principals`` example displays a list of the principals that can access resources of the specified type through any resource shares. ::

    aws ram list-principals \
        --resource-owner SELF \
        --resource-type ec2:Subnet

Output::

    {
        "principals": [
            {
                "id": "arn:aws:organizations::123456789012:ou/o-gx7EXAMPLE/ou-29c5-zEXAMPLE",
                "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "creationTime": 1565298209.737,
                "lastUpdatedTime": 1565298211.019,
                "external": false
            }
        ]
    }

For more information, see `Viewing the principals you share resources with in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/working-with-sharing-view-principals.html>`__ in the *AWS RAM User Guide*.
