**To unassign a secondary private IP address from a network interface**

The following ``unassign-private-ip-addresses`` example unassigns the specified private IP address from the specified network interface. ::

    aws ec2 unassign-private-ip-addresses \
        --network-interface-id eni-e5aa89a3 \
        --private-ip-addresses 10.0.0.82

This command produces no output.

For more information, see `Secondary IP addresses for your EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-secondary-ip-addresses.html>`__ in the *Amazon EC2 User Guide*.
