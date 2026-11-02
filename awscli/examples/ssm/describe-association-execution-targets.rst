**To get details of an association execution**

The following ``describe-association-execution-targets`` example describes the specified association execution. ::

    aws ssm describe-association-execution-targets \
        --association-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --execution-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"

Output::

    {
        "AssociationExecutionTargets": [
            {
                "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "AssociationVersion": "1",
                "ExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "ResourceId": "i-1234567890abcdef0",
                "ResourceType": "ManagedInstance",
                "Status": "Success",
                "DetailedStatus": "Success",
                "LastExecutionDate": 1550505538.497,
                "OutputSource": {
                    "OutputSourceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                    "OutputSourceType": "RunCommand"
                }
            }
        ]
    }

For more information, see `Viewing association histories <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-state-assoc-history.html>`__ in the *AWS Systems Manager User Guide*.