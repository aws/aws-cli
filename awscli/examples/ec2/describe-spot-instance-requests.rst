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
            "InstanceId": "i-20170a7c", 
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
                            "VolumeSize": 8, 
                            "VolumeType": "standard"
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
            "InstanceId": "i-894f53d5", 
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
                            "VolumeSize": 8, 
                            "VolumeType": "standard"
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
        ...
        }
    ]
}
        
        
**To describe persistent Spot Instance requests that launched specific instance types**

This example uses filters to describe all persistent Spot Instance requests that have resulted in the launch of at least one m3.medium instance, in the us-west-1b Availability Zone.

Command::

  aws ec2 describe-spot-instance-requests --filters Name=launch.instance-type,Values=m3.medium, Name=type,Values=persistent

Output::
{
    "SpotInstanceRequests": [
        {
            "Status": {
                "UpdateTime": "2014-04-30T21:03:29.000Z", 
                "Code": "fulfilled", 
                "Message": "Your Spot request is fulfilled."
            }, 
            "ProductDescription": "Linux/UNIX", 
            "InstanceId": "i-de485482", 
            "SpotInstanceRequestId": "sir-3db31c5d", 
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
                            "VolumeSize": 8, 
                            "VolumeType": "standard"
                        }
                    }
                ], 
                "EbsOptimized": false, 
                "SecurityGroups": [
                    {
                        "GroupName": "launch-wizard-2", 
                        "GroupId": "sg-c1822985"
                    }
                ], 
                "InstanceType": "m1.small"
            }, 
            "Type": "persistent", 
            "CreateTime": "2014-04-30T21:00:25.000Z", 
            "SpotPrice": "0.010000"
        }, 
        {
            "Status": {
                "UpdateTime": "2014-04-30T21:03:30.000Z", 
                "Code": "fulfilled", 
                "Message": "Your Spot request is fulfilled."
            }, 
            "ProductDescription": "Linux/UNIX", 
            "InstanceId": "i-844955d8", 
            "SpotInstanceRequestId": "sir-48e8425d", 
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
                            "VolumeSize": 8, 
                            "VolumeType": "standard"
                        }
                    }
                ], 
                "EbsOptimized": false, 
                "SecurityGroups": [
                    {
                        "GroupName": "launch-wizard-2", 
                        "GroupId": "sg-c1822985"
                    }
                ], 
                "InstanceType": "m1.small"
            }, 
            "Type": "persistent", 
            "CreateTime": "2014-04-30T21:00:25.000Z", 
            "SpotPrice": "0.010000"
        }, 
        ...
        }
    ]
}

