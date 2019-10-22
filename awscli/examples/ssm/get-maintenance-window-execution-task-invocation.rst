**To get information about a Maintenance Window task invocation**

This example lists information about a task invocation that was part of a Maintenance Window execution.

Command::

  aws ssm get-maintenance-window-execution-task-invocation --window-execution-id "bc494bfa-e63b-49f6-8ad1-aa9f2EXAMPLE" --task-id "96f2ad59-97e3-461d-a63d-40c8aEXAMPLE" --invocation-id "a5273e2c-d2c6-4880-b3e1-5e550EXAMPLE"

Output::

  {
    "Status": "SUCCESS",
    "Parameters": "{\"comment\":\"\",\"documentName\":\"AWS-RunPowerShellScript\",\"instanceIds\":[\"i-1234567890EXAMPLE\"],\"maxConcurrency\":\"1\",\"maxErrors\":\"1\",\"parameters\":{\"executionTimeout\":[\"3600\"],\"workingDirectory\":[\"\"],\"commands\":[\"echo Hello\"]},\"timeoutSeconds\":600}",
    "ExecutionId": "03b6baa0-5460-4e15-83f2-ea685EXAMPLE",
    "InvocationId": "a5273e2c-d2c6-4880-b3e1-5e550EXAMPLE",
    "StartTime": 1549998326.421,
    "TaskType": "RUN_COMMAND",
    "EndTime": 1550001931.784,
    "WindowExecutionId": "bc494bfa-e63b-49f6-8ad1-aa9f2EXAMPLE",
    "StatusDetails": "Failed",
    "TaskExecutionId": "96f2ad59-97e3-461d-a63d-40c8aEXAMPLE"
  }
