**To describe your Availability Zones**

The following ``describe-availability-zones`` example describes the Availability Zones that are available to you. The response includes Availability Zones only for the current Region. ::

    aws ec2 describe-availability-zones

The following is example example output for the US East (Ohio) Region. ::

    {
        "AvailabilityZones": [
            {
                "State": "available",
                "Messages": [],
                "RegionName": "us-east-2",
                "ZoneName": "us-east-2a",
                "ZoneId": "use2-az1"
            },
            {
                "State": "available",
                "Messages": [],
                "RegionName": "us-east-2",
                "ZoneName": "us-east-2b",
                "ZoneId": "use2-az2"
            },
            {
                "State": "available",
                "Messages": [],
                "RegionName": "us-east-2",
                "ZoneName": "us-east-2c",
                "ZoneId": "use2-az3"
            }
        ]
    }
