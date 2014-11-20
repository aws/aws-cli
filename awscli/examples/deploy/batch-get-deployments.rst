**To get information about multiple deployments**

This example displays information about multiple deployments that are associated with the user's AWS account.

Command::

  aws deploy batch-get-deployments --deployment-ids d-USUAELQEX d-QA4G4F9EX

Output::

  {
      "deploymentsInfo": [
          {
              "applicationName": "WordPress_App",
              "status": "Failed",
              "deploymentOverview": {
                  "Failed": 0,
                  "InProgress": 0,
                  "Skipped": 0,
                  "Succeeded": 1,
                  "Pending": 0
              },
              "deploymentConfigName": "CodeDeployDefault.OneAtATime",
              "creator": "user",
              "deploymentGroupName": "WordPress_DG",
			  "revision": {		  
                "revisionType": "S3",
                "s3Location": {
                  "bundleType": "zip",
                  "version": "uTecLusvCB_JqHFXtfUcyfV8bEXAMPLE",
                  "bucket": "CodeDeployDemoBucket",
                  "key": "WordPressApp.zip"
				}
              },
              "deploymentId": "d-QA4G4F9EX",
              "createTime": 1408480721.9,
              "completeTime": 1408480741.822
          },
          {
              "applicationName": "MyOther_App",
              "status": "Failed",
              "deploymentOverview": {
                  "Failed": 1,
                  "InProgress": 0,
                  "Skipped": 0,
                  "Succeeded": 0,
                  "Pending": 0
              },
              "deploymentConfigName": "CodeDeployDefault.OneAtATime",
              "creator": "user",
              "errorInformation": {
                  "message": "Deployment failed: Constraint default violated: No hosts succeeded.",
                  "code": "HEALTH_CONSTRAINTS"
              },
              "deploymentGroupName": "MyOther_DG",
			  "revision": {		  
                "revisionType": "S3",
                "s3Location": {
                  "bundleType": "zip",
                  "eTag": "\"dd56cfd59d434b8e768f9d77fEXAMPLE\"",
                  "bucket": "CodeDeployDemoBucket",
                  "key": "MyOtherApp.zip"
				}
              },
              "deploymentId": "d-USUAELQEX",
              "createTime": 1409764576.589,
              "completeTime": 1409764596.101
          }
      ]
  }
