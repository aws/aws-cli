**To send a diagnostic interrupt**

The following ``send-diagnostic-interrupt`` example sends a diagnostic interrupt to the specified instance. ::

    aws ec2 send-diagnostic-interrupt \
        --instance-id i-1234567890abcdef0

This command produces no output.

For more information, see `Send a diagnostic interrupt to debug an unreachable Amazon EC2 instance <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/diagnostic-interrupt.html>`__ in the *Amazon EC2 User Guide*.
