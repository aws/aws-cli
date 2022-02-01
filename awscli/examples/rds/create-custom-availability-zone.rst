**To create a custom Availability Zone**

The following ``create-custom-availability-zone`` example creates a custom Availability Zone. ::

    aws rds create-custom-availability-zone \
        --custom-availability-zone-name test-custom-availability-zone \
        --new-vpn-tunnel-name test-vpn-tunnel \
        --vpn-tunnel-originator-ip 192.0.2.0

Output::

    {
        "CustomAvailabilityZone": {
            "CustomAvailabilityZoneId": "rds-caz-EXAMPLE",
            "CustomAvailabilityZoneName": "test-custom-availability-zone",
            "CustomAvailabilityZoneStatus": "CREATING"
        }
    }

For more information, see `Creating additional custom AZs in an AWS Region <https://docs.aws.amazon.com/AmazonRDS/latest/RDSonVMwareUserGuide/creating-a-custom-az.html>`__ in the *Amazon RDS on VMware User Guide*.