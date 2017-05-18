**To override the stage settings and disable full request/response logging for a specific resource and method in an API's stage**

Command::

  aws apigateway update-stage --rest-api-id 1234123412 --stage-name 'dev' --patch-operations op=replace,path=/~1resourceName/GET/logging/dataTrace,value=false

**To enable full request/response logging for all resources/methods in an API's stage**

Command::

  aws apigateway update-stage --rest-api-id 1234123412 --stage-name 'dev' --patch-operations op=replace,path=/*/*/logging/dataTrace,value=true
