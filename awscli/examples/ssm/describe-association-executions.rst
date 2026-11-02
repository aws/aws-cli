**Example 1: To get details of all executions for an association**

The following ``describe-association-executions`` example describes all executions of the specified association. ::

    aws ssm describe-association-executions \
        --association-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "AssociationExecutions": [
            {
                "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "AssociationVersion": "1",
                "ExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Status": "Success",
                "DetailedStatus": "Success",
                "CreatedTime": 1550505827.119,
                "ResourceCountByStatus": "{Success=1}"
            },
            {
                "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "AssociationVersion": "1",
                "ExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Status": "Success",
                "DetailedStatus": "Success",
                "CreatedTime": 1550505536.843,
                "ResourceCountByStatus": "{Success=1}"
            }
        ]
    }

For more information, see `Viewing association histories <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-state-assoc-history.html>`__ in the *AWS Systems Manager User Guide*.

**Example 2: To get details of all executions for an association after a specific date and time**

The following ``describe-association-executions`` example describes all executions of an association after the specified date and time. ::

    aws ssm describe-association-executions \
        --association-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --filters "Key=CreatedTime,Value=2019-02-18T16:00:00Z,Type=GREATER_THAN"

Output::

    {
        "AssociationExecutions": [
            {
                "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "AssociationVersion": "1",
                "ExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Status": "Success",
                "DetailedStatus": "Success",
                "CreatedTime": 1550505827.119,
                "ResourceCountByStatus": "{Success=1}"
            },
            {
                "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "AssociationVersion": "1",
                "ExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Status": "Success",
                "DetailedStatus": "Success",
                "CreatedTime": 1550505536.843,
                "ResourceCountByStatus": "{Success=1}"
            }
        ]
    }

For more information, see `Viewing association histories <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-state-assoc-history.html>`__ in the *AWS Systems Manager User Guide*.