**To get the details of a lifecycle policy**

The following ``get-lifecycle-policy`` example retrieves the full definition of the specified lifecycle policy. For a policy that has never been updated or run, the response doesn't include the ``dateUpdated`` and ``dateLastRun`` fields. ::

    aws imagebuilder get-lifecycle-policy \
        --lifecycle-policy-arn arn:aws:imagebuilder:us-west-2:123456789012:lifecycle-policy/my-example-lifecycle-policy

Output::

    {
        "lifecyclePolicy": {
            "arn": "arn:aws:imagebuilder:us-west-2:123456789012:lifecycle-policy/my-example-lifecycle-policy",
            "name": "my-example-lifecycle-policy",
            "description": "Deletes AMIs and snapshots for builds older than six months, keeping at least the five most recent",
            "status": "ENABLED",
            "executionRole": "arn:aws:iam::123456789012:role/my-example-lifecycle-role",
            "resourceType": "AMI_IMAGE",
            "policyDetails": [
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
                        "value": 6,
                        "unit": "MONTHS",
                        "retainAtLeast": 5
                    }
                }
            ],
            "resourceSelection": {
                "tagMap": {
                    "Environment": "my-example-environment"
                }
            },
            "dateCreated": "2026-09-09T19:34:38.409000+00:00",
            "tags": {}
        }
    }

For more information, see `View lifecycle policy details <https://docs.aws.amazon.com/imagebuilder/latest/userguide/view-lifecycle-policy.html>`__ in the *EC2 Image Builder User Guide*.
