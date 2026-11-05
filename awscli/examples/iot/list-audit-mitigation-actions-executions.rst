**To list the details of an audit mitigation action execution**

The following ``list-audit-mitigation-actions-executions`` example lists the details for the mitigation action task with the specified ``taskId`` and for the specified finding. An audit mitigation action task applies a mitigation action to one or more findings from an AWS IoT Device Defender audit. ::

    aws iot list-audit-mitigation-actions-executions \
        --task-id myActionsTaskId \
        --finding-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "actionsExecutions": [
            {
                "taskId": "myActionsTaskId",
                "findingId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "actionName": "ResetPolicyVersionAction",
                "actionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "status": "COMPLETED",
                "startTime": "2019-12-10T15:19:13.279000-08:00",
                "endTime": "2019-12-10T15:19:13.337000-08:00"
            }
        ]
    }

For more information, see `ListAuditMitigationActionsExecutions (Mitigation Action Commands) <https://docs.aws.amazon.com/iot/latest/developerguide/mitigation-action-commands.html>`__ in the *AWS IoT Developer Guide*.
