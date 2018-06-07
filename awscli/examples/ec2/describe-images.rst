**To describe a specific AMI**

This example describes the specified AMI.

Command::

  aws ec2 describe-images --image-ids ami-5731123e

Output::

  {
      "Images": [
          {
              "VirtualizationType": "paravirtual",
              "Name": "My server",
              "Hypervisor": "xen",
              "ImageId": "ami-5731123e",
              "RootDeviceType": "ebs",
              "State": "available",
              "BlockDeviceMappings": [
                  {
                      "DeviceName": "/dev/sda1",
                      "Ebs": {
                          "DeleteOnTermination": true,
                          "SnapshotId": "snap-1234567890abcdef0",
                          "VolumeSize": 8,
                          "VolumeType": "standard"
                      }
                  }
              ],
              "Architecture": "x86_64",
              "ImageLocation": "123456789012/My server",
              "KernelId": "aki-88aa75e1",
              "OwnerId": "123456789012",
              "RootDeviceName": "/dev/sda1",
              "Public": false,
              "ImageType": "machine",
              "Description": "An AMI for my server"
          }
      ]
  }

**To describe Windows AMIs from Amazon that are backed by Amazon EBS**

This example describes Windows AMIs provided by Amazon that are backed by Amazon EBS.

Command::

  aws ec2 describe-images --owners amazon --filters "Name=platform,Values=windows" "Name=root-device-type,Values=ebs"

**To describe tagged AMIs**

This example describes all AMIs that have the tag ``Custom=Linux1``. The output is filtered to display only the AMI IDs.

Command::

  aws ec2 describe-images --filters "Name=tag:Custom,Values=Linux1" --query 'Images[*].{ID:ImageId}'

Output::

   [
     {
        "ID": "ami-1a2b3c4d"
     }, 
     {
        "ID": "ami-ab12cd34"
     }
   ]
