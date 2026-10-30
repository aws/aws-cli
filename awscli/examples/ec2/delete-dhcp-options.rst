**To delete a DHCP options set**

The following ``delete-dhcp-options`` example deletes the specified DHCP options set. If the command succeeds, no output is returned. ::

    aws ec2 delete-dhcp-options \
        --dhcp-options-id dopt-d9070ebb
