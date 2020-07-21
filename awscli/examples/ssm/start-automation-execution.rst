**To execute an automation document**

The following ``start-automation-execution`` example runs an Automation document. ::

    aws ssm start-automation-execution \
        --document-name "AWS-UpdateLinuxAmi" \
        --parameters "AutomationAssumeRole=arn:aws:iam::123456789012:role/SSMAutomationRole,SourceAmiId=ami-EXAMPLE,IamInstanceProfileName=EC2InstanceRole"

Output::

    {
      "AutomationExecutionId": "4105a4fc-f944-11e6-9d32-0a1b2EXAMPLE"
    }

For more information, see `Running an Automation Workflow Manually <https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-working-executing-manually.html>`__ in the *AWS Systems Manager User Guide*.
