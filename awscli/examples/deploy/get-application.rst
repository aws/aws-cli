**To get information about an application**

This example displays information about an application that is associated with the user's AWS account.

Command::

  aws deploy get-application --application-name WordPress_App

Output::

  {
      "application": {
          "applicationName": "WordPress_App",
          "applicationId": "d9dd6993-f171-44fa-a811-211e4EXAMPLE",
          "createTime": 1407878168.078,
		  "linkedToGitHub": false
      }
  }