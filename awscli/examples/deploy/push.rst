**To bundle and deploy an AWS CodeDeploy compatible application revision to Amazon S3**

This example bundles and deploys an application revision to Amazon S3 and then associates the application revision with the specified application.

Use the output of the push command to create a deployment that uses the uploaded application revision.

Command::

  aws deploy push --application-name WordPress_App --description "This is my deployment" --ignore-hidden-files --s3-location s3://CodeDeployDemoBucket/WordPressApp.zip --source /tmp/MyLocalDeploymentFolder/

Output::

  To deploy with this revision, run: 
  aws deploy create-deployment --application-name WordPress_App --deployment-config-name <deployment-config-name> --deployment-group-name <deployment-group-name> --s3-location bucket=CodeDeployDemoBucket,key=WordPressApp.zip,bundleType=zip,eTag="cecc9b8a08eac650a6e71fdb88EXAMPLE",version=LFsJAUd_2J4VWXfvKtvi79L8EXAMPLE