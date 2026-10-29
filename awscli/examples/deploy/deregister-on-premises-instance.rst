**To deregister an on-premises instance**

The following ``deregister-on-premises-instance`` example deregisters an on-premises instance with AWS CodeDeploy, but it does not delete the IAM user associated with the instance, nor does it disassociate in AWS CodeDeploy the on-premises instance tags from the instance. It also does not uninstall the AWS CodeDeploy Agent from the instance nor remove the on-premises configuration file from the instance. ::

    aws deploy deregister-on-premises-instance \
        --instance-name AssetTag12010298EX

This command produces no output.

For more information, see `Manually deregister an on-premises instance <https://docs.aws.amazon.com/codedeploy/latest/userguide/on-premises-instances-operations-deregister-manually.html>`__ in the *AWS CodeDeploy User Guide*.
