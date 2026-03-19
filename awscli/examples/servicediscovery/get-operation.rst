**Example 1: To get the result of an operation**

The following ``get-operation`` example gets the result of a namespace creation operation. ::

    aws servicediscovery get-operation \
        --operation-id abcd1234xmpl5678abcd1234xmpl5678-abcd1234

Output::

    {
        "Operation": {
            "Id": "abcd1234xmpl5678abcd1234xmpl5678-abcd1234",
            "Type": "CREATE_NAMESPACE",
            "Status": "SUCCESS",
            "CreateDate": "2025-01-13T13:35:21.874000-06:00",
            "UpdateDate": "2025-01-13T13:36:02.469000-06:00",
            "Targets": {
                "NAMESPACE": "ns-abcd1234xmpl5678"
            }
        }
    }

For more information, see `Creating an AWS Cloud Map namespace to group application services <https://docs.aws.amazon.com/cloud-map/latest/dg/creating-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To get an operation from a specific owner account**

The following ``get-operation`` example gets the result of an operation associated with a specific namespace owner account. This parameter is necessary to get the result of operations associated with namespaces shared with your account. ::

    aws servicediscovery get-operation \
        --operation-id abcd1234xmpl5678abcd1234xmpl5678-abcd1234 \
        --owner-account 123456789111

Output::

    {
        "Operation": {
            "Id": "abcd1234xmpl5678abcd1234xmpl5678-abcd1234",
            "OwnerAccount": "123456789111",
            "Type": "CREATE_NAMESPACE",
            "Status": "SUCCESS",
            "CreateDate": "2025-01-13T13:35:21.874000-06:00",
            "UpdateDate": "2025-01-13T13:36:02.469000-06:00",
            "Targets": {
                "NAMESPACE": "ns-abcd1234xmpl5678"
            }
        }
    }

For more information, see `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.
