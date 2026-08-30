**To enable lifecycle management for a file system**

The following ``put-lifecycle-configuration`` example enables lifecycle management on an existing file system to transition files to the Infrequent Access (IA) storage class after 30 days of non-access.::

    aws efs put-lifecycle-configuration \
        --file-system-id fs-4gd2a78et \
        --lifecycle-policies TransitionToIA=AFTER_30_DAYS


Output::

    {
        "LifecyclePolicies": [
            {
                "TransitionToIA": "AFTER_30_DAYS"
            }
        ]
    }


This command sets a lifecycle policy for the file system with the ID fs-4gd2a78et, transitioning files to IA storage after 30 days of inactivity.

For more information, see `EFS Lifecycle Management <https://docs.aws.amazon.com/efs/latest/ug/lifecycle-management.html>`__ in the *Amazon Elastic File System User Guide.*.