**To request Spot Instances**

This example command creates a Spot Instances request for five m1.small instances in a VPC.

Command::

  aws ec2 request-spot-instances --spot-price "0.050" --instance-count 5 --type "one-time" --launch-specification "{\"ImageId\":\"ami-a43909e1\",\"InstanceType\":
  "m1.small\",\"SubnetId\":\"subnet-d50bfebc\"}"

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
                   "SubnetId": "subnet-d50bfebc",
                   "Placement": {
                       "AvailabilityZone": "us-west-1c"
                   }
                   "SecurityGroups": [
                       {
                           "GroupName": "default",
                           "GroupID": "sg-223b284e"
                       }
                   ]
                   "InstanceType": "m1.small",
                   "ImageId": "ami-a43909e1"
               },
               "Type": "one-time",
               "CreateTime": "2014-03-25T22:21:58.000Z",
               "SpotPrice": "0.050000"
            },
            {
               "Status": {
                   "UpdateTime": "2014-03-25T22:21:58:000Z",
                   "Code": "pending-evaluation",
                   "Message": "Your Spot request has been submitted for review, and is pending evaluation."
               },
               "ProductDescription": "Linux/UNIX",
               "SpotInstanceRequestId": "sir-696e265d",
               "State": "open",
               "LaunchSpecification": {
                   "SubnetId": "subnet-d50bfebc",
                   "Placement": {
                       "AvailabilityZone": "us-west-1c"
                   },
                   "SecurityGroups": [
                       {
                           "GroupName": "default",
                           "GroupId": "sg-223b284e"
                       }
                   ]
                   "InstanceType": "m1.small",
                   "ImageId": "ami-a43909e1"
               },
               "Type": "one-time",
               "CreateTime": "2014-03-25T22:21:58.000Z",
               "SpotPrice": "0.050000"
            },
            ...
            }
   ]
  }

