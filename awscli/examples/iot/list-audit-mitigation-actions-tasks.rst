**To list audit mitigation action tasks**

The following ``list-audit-mitigation-actions-tasks`` example lists the mitigation actions that were applied to findings within the specified time period. ::

    aws iot create-mitigation-action --cli-input-json file://params.json

Contents of ``params.json``::

    {
        "actionName": "AddThingsToQuarantineGroup1Action",
        "actionParams": {
            "addThingsToThingGroupParams": {
                "thingGroupNames": [
                    "QuarantineGroup1"
                ],
                "overrideDynamicGroups": true
            }
        },
        "roleArn": "arn:aws:iam::123456789012:role/service-role/MoveThingsToQuarantineGroupRole"
    }

Output::

    {
        "tasks": [
            {
                "taskId": "ResetPolicyTask01",
                "startTime": "2019-12-10T15:13:19.457000-08:00",
                "taskStatus": "COMPLETED"
            }
        ]
    }

For more information, see `ListAuditMitigationActionsTasks (Mitigation Action Commands) <https://docs.aws.amazon.com/iot/latest/developerguide/mitigation-action-commands.html#dd-api-iot-ListAuditMitigationActionsTasks>`__ in the *AWS IoT Developer Guide*.
