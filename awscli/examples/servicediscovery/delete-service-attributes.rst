**Example 1: To delete a service attribute**

The following ``delete-service-attributes`` example deletes a service attribute with the key ``Port`` that is associated with the specified service. ::

    aws servicediscovery delete-service-attributes \
        --service-id srv-abcd1234xmpl5678 \
        --attributes Port

This command produces no output.

For more information, see `AWS Cloud Map services <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-services.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To delete a service attribute using ARN**

The following ``delete-service-attributes`` example deletes a service attribute using the service ARN. Specifying the ARN is necessary for deleting attributes associated with services created in namespaces shared with your account. ::

    aws servicediscovery delete-service-attributes \
        --service-id arn:aws:servicediscovery:us-west-2:123456789012:service/srv-abcd1234xmpl5678 \
        --attributes Port

This command produces no output.

For more information, see `AWS Cloud Map services <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-services.html>`__ and `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.
