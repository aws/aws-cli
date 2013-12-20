**To create an AMI from an Amazon EBS-backed instance**

This example creates an AMI from the specified instance.

Command::

  aws ec2 create-image --instance-id i-10a64379 --name "My server" --description "An AMI for my server"

Output::

  {
      "ImageId": "ami-5731123e"
  }