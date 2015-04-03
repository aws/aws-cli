**To uninstall an on-premises instance**

This example uninstalls the AWS CodeDeploy Agent from the on-premises instance, and it removes the on-premises configuration file from the instance. It does not deregister the instance in AWS CodeDeploy, nor disassociate any on-premises instance tags in AWS CodeDeploy from the instance, nor delete the IAM user that is associated with the instance. 

Command::

  aws deploy uninstall

Output::

  This command produces no output.