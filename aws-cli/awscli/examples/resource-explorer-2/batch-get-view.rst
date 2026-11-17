**To retrieve details about multiple Resource Explorer views**

The following ``batch-get-view`` example displays the details about two views specified by their ARNs. Use spaces to separate the multiple ARNs in the --view-arn parameter. ::

    aws resource-explorer-2 batch-get-view \
        --view-arns arn:aws:resource-explorer-2:us-west-2:123456789012:view/My-EC2-Only-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 arn:aws:resource-explorer-2:us-west-2:123456789012:view/My-Main-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Views": [
            {
                "Filters": {
                    "FilterString": "service:ec2"
                },
                "IncludedProperties": [
                    {
                        "Name": "tags"
                    }
                ],
                "LastUpdatedAt": "2022-07-13T21:33:45.249000+00:00",
                "Owner": "123456789012",
                "Scope": "arn:aws:iam::123456789012:root",
                "ViewArn": "arn:aws:resource-explorer-2:us-west-2:123456789012:view/My-EC2-Only-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            },
            {
                "Filters": {
                    "FilterString": ""
                },
                "IncludedProperties": [
                    {
                        "Name": "tags"
                    }
                ],
                "LastUpdatedAt": "2022-07-13T20:34:11.314000+00:00",
                "Owner": "123456789012",
                "Scope": "arn:aws:iam::123456789012:root",
                "ViewArn": "arn:aws:resource-explorer-2:us-west-2:123456789012:view/My-Main-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            }
        ],
        "Errors": []
    }

For more information about views, see `Working with views <https://docs.aws.amazon.com/resource-explorer/latest/userguide/views.html>`__ in the *AWS Resource Explorer Users Guide*.