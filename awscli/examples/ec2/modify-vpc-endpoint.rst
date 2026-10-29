**Example 1: To modify a gateway endpoint**

The following ``modify-vpc-endpoint`` example modifies gateway endpoint ``vpce-1a2b3c4d`` by associating route table ``rtb-aaa222bb`` with the endpoint, and resetting the policy document. ::

    aws ec2 modify-vpc-endpoint \
        --vpc-endpoint-id vpce-1a2b3c4d \
        --add-route-table-ids rtb-aaa222bb \
        --reset-policy

Output::

    {
        "Return": true
    }

For more information, see `Gateway endpoints <https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html>`__ in the *AWS PrivateLink User Guide*.

**Example 2: To modify an interface endpoint**

The following ``modify-vpc-endpoint`` example modifies interface endpoint ``vpce-0fe5b17a0707d6fa5`` by adding subnet ``subnet-d6fcaa8d`` to the endpoint. ::

    aws ec2 modify-vpc-endpoint \
        --vpc-endpoint-id vpce-0fe5b17a0707d6fa5 \
        --add-subnet-id subnet-d6fcaa8d

Output::

    {
        "Return": true
    }

For more information, see `Access an AWS service using an interface VPC endpoint <https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html>`__ in the *AWS PrivateLink User Guide*.
