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
              "Endpoint": "ec2.ap-south-1.amazonaws.com",
              "RegionName": "ap-south-1"
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

**To describe region names only**

This example uses the ``--query`` parameter to filter the output and return the names of the regions only. The output is returned as tab-delimited lines.

Command::

  aws ec2 describe-regions --query 'Regions[].{Name:RegionName}' --output text
  
Output::

  ap-south-1
  eu-west-1
  ap-southeast-1
  ap-southeast-2
  eu-central-1
  ap-northeast-2
  ap-northeast-1
  us-east-1
  sa-east-1
  us-west-1
  us-west-2
