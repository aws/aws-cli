**To get information about a deployment**

This example displays information about a deployment that is associated with the user's AWS account.

Command::

  aws deploy get-deployment --deployment-id d-USUAELQEX

Output::

  {
      "deploymentInfo": {
          "applicationName": "WordPress_App",
          "status": "Succeeded",
          "deploymentOverview": {
              "Failed": 0,
              "InProgress": 0,
              "Skipped": 0,
              "Succeeded": 1,
              "Pending": 0
          },
          "deploymentConfigName": "CodeDeployDefault.OneAtATime",
          "creator": "user",
		  "description": "My WordPress app deployment",
		  "revision": {		  
            "revisionType": "S3",
            "s3Location":  {
              "bundleType": "zip",
              "eTag": "\"dd56cfd59d434b8e768f9d77fEXAMPLE\"",
              "bucket": "CodeDeployDemoBucket",
              "key": "WordPressApp.zip"
			}
          },
          "deploymentId": "d-USUAELQEX",
          "deploymentGroupName": "WordPress_DG",
		  "createTime": 1409764576.589,
          "completeTime": 1409764596.101,
		  "ignoreApplicationStopFailures": false
      }
  }