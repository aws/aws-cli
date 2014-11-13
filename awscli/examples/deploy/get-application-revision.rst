**To get information about an application revision**

This example displays information about an application revision that is associated with the specified application.

Command::

  aws deploy get-application-revision --application-name WordPress_App --s3-location bucket=CodeDeployDemoBucket,bundleType=zip,eTag=dd56cfd59d434b8e768f9d77fEXAMPLE,key=WordPressApp.zip

Output::

  {
      "applicationName": "WordPress_App",
      "revisionInfo": {
          "description": "Application revision registered by Deployment ID: d-N65I7GEX",
          "registerTime": 1411076520.009,
          "deploymentGroups": "WordPress_DG",
          "lastUsedTime": 1411076520.009,
          "firstUsedTime": 1411076520.009
      },
      "revision": {
	      "revisionType": "S3",
		  "s3Location": {
		    "bundleType": "zip",
            "eTag": "dd56cfd59d434b8e768f9d77fEXAMPLE",
            "bucket": "CodeDeployDemoBucket",
            "key": "WordPressApp.zip"
	      }
      }
  }