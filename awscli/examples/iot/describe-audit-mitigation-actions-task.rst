**To show the details of an audit mitigation actions task**

The following ``describe-audit-mitigation-actions-task`` example shows the details for the specified task, where the ``ResetPolicyVersionAction`` was applied to a finding. The results include when the task started and ended, how many findings were targeted (and the outcome), and the definition of the action that is applied as part of this task. ::

    aws iot describe-audit-mitigation-actions-task \
        --task-id ResetPolicyTask01

Output::

    {
        "taskStatus": "COMPLETED",
        "startTime": "2019-12-10T15:13:19.457000-08:00",
        "endTime": "2019-12-10T15:13:19.947000-08:00",
        "taskStatistics": {
            "IOT_POLICY_OVERLY_PERMISSIVE_CHECK": {
                "totalFindingsCount": 1,
                "failedFindingsCount": 0,
                "succeededFindingsCount": 1,
                "skippedFindingsCount": 0,
                "canceledFindingsCount": 0
            }
        },
        "target": {
            "findingIds": [
                "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            ]
        },
        "auditCheckToActionsMapping": {
            "IOT_POLICY_OVERLY_PERMISSIVE_CHECK": [
                "ResetPolicyVersionAction"
            ]
        },
        "actionsDefinition": [
            {
                "name": "ResetPolicyVersionAction",
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "roleArn": "arn:aws:iam::123456789012:role/service-role/ReplacePolicyVersionRole",
                "actionParams": {
                    "replaceDefaultPolicyVersionParams": {
                        "templateName": "BLANK_POLICY"
                    }
                }
            }
        ]
    }

For more information, see `DescribeAuditMitigationActionsTask (Mitigation Action Commands) <https://docs.aws.amazon.com/iot/latest/developerguide/mitigation-action-commands.html>`__ in the *AWS IoT Developer Guide*.
