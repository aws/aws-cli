**To export an instance**

This example command creates a task to export the instance i-38e485d8 to the Amazon S3 bucket
myexportbucket.

Command::

  aws ec2 create-instance-export-task --description "W2K12 instance" --instance-id i-38e485d8  --target-environment <value>vmware --export-to-s3-task DiskImageFormat=vmdk,ContainerFormat=ova,S3Bucket=myexportbucket,S3Prefix=w2k12

Output::

  {
