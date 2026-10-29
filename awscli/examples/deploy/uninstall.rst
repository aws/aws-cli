**To uninstall an on-premises instance**

The following ``uninstall`` example uninstalls the AWS CodeDeploy Agent from the on-premises instance and removes the on-premises configuration file from the instance. It doesn't deregister the instance in AWS CodeDeploy, nor disassociate any on-premises instance tags in AWS CodeDeploy from the instance, nor delete the IAM user that is associated with the instance. ::

    aws deploy uninstall

This command produces no output.

For more information, see `Automatically uninstall the CodeDeploy agent and remove the configuration file from an on-premises instance <https://docs.aws.amazon.com/codedeploy/latest/userguide/on-premises-instances-operations-uninstall-agent.html>`__ in the *AWS CodeDeploy User Guide*.
