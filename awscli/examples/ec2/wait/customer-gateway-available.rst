**To wait until a customer gateway is available**

The following ``wait customer-gateway-available`` example pauses and resumes running only after it confirms that the specified customer gateway is available. ::

    aws ec2 wait customer-gateway-available \
        --customer-gateway-ids cgw-1234567890abcdef0

This command produces no output.

For more information, see `AWS Site-to-Site VPN customer gateway devices <https://docs.aws.amazon.com/vpn/latest/s2svpn/your-cgw.html>`__ in the *AWS Site-to-Site VPN User Guide*.
