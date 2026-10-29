**To update an IP set**

The following ``update-ip-set`` example updates an IPSet with an IPv4 address and deletes an IPv6 address. Get the value for ``change-token`` by running the ``get-change-token`` command. Because the value for updates includes embedded double-quotes, you must surround the value with single quotes. ::

    aws waf update-ip-set \
        --ip-set-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --change-token 12cs345-67cd-890b-1cd2-c3a4567d89f1 \
        --updates 'Action="INSERT",IPSetDescriptor={Type="IPV4",Value="12.34.56.78/16"},Action="DELETE",IPSetDescriptor={Type="IPV6",Value="1111:0000:0000:0000:0000:0000:0000:0111/128"}' 

Output::

    {
        "ChangeToken": "12cs345-67cd-890b-1cd2-c3a4567d89f1"
    }

Alternatively, you can use a JSON file to specify the input, as shown in the following example. ::

    aws waf-regional update-ip-set \
        --ip-set-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --change-token 12cs345-67cd-890b-1cd2-c3a4567d89f1  \
        --updates file://change.json 

Contents of ``change.json``::

    [
        { 
            "Action": "INSERT",
            "IPSetDescriptor":
            {
                "Type": "IPV4", 
                "Value": "12.34.56.78/16" 
            }
        },
        {
            "Action": "DELETE",
            "IPSetDescriptor":
            {
                "Type": "IPV6",
                "Value": "1111:0000:0000:0000:0000:0000:0000:0111/128"
            } 
        }
    ]

Output::

    {
        "ChangeToken": "12cs345-67cd-890b-1cd2-c3a4567d89f1"
    }

For more information, see `Working with IP match conditions <https://docs.aws.amazon.com/waf/latest/developerguide/classic-web-acl-ip-conditions.html>`__ in the *AWS WAF Developer Guide*.
