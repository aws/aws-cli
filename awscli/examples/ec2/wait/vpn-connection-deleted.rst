**To wait until a VPN connection is deleted**

The following ``wait vpn-connection-deleted`` example command pauses and continues when it can confirm that the specified VPN connection is deleted. ::

    aws ec2 wait vpn-connection-deleted \
        --vpn-connection-ids vpn-1234567890abcdef0

This command produces no output.

For more information, see `Delete an AWS Site-to-Site VPN connection and gateway <https://docs.aws.amazon.com/vpn/latest/s2svpn/delete-vpn.html>`__ in the *AWS Site-to-Site VPN User Guide*.
