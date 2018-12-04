**To create an API in the specified region**

Command::

  aws apigateway create-rest-api --name 'My First API' --description 'This is my first API' --region us-west-2

**To create a duplicate API in the specified region from an existing API in the same region**

Command::

  aws apigateway create-rest-api --name 'Copy of My First API' --description 'This is a copy of my first API' --clone-from 1234123412 --region us-west-2

