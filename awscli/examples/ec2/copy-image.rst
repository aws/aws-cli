**To copy an AMI to another region**

This example copies the specified AMI from the ``us-east-1`` region to the ``ap-northeast-1`` region.

Command::

  aws ec2 copy-image --source-image-id ami-5731123e --source-region us-east-1 --region ap-northeast-1 --name "My server"

Output::

  {
      "ImageId": "ami-438bea42"
  }