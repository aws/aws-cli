**To describe your Availability Zones**

This example describes the Availability Zones that are available to you. The response includes Availability Zones only for the current region.

Command::

  aws ec2 describe-availability-zones

Output::

  {
      "AvailabilityZones": [
          {
              "State": "available",
              "Messages": [],
              "RegionName": "us-west-2",
              "ZoneName": "us-west-2a",
              "ZoneId": "usw2-az2"
          },
          {
              "State": "available",
              "Messages": [],
              "RegionName": "us-west-2",
              "ZoneName": "us-west-2b",
              "ZoneId": "usw2-az1"
          },
          {
              "State": "available",
              "Messages": [],
              "RegionName": "us-west-2",
              "ZoneName": "us-west-2c",
              "ZoneId": "usw2-az3"
          }
      ]
  }
