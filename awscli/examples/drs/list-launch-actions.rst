**To list launch actions for a source server**

The following ``list-launch-actions`` example lists the post-launch actions configured for the specified source server. ::

    aws drs list-launch-actions \
        --resource-id s-1234567890abcdef0

Output::

    {
        "items": [
            {
                "actionCode": "AWSMigration-VerifyMountedVolumes",
                "actionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "actionVersion": "$DEFAULT",
                "active": true,
                "category": "VALIDATION",
                "description": "This document verifies that EBS volumes on the launched instance are accessible and properly mounted.",
                "name": "Volume integrity validation",
                "optional": true,
                "order": 401,
                "type": "SSM_COMMAND"
            }
        ]
    }

For more information, see `Post-launch actions <https://docs.aws.amazon.com/drs/latest/userguide/post-launch-actions.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
