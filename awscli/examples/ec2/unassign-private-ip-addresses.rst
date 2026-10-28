**To unassign a secondary private IP address from a network interface**

The following ``unassign-private-ip-addresses`` example unassigns the specified private IP address from the specified network interface. If the command succeeds, no output is returned. ::

    aws ec2 unassign-private-ip-addresses \
        --network-interface-id eni-e5aa89a3 \
        --private-ip-addresses 10.0.0.82
