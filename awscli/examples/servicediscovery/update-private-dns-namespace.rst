**Example 1: To update a private DNS namespace using ID**

The following ``update-private-dns-namespace`` example updates the description of a private DNS namespace using namespace ID. ::

    aws servicediscovery update-private-dns-namespace \
        --id ns-abcd1234xmpl5678 \
        --updater-request-id abcd1234-5678-90ab-cdef-xmpl12345678 \
        --namespace Description="The updated namespace description."

Output::

    {
        "OperationId": "abcd1234-5678-90ab-cdef-xmpl12345678"
    }

To confirm that the operation succeeded, you can run ``get-operation``.

For more information, see `AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To update a private DNS namespace using ARN**

The following ``update-private-dns-namespace`` example updates a private DNS namespace using its ARN. ::

    aws servicediscovery update-private-dns-namespace \
        --id arn:aws:servicediscovery:us-west-2:123456789012:namespace/ns-abcd1234xmpl5678 \
        --updater-request-id abcd1234-5678-90ab-cdef-xmpl12345678 \
        --namespace Description="The updated namespace description."

Output::

    {
        "OperationId": "abcd1234-5678-90ab-cdef-xmpl12345678"
    }

For more information, see `AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.
