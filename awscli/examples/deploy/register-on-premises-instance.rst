**To register an on-premises instance**

The following ``register-on-premises-instance`` example registers an on-premises instance with AWS CodeDeploy. It does not create the specified IAM user, nor does it associate in AWS CodeDeploy any on-premises instances tags with the registered instance. ::

    aws deploy register-on-premises-instance \
        --instance-name AssetTag12010298EX \
        --iam-user-arn arn:aws:iam::80398EXAMPLE:user/CodeDeployDemoUser-OnPrem

This command produces no output.

For more information, see `Use the register-on-premises-instance command (IAM user ARN) to register an on-premises instance <https://docs.aws.amazon.com/codedeploy/latest/userguide/register-on-premises-instance-iam-user-arn.html>`__ in the *AWS CodeDeploy User Guide*.
