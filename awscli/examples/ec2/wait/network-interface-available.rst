**To wait until a network interface is available**

The following ``wait network-interface-available`` example pauses and resumes running only after it confirms that the specified network interface is available. ::

    aws ec2 wait network-interface-available \
        --network-interface-ids eni-1234567890abcdef0

This command produces no output.

For more information, see `Elastic network interfaces <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-eni.html>`__ in the *Amazon EC2 User Guide*.
