**To delete a custom Availability Zone**

The following ``delete-custom-availability-zone`` example deletes a custom Availability Zone. ::

    aws rds delete-custom-availability-zone \
        --custom-availability-zone-id rds-caz-EXAMPLE

Output::

    {
        "CustomAvailabilityZone": {
            "CustomAvailabilityZoneId": "rds-caz-EXAMPLE",
            "CustomAvailabilityZoneName": "test-custom-availability-zone",
            "CustomAvailabilityZoneStatus": "DELETING"
        }
    }

For more information, see `What is Amazon RDS on VMware? <https://docs.aws.amazon.com/AmazonRDS/latest/RDSonVMwareUserGuide/rds-on-vmware.html>`__ in the *Amazon RDS on VMware User Guide*.