**To describe Spot Instance requests**

This example describes all of your Spot Instance requests.

Command::

  aws ec2 describe-spot-instance-requests

Output::

  {
    "SpotInstanceRequests": [
      {
        "Status": {
          "UpdateTime": "2014-04-30T18:16:21.000Z",
          "Code": "fulfilled",
          "Message": "Your Spot request is fulfilled."
        },
        "ProductDescription": "Linux/UNIX",
        "InstanceId": "i-1234567890abcdef0",
        "SpotInstanceRequestId": "sir-08b93456",
        "State": "active",
        "LaunchedAvailabilityZone": "us-west-1b",
        "LaunchSpecification": {
          "ImageId": "ami-7aba833f",
          "KeyName": "May14Key",
          "BlockDeviceMappings": [
            {
              "DeviceName": "/dev/sda1",
              "Ebs": {
                "DeleteOnTermination": true,
                "VolumeType": "standard",
                "VolumeSize": 8
              }
            }
          ],
          "EbsOptimized": false,
          "SecurityGroups": [
            {
              "GroupName": "launch-wizard-1",
              "GroupId": "sg-e38f24a7"
            }
          ],
          "InstanceType": "m1.small"
        },
        "Type": "one-time",
        "CreateTime": "2014-04-30T18:14:55.000Z",
        "SpotPrice": "0.010000"
      },
      {
        "Status": {
          "UpdateTime": "2014-04-30T18:16:21.000Z",
          "Code": "fulfilled",
          "Message": "Your Spot request is fulfilled."
        },
        "ProductDescription": "Linux/UNIX",
        "InstanceId": "i-1234567890abcdef1",
        "SpotInstanceRequestId": "sir-285b1e56",
        "State": "active",
        "LaunchedAvailabilityZone": "us-west-1b",
        "LaunchSpecification": {
          "ImageId": "ami-7aba833f",
          "KeyName": "May14Key",
          "BlockDeviceMappings": [
            {
              "DeviceName": "/dev/sda1",
              "Ebs": {
                "DeleteOnTermination": true,
                "VolumeType": "standard",
                "VolumeSize": 8
              }
            }
          ],
          "EbsOptimized": false,
          "SecurityGroups": [
            {
              "GroupName": "launch-wizard-1",
              "GroupId": "sg-e38f24a7"
            }
          ],
          "InstanceType": "m1.small"
        },
        "Type": "one-time",
        "CreateTime": "2014-04-30T18:14:55.000Z",
        "SpotPrice": "0.010000"
      }
    ]
  }

