**Example 1: To update a service**

The following ``update-service`` example updates a service to update the ``DnsConfig`` and ``HealthCheckConfig`` settings. ::

    aws servicediscovery update-service \
        --id srv-abcd1234xmpl5678 \
        --service "DnsConfig={DnsRecords=[{Type=A,TTL=60}]},HealthCheckConfig={Type=HTTP,ResourcePath=/,FailureThreshold=2}"

Output::

    {
        "OperationId": "abcd1234-5678-90ab-cdef-xmpl12345678"
    }

To confirm that the operation succeeded, you can run ``get-operation``.

For more information about updating a service, see `Updating an AWS Cloud Map service <https://docs.aws.amazon.com/cloud-map/latest/dg/editing-services.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To update a service using ARN**

The following ``update-service`` example updates a service using its ARN. Specifying an ARN is necessary for services that are created in namespaces shared with your account. ::

    aws servicediscovery update-service \
        --id arn:aws:servicediscovery:us-west-2:123456789012:service/srv-abcd1234xmpl5678 \
        --service "DnsConfig={DnsRecords=[{Type=A,TTL=60}]},HealthCheckConfig={Type=HTTP,ResourcePath=/,FailureThreshold=2}"

Output::

    {
        "OperationId": "abcd1234-5678-90ab-cdef-xmpl12345678"
    }

For more information about updating a service, see `Updating an AWS Cloud Map service <https://docs.aws.amazon.com/cloud-map/latest/dg/editing-services.html>`__ and `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.
