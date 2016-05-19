**To describe your regions**

This example describes all the regions that are available to you.

Command::

  aws ec2 describe-regions

Output::

  {
      "Regions": [
          {
              "Endpoint": "ec2.eu-west-1.amazonaws.com",
              "RegionName": "eu-west-1"
          },
          {
              "Endpoint": "ec2.ap-southeast-1.amazonaws.com",
              "RegionName": "ap-southeast-1"
          },
          {
              "Endpoint": "ec2.ap-southeast-2.amazonaws.com",
              "RegionName": "ap-southeast-2"
          },
          {
              "Endpoint": "ec2.eu-central-1.amazonaws.com",
              "RegionName": "eu-central-1"
          },
          {
              "Endpoint": "ec2.ap-northeast-2.amazonaws.com",
              "RegionName": "ap-northeast-2"
          },
          {
              "Endpoint": "ec2.ap-northeast-1.amazonaws.com",
              "RegionName": "ap-northeast-1"
          },
          {
              "Endpoint": "ec2.us-east-1.amazonaws.com",
              "RegionName": "us-east-1"
          },
          {
              "Endpoint": "ec2.sa-east-1.amazonaws.com",
              "RegionName": "sa-east-1"
          },
          {
              "Endpoint": "ec2.us-west-1.amazonaws.com",
              "RegionName": "us-west-1"
          },
          {
              "Endpoint": "ec2.us-west-2.amazonaws.com",
              "RegionName": "us-west-2"
          }
      ]
  }

**To describe the regions with an endpoint that has a specific string**

This example describes all regions that are available to you that have the string "us" in the endpoint.

Command::

  aws ec2 describe-regions --filters "Name=endpoint,Values=*us*"

Output::

  {
      "Regions": [
          {
              "Endpoint": "ec2.us-east-1.amazonaws.com",
              "RegionName": "us-east-1"
          },
          {
              "Endpoint": "ec2.us-west-2.amazonaws.com",
              "RegionName": "us-west-2"
          },
          {
              "Endpoint": "ec2.us-west-1.amazonaws.com",
              "RegionName": "us-west-1"
          },
      ]
  }
