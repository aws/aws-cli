**To get the per-region list of deployments for a REST API**

Command::

  aws apigateway get-deployments --rest-api-id 1234123412 --region us-west-2

Output::

  {
      "items": [
          {
              "createdDate": 1453797217, 
              "id": "0a2b4c", 
              "description": "Deployed my API for the first time"
          }
      ]
  }

