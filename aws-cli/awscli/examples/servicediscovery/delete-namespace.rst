**Example 1: To delete a namespace**

The following ``delete-namespace`` example deletes a namespace. ::

    aws servicediscovery delete-namespace \
        --id ns-abcd1234xmpl5678

Output::

    {
        "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

To confirm that the operation succeeded, you can run ``get-operation``. For more information, see `get-operation <https://docs.aws.amazon.com/cli/latest/reference/servicediscovery/get-operation.html>`__ .

For more information, see `Deleting an AWS Cloud Map namespace <https://docs.aws.amazon.com/cloud-map/latest/dg/deleting-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To delete a namespace using namespace ARN**

The following ``delete-namespace`` example deletes a namespace using its ARN. ::

    aws servicediscovery delete-namespace \
        --id arn:aws:servicediscovery:us-west-2:123456789012:namespace/ns-abcd1234xmpl5678

Output::

    {
        "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Deleting an AWS Cloud Map namespace <https://docs.aws.amazon.com/cloud-map/latest/dg/deleting-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.
