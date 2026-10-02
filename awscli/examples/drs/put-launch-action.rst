**To add a launch action to a source server**

The following ``put-launch-action`` example adds a post-launch action to the specified source server. ::

    aws drs put-launch-action \
        --resource-id s-1234567890abcdef0 \
        --action-code AWSMigration-VerifyMountedVolumes \
        --action-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --action-version '$DEFAULT' \
        --active \
        --category VALIDATION \
        --description "Verify EBS volumes are accessible" \
        --name "Volume integrity validation" \
        --optional \
        --order 401

Output::

    {
        "actionCode": "AWSMigration-VerifyMountedVolumes",
        "actionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "actionVersion": "$DEFAULT",
        "active": true,
        "category": "VALIDATION",
        "description": "Verify EBS volumes are accessible",
        "name": "Volume integrity validation",
        "optional": true,
        "order": 401,
        "resourceId": "s-1234567890abcdef0",
        "type": "SSM_COMMAND"
    }

For more information, see `Post-launch actions <https://docs.aws.amazon.com/drs/latest/userguide/post-launch-actions.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
