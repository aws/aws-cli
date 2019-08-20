**Example 1: To describe all of your enabled regions**

This example describes all Regions that are enabled for your account. 

Command::

  aws ec2 describe-regions

Output::

    {
        "Regions": [
            {
                "Endpoint": "ec2.eu-north-1.amazonaws.com",
                "RegionName": "eu-north-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.ap-south-1.amazonaws.com",
                "RegionName": "ap-south-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.eu-west-3.amazonaws.com",
                "RegionName": "eu-west-3",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.eu-west-2.amazonaws.com",
                "RegionName": "eu-west-2",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.eu-west-1.amazonaws.com",
                "RegionName": "eu-west-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.ap-northeast-3.amazonaws.com",
                "RegionName": "ap-northeast-3",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.ap-northeast-2.amazonaws.com",
                "RegionName": "ap-northeast-2",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.ap-northeast-1.amazonaws.com",
                "RegionName": "ap-northeast-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.sa-east-1.amazonaws.com",
                "RegionName": "sa-east-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.ca-central-1.amazonaws.com",
                "RegionName": "ca-central-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.ap-southeast-1.amazonaws.com",
                "RegionName": "ap-southeast-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.ap-southeast-2.amazonaws.com",
                "RegionName": "ap-southeast-2",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.eu-central-1.amazonaws.com",
                "RegionName": "eu-central-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.us-east-1.amazonaws.com",
                "RegionName": "us-east-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.us-east-2.amazonaws.com",
                "RegionName": "us-east-2",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.us-west-1.amazonaws.com",
                "RegionName": "us-west-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.us-west-2.amazonaws.com",
                "RegionName": "us-west-2",
                "OptInStatus": "opt-in-not-required"
            }
        ]
    }

**Example 2: To describe enabled regions with an endpoint whose name contains a specific string**

This example describes all regions that you have enabled that have the string "us" in the endpoint. ::

    aws ec2 describe-regions --filters "Name=endpoint,Values=*us*"

Output::

    {
        "Regions": [
            {
                "Endpoint": "ec2.us-east-1.amazonaws.com",
                "RegionName": "us-east-1"
            },
            {
                "Endpoint": "ec2.us-east-2.amazonaws.com",
                "RegionName": "us-east-2"
            },
            {
                "Endpoint": "ec2.us-west-1.amazonaws.com",
                "RegionName": "us-west-1"
            },
            {
                "Endpoint": "ec2.us-west-2.amazonaws.com",
                "RegionName": "us-west-2"
            },
        ]
    }

**Example 3: To describe all regions**

The following ``describe-regions`` example describes all available Regions, including opt-in Regions like HKG and BAH. For a description of opt-in Regions, see `Available Regions <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html#concepts-available-regions>`__ in the *Amazon EC2 User Guide*. ::

    aws ec2 describe-regions \
        --all-regions

Output::

    {
        "Regions": [
            {
                "Endpoint": "ec2.eu-north-1.amazonaws.com",
                "RegionName": "eu-north-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.ap-south-1.amazonaws.com",
                "RegionName": "ap-south-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.eu-west-3.amazonaws.com",
                "RegionName": "eu-west-3",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.eu-west-2.amazonaws.com",
                "RegionName": "eu-west-2",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.eu-west-1.amazonaws.com",
                "RegionName": "eu-west-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.ap-northeast-3.amazonaws.com",
                "RegionName": "ap-northeast-3",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.ap-northeast-2.amazonaws.com",
                "RegionName": "ap-northeast-2",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.ap-northeast-1.amazonaws.com",
                "RegionName": "ap-northeast-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.sa-east-1.amazonaws.com",
                "RegionName": "sa-east-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.ca-central-1.amazonaws.com",
                "RegionName": "ca-central-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.ap-east-1.amazonaws.com",
                "RegionName": "ap-east-1",
                "OptInStatus": "not-opted-in"
            },
            {
                "Endpoint": "ec2.ap-southeast-1.amazonaws.com",
                "RegionName": "ap-southeast-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.ap-southeast-2.amazonaws.com",
                "RegionName": "ap-southeast-2",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.eu-central-1.amazonaws.com",
                "RegionName": "eu-central-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.us-east-1.amazonaws.com",
                "RegionName": "us-east-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.us-east-2.amazonaws.com",
                "RegionName": "us-east-2",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.us-west-1.amazonaws.com",
                "RegionName": "us-west-1",
                "OptInStatus": "opt-in-not-required"
            },
            {
                "Endpoint": "ec2.us-west-2.amazonaws.com",
                "RegionName": "us-west-2",
                "OptInStatus": "opt-in-not-required"
            }
        ]
    }

**Example 4: To describe region names only**

This example uses the ``--query`` parameter to filter the output and return the names of the regions only. The output is returned as tab-delimited lines. ::

    aws ec2 describe-regions --query "Regions[].{Name:RegionName}" --output text
  
Output::

  ap-south-1
  eu-west-3
  eu-west-2
  eu-west-1
  ap-northeast-3
  ap-northeast-2
  ap-northeast-1
  sa-east-1
  ca-central-1
  ap-southeast-1
  ap-southeast-2
  eu-central-1
  us-east-1
  us-east-2
  us-west-1
  us-west-2
