**To get information about deployment groups**

This example displays information about all deployment groups that are associated with the specified application.

Command::

  aws deploy list-deployment-groups --application-name WordPress_App

Output::

  {
      "applicationName": "WordPress_App",
      "deploymentGroups": [
          "WordPress_DG",
		  "WordPress_Beta_DG"
      ]
  }