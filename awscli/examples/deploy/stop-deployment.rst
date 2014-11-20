**To attempt to stop a deployment**

This example attempts to stop an in-progress deployment that is associated with the user's AWS account.

Command::

  aws deploy stop-deployment --deployment-id d-8365D4OEX

Output::

  {
      "status": "Succeeded", 
      "statusMessage": "No more commands will be scheduled for execution in the deployment instances"
  }