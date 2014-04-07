**To describe the instance type**

This example describes the instance type of the specified instance.

Command::

  aws ec2 describe-instance-attribute --instance-id i-5203422c --attribute instanceType

Output::

  {
      "InstanceId": "i-5203422c"
      "InstanceType": {
          "Value": "t1.micro"
      }
  }

**To describe the disableApiTermination attribute**

This example describes the ``disableApiTermination`` attribute of the specified instance.

Command::

  aws ec2 describe-instance-attribute --instance-id i-5203422c --attribute disableApiTermination

Output::

  {
      "InstanceId": "i-5203422c"
      "DisableApiTermination": {
          "Value": "false"
      }
  }

**To describe the block device mapping for an instance**

This example describes the ``blockDeviceMapping`` attribute of the specified instance.

Command::

  aws ec2 describe-instance-attribute --instance-id i-5203422c --attribute blockDeviceMapping

Output::

  {
      "InstanceId": "i-5203422c"
      "BlockDeviceMappings": [
          {
              "DeviceName": "/dev/sda1",
              "Ebs": {
                  "Status": "attached",
                  "DeleteOnTermination": true,
                  "VolumeId": "vol-615a1339",
                  "AttachTime": "2013-05-17T22:42:34.000Z"
              }
          },
          {
              "DeviceName": "/dev/sdf",
              "Ebs": {
                  "Status": "attached",
                  "DeleteOnTermination": false,
                  "VolumeId": "vol-9f54b8dc",
                  "AttachTime": "2013-09-10T23:07:00.000Z"
              }
          }
      ],
  }
