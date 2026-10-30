**To test invoke a request to a Custom Authorizer including the required header and value**

The following ``test-invoke-authorizer`` example tests a request to a Custom Authorizer including the required header and value. ::

    aws apigateway test-invoke-authorizer --rest-api-id 1234123412 --authorizer-id 5yid1t --headers Authorization='Value'
