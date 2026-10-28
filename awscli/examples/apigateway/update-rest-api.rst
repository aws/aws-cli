**Example 1: To change the name of an API**

The following ``update-rest-api`` example changes the name of an API. ::

    aws apigateway update-rest-api \
        --rest-api-id 1234123412 \
        --patch-operations op=replace,path=/name,value='New Name'

**Example 2: To change the description of an API**

The following ``update-rest-api`` example changes the description of an API. ::

    aws apigateway update-rest-api \
        --rest-api-id 1234123412 \
        --patch-operations op=replace,path=/description,value='New Description'
