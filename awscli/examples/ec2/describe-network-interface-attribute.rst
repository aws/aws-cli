**To describe the attachment attribute of a network interface**

This example command describes the <code>attachment</code> attribute of the specified network interface.

Command::

  aws ec2 describe-network-interface-attribute --network-interface-id eni-686ea200 --attribute attachment
  
Output::

  {
    "NetworkInterfaceId": "eni-686ea200",
    "Attachment": {
        "Status": "attached",
        "DeviceIndex": 0,
        "AttachTime": "2015-05-21T20:02:20.000Z",
        "InstanceId": "i-d5652e23",
        "DeleteOnTermination": true,
        "AttachmentId": "eni-attach-43348162",
        "InstanceOwnerId": "123456789012"
    }
  }

**To describe the description attribute of a network interface**

This example command describes the <code>description</code> attribute of the specified network interface.

Command::

  aws ec2 describe-network-interface-attribute --network-interface-id eni-686ea200 --attribute description 
  
Output::

  {
    "NetworkInterfaceId": "eni-686ea200",
    "Description": {
        "Value": "My description"
    }
  }

**To describe the groupSet attribute of a network interface**

This example command describes the <code>groupSet</code> attribute of the specified network interface.

Command::

  aws ec2 describe-network-interface-attribute --network-interface-id eni-686ea200 --attribute groupSet
  
Output::

  {
    "NetworkInterfaceId": "eni-686ea200",
    "Groups": [
        {
            "GroupName": "my-security-group",
            "GroupId": "sg-903004f8"
        }
    ]
  }

**To describe the sourceDestCheck attribute of a network interface**

This example command describes the <code>sourceDestCheck</code> attribute of the specified network interface.

Command::

  aws ec2 describe-network-interface-attribute --network-interface-id eni-686ea200 --attribute sourceDestCheck
  
Output::

  {
    "NetworkInterfaceId": "eni-686ea200",
    "SourceDestCheck": {
        "Value": true
    }
  }
