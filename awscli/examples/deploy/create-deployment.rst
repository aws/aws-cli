**To create a deployment**

The following ``create-deployment`` example creates a deployment and associates it with the user's AWS account. ::

    aws deploy create-deployment \
        --application-name WordPress_App \
        --deployment-config-name CodeDeployDefault.OneAtATime \
        --deployment-group-name WordPress_DG \
        --description "My demo deployment" \
        --s3-location bucket=CodeDeployDemoBucket,bundleType=zip,eTag=dd56cfdEXAMPLE8e768f9d77fEXAMPLE,key=WordPressApp.zip

Output::

    {
        "deploymentId": "d-A1B2C3111"
    }
