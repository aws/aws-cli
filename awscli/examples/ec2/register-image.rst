**To register an AMI using a manifest file**

This example registers an AMI using the specified manifest file in Amazon S3.

Command::

  aws ec2 register-image --image-location my-s3-bucket/myimage/image.manifest.xml --name "MyImage"

Output::

  {
      "ImageId": "ami-61341708"
  }