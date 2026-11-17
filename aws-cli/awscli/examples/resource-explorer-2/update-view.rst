**Example 1: To update the IncludedProperties field for a Resource Explorer view**

The following ``update-view`` example updates the specified view by adding ```tags``` to the optional ```IncludedProperties```. After running this operation, search operations that use this view include information about the tags attached to the resources that appear in the results. ::

    aws resource-explorer-2 update-view \
        --included-properties Name=tags \
        --view-arn arn:aws:resource-explorer-2:us-west-2:123456789012:view/My-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "View": {
            "Filters": {
                "FilterString": ""
            },
            "IncludedProperties": [
                {
                    "Name": "tags"
                }
            ],
            "LastUpdatedAt": "2022-07-19T17:41:21.710000+00:00",
            "Owner": "123456789012",
            "Scope": "arn:aws:iam::123456789012:root",
            "ViewArn": "arn:aws:resource-explorer-2:us-west-2:123456789012:view/My-EC2-Only-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
        }
    }

**Example 2: To update the filters attached to a view**

The following ``update-view`` example updates the specified view to use a filter that limits results to only resource types that are associated with the Amazon EC2 service. ::

    aws resource-explorer-2 update-view \
        --filters FilterString="service:ec2" \
        --view-arn arn:aws:resource-explorer-2:us-west-2:123456789012:view/My-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "View": {
        "Filters": {
            "FilterString": "service:ec2"
        },
        "IncludedProperties": [],
        "LastUpdatedAt": "2022-07-19T17:41:21.710000+00:00",
            "Owner": "123456789012",
            "Scope": "arn:aws:iam::123456789012:root",
            "ViewArn": "arn:aws:resource-explorer-2:us-west-2:123456789012:view/My-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
        }
    }

For more information about views, see `Working with views <https://docs.aws.amazon.com/resource-explorer/latest/userguide/views.html>`__ in the *AWS Resource Explorer Users Guide*.