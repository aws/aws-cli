**To delete a virtual interface**

The following ``delete-virtual-interface`` example deletes the specified virtual interface. ::

    aws directconnect delete-virtual-interface \
        --virtual-interface-id dxvif-ffhhk74f

Output::

    {
        "virtualInterfaceState": "deleting"
    }

For more information, see `Delete a Direct Connect virtual interface <https://docs.aws.amazon.com/directconnect/latest/UserGuide/deletevif.html>`__ in the *AWS Direct Connect User Guide*.
