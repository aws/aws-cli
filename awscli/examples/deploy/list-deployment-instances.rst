**To get information about deployment instances**

This example displays information about all deployment instances that are associated with the specified deployment.

Command::

  aws deploy list-deployment-instances --deployment-id d-9DI6I4EX --instance-status-filter Succeeded

Output::

  {
      "instancesList": [
          "i-8c4490EX",
		  "i-7d5389EX"
      ]
  }