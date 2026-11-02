**To list audit mitigation action tasks**

The following ``list-audit-mitigation-actions-tasks`` example lists the mitigation actions that were applied to findings within the specified time period. ::

    aws iot list-audit-mitigation-actions-tasks \
        --start-time 1594157400 \
        --end-time 1594157430

Output::

    {
        "tasks": [
            {
                    "taskId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                    "startTime": "2020-07-07T14:30:15.172000-07:00",
                "taskStatus": "COMPLETED"
            }
        ]
    }

For more information, see `ListAuditMitigationActionsTasks (Mitigation Action Commands) <https://docs.aws.amazon.com/iot/latest/developerguide/mitigation-action-commands.html>`__ in the *AWS IoT Developer Guide*.