**Example 1: To create a lifecycle policy**

The following ``create-lifecycle-policy`` example creates a lifecycle policy that deletes AMI-based images six months after they were created. The policy applies to images that match the specified resource tags. ::

    aws imagebuilder create-lifecycle-policy \
        --name my-example-lifecycle-policy \
        --execution-role arn:aws:iam::123456789012:role/my-example-lifecycle-role \
        --resource-type AMI_IMAGE \
        --policy-details '[{"action":{"type":"DELETE"},"filter":{"type":"AGE","value":6,"unit":"MONTHS"}}]' \
        --resource-selection '{"tagMap":{"Environment":"test"}}' \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "lifecyclePolicyArn": "arn:aws:imagebuilder:us-west-2:123456789012:lifecycle-policy/my-example-lifecycle-policy"
    }

**Example 2: To create a lifecycle policy with exclusion rules**

The following ``create-lifecycle-policy`` example creates a lifecycle policy that deletes images created from the specified recipe version after six months. The policy excludes images whose AMIs launched an instance within the last 30 days or are tagged to be retained. ::

    aws imagebuilder create-lifecycle-policy \
        --name my-example-lifecycle-policy \
        --execution-role arn:aws:iam::123456789012:role/my-example-lifecycle-role \
        --resource-type AMI_IMAGE \
        --policy-details file://policy-details.json \
        --resource-selection '{"recipes":[{"name":"my-example-recipe","semanticVersion":"1.0.0"}]}' \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Contents of ``policy-details.json``::

    [
        {
            "action": {
                "type": "DELETE"
            },
            "filter": {
                "type": "AGE",
                "value": 6,
                "unit": "MONTHS"
            },
            "exclusionRules": {
                "amis": {
                    "lastLaunched": {
                        "value": 30,
                        "unit": "DAYS"
                    },
                    "tagMap": {
                        "Retention": "keep"
                    }
                }
            }
        }
    ]

Output::

    {
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "lifecyclePolicyArn": "arn:aws:imagebuilder:us-west-2:123456789012:lifecycle-policy/my-example-lifecycle-policy"
    }

For more information, see `Create lifecycle policies <https://docs.aws.amazon.com/imagebuilder/latest/userguide/create-lifecycle-policies.html>`__ in the *EC2 Image Builder User Guide*.
