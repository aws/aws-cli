**To report status feedback for an instance**

The following ``report-instance-status`` example reports status feedback for the specified instance. ::

    aws ec2 report-instance-status \
        --instances i-1234567890abcdef0 \
        --status impaired \
        --reason-codes unresponsive
