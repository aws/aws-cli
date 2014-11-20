**To create a deployment**

This example creates a deployment and associates it with the user's AWS account.

Command::

  aws deploy create-deployment --application-name WordPress_App --deployment-config-name CodeDeployDefault.OneAtATime --deployment-group-name WordPress_DG --description "My demo deployment" --s3-location bucket=CodeDeployDemoBucket,bundleType=zip,eTag=dd56cfd59d434b8e768f9d77fEXAMPLE,key=WordPressApp.zip

Output::

  {
      "deploymentId": "d-N65YI7Gex"
  }