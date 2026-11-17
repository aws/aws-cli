**Example 1: To update a service to add an attribute**

The following ``update-service-attributes`` example updates the specified service to add a service attribute with a key ``Port`` and a value ``80``. ::

    aws servicediscovery update-service-attributes \
        --service-id srv-abcd1234xmpl5678 \
        --attributes Port=80

This command produces no output.

For more information, see `AWS Cloud Map services <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-services.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To update a service attributes using ARN**

The following ``update-service-attributes`` example updates a service using its ARN to add a service attribute. Specifying the ARN is necessary for adding attributes to services created in namespaces shared with your account. ::

    aws servicediscovery update-service-attributes \
        --service-id arn:aws:servicediscovery:us-west-2:123456789012:service/srv-abcd1234xmpl5678 \
        --attributes Port=80

This command produces no output.

For more information, see  `AWS Cloud Map services <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-services.html>`__ and `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.
