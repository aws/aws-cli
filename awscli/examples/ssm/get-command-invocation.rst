**To display the details of a command invocation**

The following ``get-command-invocation`` example lists all the invocations of the specified command on the specified instance. ::

    aws ssm get-command-invocation \
        --command-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --instance-id "i-1234567890abcdef0"

Output::

    {
        "CommandId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "InstanceId": "i-1234567890abcdef0",
        "Comment": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222:a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
        "DocumentName": "AWS-UpdateSSMAgent",
        "DocumentVersion": "",
        "PluginName": "aws:updateSsmAgent",
        "ResponseCode": 0,
        "ExecutionStartDateTime": "2020-02-19T18:18:03.419Z",
        "ExecutionElapsedTime": "PT0.091S",
        "ExecutionEndDateTime": "2020-02-19T18:18:03.419Z",
        "Status": "Success",
        "StatusDetails": "Success",
        "StandardOutputContent": "Updating amazon-ssm-agent from 2.3.842.0 to latest\nSuccessfully downloaded https://s3.us-west-2.amazonaws.com/amazon-ssm-us-east-2/ssm-agent-manifest.json\namazon-ssm-agent 2.3.842.0 has already been installed, update skipped\n",
        "StandardOutputUrl": "",
        "StandardErrorContent": "",
        "StandardErrorUrl": "",
        "CloudWatchOutputConfig": {
            "CloudWatchLogGroupName": "",
            "CloudWatchOutputEnabled": false
        }
    }

For more information, see `Understanding Command Statuses <https://docs.aws.amazon.com/systems-manager/latest/userguide/monitor-commands.html>`__ in the *AWS Systems Manager User Guide*.
