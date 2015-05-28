**To request Spot Instances**

This example command creates a Spot Instance request for five instances in a default VPC or EC2-Classic.

Command::

  aws ec2 request-spot-instances --spot-price "0.050" --instance-count 5 --type "one-time" --launch-specification {\"ImageId\":\"ami-1a2b3c4d\",\"InstanceType\":"t1.micro\",\"Placement\":{\"AvailabilityZone\":\"us-west-2a\"}}

Output::

  {
    "SpotInstanceRequests": [
        {
            "Status": {
                "UpdateTime": "2014-03-25T20:54:21.000Z",
                "Code": "pending-evaluation",
                "Message": "Your Spot request has been submitted for review, and is pending evaluation."
            },
            "ProductDescription": "Linux/UNIX",
            "SpotInstanceRequestId": "sir-df6f405d",
            "State": "open",
            "LaunchSpecification": {
                "Placement": {
                    "AvailabilityZone": "us-west-2a"
                },
                "SecurityGroups": [
                    {
                        "GroupName": "default",
                        "GroupId": "sg-223b284e"
                    }
                ],
                "InstanceType": "t1.micro",
                "Monitoring": {
                    "Enabled": false
                },
                "ImageId": "ami-1a2b3c4d"
            },
            "Type": "one-time",
            "CreateTime": "2014-03-25T20:54:20.000Z",
            "SpotPrice": "0.050000"
        },
        ...
    ]
  }

This example command creates a Spot Instance request for five instances in a nondefault VPC.

Command::

  aws ec2 request-spot-instances --spot-price "0.050" --instance-count 5 --type "one-time" --launch-specification {\"ImageId\":\"ami-a43909e1\",\"InstanceType\":"t2.micro\",\"SubnetId\":\"subnet-d50bfebc\"}

Output::

  {
    "SpotInstanceRequests": [
        {
            "Status": {
               "UpdateTime": "2014-03-25T22:21:58.000Z",
               "Code": "pending-evaluation",
               "Message": "Your Spot request has been submitted for review, and is pending evaluation."
            },
            "ProductDescription": "Linux/UNIX",
            "SpotInstanceRequestId": "sir-df6f405d",
            "State": "open",
            "LaunchSpecification": {
               "Placement": {
                   "AvailabilityZone": "us-west-2a"
               }
               "ImageId": "ami-a43909e1"
               "SecurityGroups": [
                   {
                       "GroupName": "default",
                       "GroupID": "sg-223b284e"
                   }
               ]
               "SubnetId": "subnet-d50bfebc",
               "Monitoring": {
                   "Enabled": false
               },
               "InstanceType": "t2.micro",
           },
           "Type": "one-time",
           "CreateTime": "2014-03-25T22:21:58.000Z",
           "SpotPrice": "0.050000"
        },
        ...
    ]
  }

To assign a public IP address to the Spot Instances that you launch in a nondefault VPC, use the following command: 

Command::

  aws ec2 request-spot-instances --spot-price "0.050" --instance-count 1 --type "one-time" --launch-specification "{\"ImageId\":\"ami-e7527ed7\",\"InstanceType\":\"m3.medium\",\"NetworkInterfaces\":[{\"DeviceIndex\":0,\"SubnetId\":\"subnet-e4f33493\",\"AssociatePublicIpAddress\":true}]}"
