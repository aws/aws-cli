**Example 1: To create an API**

The following ``create-rest-api`` example creates an API named ``My First API``. ::

    aws apigateway create-rest-api \
        --name 'My First API' \
        --description 'This is my first API'

**Example 2: To create a duplicate API from an existing API**

The following ``create-rest-api`` example creates a duplicate of an existing API by cloning it. ::

    aws apigateway create-rest-api \
        --name 'Copy of My First API' \
        --description 'This is a copy of my first API' \
        --clone-from 1234123412
