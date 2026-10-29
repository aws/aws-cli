**Example 1: To enable a lifecycle policy**

The following ``update-lifecycle-policy`` example enables the specified lifecycle policy. ::

    aws dlm update-lifecycle-policy \
        --policy-id policy-0123456789abcdef0 \
        --state ENABLED

This command produces no output.

For more information, see `Modify Amazon Data Lifecycle Manager policies <https://docs.aws.amazon.com/ebs/latest/userguide/modify.html>`__ in the *Amazon EBS User Guide*.

**Example 2: To disable a lifecycle policy**

The following ``update-lifecycle-policy`` example disables the specified lifecycle policy. ::

    aws dlm update-lifecycle-policy \
        --policy-id policy-0123456789abcdef0 \
        --state DISABLED

This command produces no output.

For more information, see `Modify Amazon Data Lifecycle Manager policies <https://docs.aws.amazon.com/ebs/latest/userguide/modify.html>`__ in the *Amazon EBS User Guide*.

**Example 3: To update the details for lifecycle policy**

The following ``update-lifecycle-policy`` example updates the target tags for the specified lifecycle policy. ::

    aws dlm update-lifecycle-policy \
        --policy-id policy-0123456789abcdef0 \
        --policy-details file://policyDetails.json

This command produces no output.

Other details not referenced in the file are not changed by the command.

Contents of ``policyDetails.json``::

    {
        "TargetTags": [
            {
                "Key": "costCenter",
                "Value": "120"
            },
            {
                "Key": "project",
                "Value": "lima"
            }
        ]
    }

For more information, see `Modify Amazon Data Lifecycle Manager policies <https://docs.aws.amazon.com/ebs/latest/userguide/modify.html>`__ in the *Amazon EBS User Guide*.
