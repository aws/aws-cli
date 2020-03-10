**To log in to an Amazon ECR registry**

This command retrieves and displays a password that you can use to authenticate to any Amazon ECR registry that your IAM principal has access to. The password is valid for 12 hours. You can pass the password to the login command of the container client of your preference, such as the Docker CLI. After you have authenticated to an Amazon ECR registry with this command, you can use the Docker CLI to push and pull images from that registry until the token expires.

This command is supported using the latest version of AWS CLI version 2 or in v1.17.10 or later of AWS CLI version 1. For information on updating to the latest AWS CLI version, see `Installing the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html>`__ in the *AWS Command Line Interface User Guide*.
