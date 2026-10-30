**To report status feedback for an instance**

The following ``report-instance-status`` example reports status feedback for the specified instance. ::

    aws ec2 report-instance-status \
        --instances i-1234567890abcdef0 \
        --status impaired \
        --reason-codes unresponsive

This command produces no output.

For more information, see `Status checks for Amazon EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-system-instance-status-check.html>`__ in the *Amazon EC2 User Guide*.
