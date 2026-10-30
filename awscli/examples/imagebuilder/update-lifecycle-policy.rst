**To update a lifecycle policy**

The following ``update-lifecycle-policy`` example updates a lifecycle policy to delete AMI images and their associated snapshots after 12 months, retaining the 3 most recent images. ::

    aws imagebuilder update-lifecycle-policy \
        --lifecycle-policy-arn arn:aws:imagebuilder:us-west-2:123456789012:lifecycle-policy/my-example-policy \
        --description "Deletes AMI images and their snapshots after 12 months, retaining the 3 most recent" \
        --status ENABLED \
        --execution-role arn:aws:iam::123456789012:role/my-example-lifecycle-role \
        --resource-type AMI_IMAGE \
        --policy-details file://policy-details.json \
        --resource-selection '{"tagMap":{"environment":"production"}}' \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Contents of ``policy-details.json``::

    [
        {
            "action": {
                "type": "DELETE",
                "includeResources": {
                    "amis": true,
                    "snapshots": true
                }
            },
            "filter": {
                "type": "AGE",
                "value": 12,
                "unit": "MONTHS",
                "retainAtLeast": 3
            }
        }
    ]

Output::

    {
        "lifecyclePolicyArn": "arn:aws:imagebuilder:us-west-2:123456789012:lifecycle-policy/my-example-policy"
    }

For more information, see `Create lifecycle policies <https://docs.aws.amazon.com/imagebuilder/latest/userguide/create-lifecycle-policies.html>`__ in the *EC2 Image Builder User Guide*.
