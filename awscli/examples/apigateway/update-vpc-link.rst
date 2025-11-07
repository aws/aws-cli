**Example 1: To update an existing VPC link name**

The following ``update-vpc-link`` example updates the name of the specified VPC link. ::

    aws apigateway update-vpc-link  \
        --vpc-link-id ab3de6 \
        --patch-operations op=replace,path=/name,value=my-vpc-link

Output::

    {
        "id": "ab3de6",
        "name": "my-vpc-link",
        "targetArns": [
            "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/my-lb/12a456s89aaa12345"
        ],
        "status": "AVAILABLE",
        "statusMessage": "Your vpc link is ready for use",
        "tags": {}
    }

For more information, see `Updating existing VPC link <https://docs.aws.amazon.com/cli/latest/reference/apigateway/update-vpc-link.html>`__ in the *AWS CLI Command Reference*.


**Example 2: To update an existing VPC link name and description**

The following ``update-vpc-link`` example updates name of the specified VPC link. ::

    aws apigateway update-vpc-link  \
        --vpc-link-id ab3de6 \
        --patch-operations op=replace,path=/name,value=my-vpc-link op=replace,path=/description,value="My custom description"

Output::

    {
        "id": "ab3de6",
        "name": "my-vpc-link",
        "description": "My custom description",
        "targetArns": [
            "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/my-lb/12a456s89aaa12345"
        ],
        "status": "AVAILABLE",
        "statusMessage": "Your vpc link is ready for use",
        "tags": {}
    }

For more information, see `Updating existing VPC link <https://docs.aws.amazon.com/cli/latest/reference/apigateway/update-vpc-link.html>`__ in the *AWS CLI Command Reference*.
