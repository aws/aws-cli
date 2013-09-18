**To describe your Availability Zones**

This example describes the Availability Zones that are available to you. The response includes Availability Zones only for the current region.

Command::

  aws ec2 describe-availability-zones

Output::

  {
      "AvailabilityZones": [
          {
              "State": "available",
              "RegionName": "us-east-1",
              "Messages": [],
              "ZoneName": "us-east-1b"
          },
          {
              "State": "available",
              "RegionName": "us-east-1",
              "Messages": [],
              "ZoneName": "us-east-1c"
          },
          {
              "State": "available",
              "RegionName": "us-east-1",
              "Messages": [],
              "ZoneName": "us-east-1d"
          }
      ]
  }
