**To register a compliance type and compliance details to a designated instance**

The following ``put-compliance-items`` example registers the compliance type ``Custom:AVCheck`` to the specified managed instance. ::

    aws ssm put-compliance-items \
        --resource-id "i-1234567890abcdef0" \
        --resource-type "ManagedInstance" \
        --compliance-type "Custom:AVCheck" \
        --execution-summary "ExecutionTime=2019-02-18T16:00:00Z" \
        --items "Id=Version2.0,Title=ScanHost,Severity=CRITICAL,Status=COMPLIANT"

This command produces no output.

