**Example 1: To delete a service**

The following ``delete-service`` example deletes a service. ::

    aws servicediscovery delete-service \
        --id srv-abcd1234xmpl5678

This command produces no output.

For more information, see `Deleting an AWS Cloud Map service <https://docs.aws.amazon.com/cloud-map/latest/dg/deleting-services.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To delete a service using ARN**

The following ``delete-service`` example deletes a service using its ARN. ::

    aws servicediscovery delete-service \
        --id arn:aws:servicediscovery:us-west-2:123456789012:service/srv-abcd1234xmpl5678

This command produces no output.

For more information, see `Deleting an AWS Cloud Map service <https://docs.aws.amazon.com/cloud-map/latest/dg/deleting-services.html>`__ in the *AWS Cloud Map Developer Guide*.
