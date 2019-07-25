**Example 1: To modify the instance type**

This example modifies the instance type of the specified instance. The instance must be in the ``stopped`` state. If the command succeeds, no output is returned.

Command::

  aws ec2 modify-instance-attribute --instance-id i-1234567890abcdef0 --instance-type "{\"Value\": \"m1.small\"}"

**Example 2: To enable enhanced networking on an instance**

This example enables enhanced networking for the specified instance. The instance must be in the ``stopped`` state. If the command succeeds, no output is returned.

Command::

  aws ec2 modify-instance-attribute --instance-id i-1234567890abcdef0 --sriov-net-support simple

**Example 3: To modify the sourceDestCheck attribute**

This example sets the ``sourceDestCheck`` attribute of the specified instance to ``true``. The instance must be in a VPC. If the command succeeds, no output is returned.

Command::

  aws ec2 modify-instance-attribute --instance-id i-1234567890abcdef0 --source-dest-check "{\"Value\": true}"

**Example 4: To modify the deleteOnTermination attribute of the root volume**

This example sets the ``deleteOnTermination`` attribute for the root volume of the specified Amazon EBS-backed instance to ``false``. By default, this attribute is ``true`` for the root volume. If the command succeeds, no output is returned.

Command::

  aws ec2 modify-instance-attribute --instance-id i-1234567890abcdef0 --block-device-mappings "[{\"DeviceName\": \"/dev/sda1\",\"Ebs\":{\"DeleteOnTermination\":false}}]"

**Example 5: To modify the user data attached to an instance**

The following ``modify-instance-attribute`` example adds the contents of the file ``UserData.txt`` as the UserData for the specified instance. The contents of the file must be base64 encoded. The first command converts the text file to base64 and saves it as a new file. That file is then referenced in the CLI command that follows.

Command::

    base64 UserData.txt > UserData.base64.txt

    aws ec2 modify-image-attribute \
        --instance-id=i-09b5a14dbca622e76 \
        --attribute userData --value file://UserData.base64.txt"

Contents of ``UserData.txt``::

    #!/bin/bash
    yum update -y
    service httpd start
    chkconfig httpd on

This command produces no output.

For more information, see `User Data and the AWS CLI <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html#user-data-api-cli>`__ in the *EC2 User Guide*.
