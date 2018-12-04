**To create the required IAM role for Amazon DLM

Amazon DLM creates the **AWSDataLifecycleManagerDefaultRole** role the first time that you create a lifecycle policy using the AWS Management Console. If you are not using the console, you can use the following command to create this role.::

  aws dlm create-default-role
