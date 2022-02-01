**To describe the custom Availability Zones**

The following ``describe-custom-availability-zones`` example retrieves the details of the custom Availability Zones in the AWS Region. ::

    aws rds describe-custom-availability-zones

Output::

    {
        "CustomAvailabilityZones": [
            {
                "CustomAvailabilityZoneId": "rds-caz-EXAMPLE1",
                "CustomAvailabilityZoneName": "custom-az-1",
                "CustomAvailabilityZoneStatus": "CREATING",
                "VpnDetails": {
                    "VpnId": "3604EXAMPLE-7bdEXAMPLE",
                    "VpnTunnelOriginatorIP": "198.51.100.0",
                    "VpnGatewayIp": "192.0.2.0",
                    "VpnPSK": "388cEXAMPLE8",
                    "VpnName": "vpn-EXAMPLE1",
                    "VpnState": "AVAILABLE"
                }
            },
            {
                "CustomAvailabilityZoneId": "rds-caz-EXAMPLE2",
                "CustomAvailabilityZoneName": "custom-az-2",
                "CustomAvailabilityZoneStatus": "CREATING",
                "VpnDetails": {
                    "VpnId": "360EXAMPLE-82EXAMPLE",
                    "VpnTunnelOriginatorIP": "203.0.113.0",
                    "VpnGatewayIp": "198.51.100.0",
                    "VpnPSK": "c95cEXAMPLE",
                    "VpnName": "vpn-EXAMPLE2",
                    "VpnState": "AVAILABLE"
                }
            }
        ]
    }

For more information, see `What is Amazon RDS on VMware? <https://docs.aws.amazon.com/AmazonRDS/latest/RDSonVMwareUserGuide/rds-on-vmware.html>`__ in the *Amazon RDS on VMware User Guide*.