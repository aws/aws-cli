**Example 1: To update a public DNS namespace using ID**

The following ``update-public-dns-namespace`` example updates the description of a public DNS namespace using its ID. ::

    aws servicediscovery update-public-dns-namespace \
        --id ns-abcd1234xmpl5678 \
        --updater-request-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --namespace Description="The updated namespace description."

Output::

    {
        "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

To confirm that the operation succeeded, you can run ``get-operation``.

For more information, see `AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To update a public DNS namespace using ARN**

The following ``update-public-dns-namespace`` example updates a public DNS namespace using its ARN. ::

    aws servicediscovery update-public-dns-namespace \
        --id arn:aws:servicediscovery:us-west-2:123456789012:namespace/ns-abcd1234xmpl5678 \
        --updater-request-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --namespace Description="The updated namespace description."

Output::

    {
        "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.
