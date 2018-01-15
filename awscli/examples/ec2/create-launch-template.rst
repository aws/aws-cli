**To create a launch template**

This example creates a launch template that specifies the subnet in which to launch the instance (``subnet-7b16de0c``), assigns a public IP address and an IPv6 address to the instance, and creates a tag for the instance (``Name=webserver``).

Command::

  aws ec2 create-launch-template --launch-template-name TemplateForWebServer --version-description WebVersion1 --launch-template-data '{"NetworkInterfaces":[{"AssociatePublicIpAddress":true,"DeviceIndex":0,"Ipv6AddressCount":1,"SubnetId":"subnet-7b16de0c"}],"ImageId":"ami-8c1be5f6","InstanceType":"t2.small","TagSpecifications":[{"ResourceType":"instance","Tags":[{"Key":"Name","Value":"webserver"}]}]}'

Output::

  {
    "LaunchTemplate": {
        "LatestVersionNumber": 1, 
        "LaunchTemplateId": "lt-01238c059e3466abc", 
        "LaunchTemplateName": "TemplateForWebServer", 
        "DefaultVersionNumber": 1, 
        "CreatedBy": "arn:aws:iam::123456789012:root", 
        "CreateTime": "2017-11-27T09:13:24.000Z"
    }
  }