**To update a Control Tower enabled control**

The following ``update-enabled-control`` example updates an AWS Control Tower enabled control. ::

    aws controltower update-enabled-control \
        --enabled-control-identifier arn:aws:controltower:us-east-1:493301538276:enabledcontrol/JSJN8UL0G2MWGRTZ \
        --parameters '[{"key":"AllowedRegions","value":["us-east-1","us-west-1","us-west-2","us-east-2"]}]'

Output::

    {
        "operationIdentifier": "b8f0dxxx-08xx-43xx-a2xx-568e9922xxxx"
    }

For more information, see `About controls in AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.