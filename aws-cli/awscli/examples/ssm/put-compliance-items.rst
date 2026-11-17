**To register a compliance type and compliance details to a designated instance**

The following ``put-compliance-items`` example registers the compliance type ``Custom:AVCheck`` to the specified managed instance. ::

    aws ssm put-compliance-items \
        --resource-id "i-1234567890abcdef0" \
        --resource-type "ManagedInstance" \
        --compliance-type "Custom:AVCheck" \
        --execution-summary "ExecutionTime=2019-02-18T16:00:00Z" \
        --items "Id=Version2.0,Title=ScanHost,Severity=CRITICAL,Status=COMPLIANT"

This command produces no output.

For more information, see `Assign custom compliance metadata using the AWS CLI <https://docs.aws.amazon.com/systems-manager/latest/userguide/compliance-custom-metadata-cli.html>`__ in the *AWS Systems Manager User Guide*.
