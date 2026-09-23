**To view a task**

The following ``get-run-task`` example gets details about a workflow task. ::

    aws omics get-run-task \
        --id "6096280" \
        --task-id "6657068"

Output::

    {
        "taskId": "6657068",
        "status": "COMPLETED",
        "name": "FileCopy",
        "cpus": 1,
        "memory": 1,
        "creationTime": "2025-06-30T23:14:54.329480+00:00",
        "startTime": "2025-06-30T23:17:43.437000+00:00",
        "stopTime": "2025-06-30T23:17:57.662000+00:00",
        "logStream": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/omics/WorkflowLog:log-stream:run/6096280/task/6657068",
        "gpus": 0,
        "instanceType": "omics.c.large"
    }

For more information, see `Task lifecycle in a HealthOmics run <https://docs.aws.amazon.com/omics/latest/dev/workflow-run-tasks.html>`__ in the *AWS HealthOmics User Guide*.
