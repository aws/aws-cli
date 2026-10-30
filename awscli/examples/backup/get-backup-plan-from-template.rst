**To get an existing backup plan from a template**

The following ``get-backup-plan-from-template`` example gets an existing backup plan from a template that specifies a daily backup with a 35 day retention. ::

    aws backup get-backup-plan-from-template \
        --backup-plan-template-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "BackupPlanDocument": {
            "Rules": [
                {
                    "RuleName": "DailyBackups",
                    "ScheduleExpression": "cron(0 5 ? * * *)",
                    "StartWindowMinutes": 480,
                    "Lifecycle": {
                        "DeleteAfterDays": 35
                    }
                }
            ]
        }
    }

For more information, see `Creating a Backup Plan <https://docs.aws.amazon.com/aws-backup/latest/devguide/creating-a-backup-plan.html>`__ in the *AWS Backup Developer Guide*.
