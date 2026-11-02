**To confirm the creation of a hosted connection on an interconnect**

The following ``confirm-connection`` example confirms the creation of a hosted connection on an interconnect. ::

    aws directconnect confirm-connection \
        --connection-id dxcon-fg2wi7hy

Output::

    {
        "connectionState": "pending"
    }

For more information, see `Accept a Direct Connect hosted connection <https://docs.aws.amazon.com/directconnect/latest/UserGuide/accept-hosted-connection.html>`__ in the *AWS Direct Connect User Guide*.
