**To create a stage in an API which will contain an existing deployment in the specified region**

Command::

  aws apigateway create-stage --rest-api-id 1234123412 --stage-name 'dev' --description 'Development stage' --deployment-id a1b2c3 --region us-west-2

**To create a stage in an API which will contain an existing deployment and custom Stage Variables in the specified region**

Command::

  aws apigateway create-stage --rest-api-id 1234123412 --stage-name 'dev' --description 'Development stage' --deployment-id a1b2c3 --variables key='value',otherKey='otherValue' --region us-west-2

