**To create an API key that is enabled for an existing API and Stage**

The following ``create-api-key`` example creates an API key that is enabled for an existing API and stage. ::

    aws apigateway create-api-key --name 'Dev API Key' --description 'Used for development' --enabled --stage-keys restApiId='a1b2c3d4e5',stageName='dev'
