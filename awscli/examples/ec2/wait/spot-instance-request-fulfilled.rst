**To wait until an Spot Instance request is fulfilled**

The following ``wait spot-instance-request-fulfilled`` example pauses and resumes running only after it confirms that a Spot Instance request is fulfilled in the specified Availability Zone. ::

    aws ec2 wait spot-instance-request-fulfilled \
        --filters Name=launched-availability-zone,Values=us-west-2a

This command produces no output.

For more information, see `Get the status of a Spot Instance request <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-request-status.html>`__ in the *Amazon EC2 User Guide*.
