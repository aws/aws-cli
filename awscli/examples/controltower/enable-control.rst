**To enable a Control Tower control**

The following ``enable-control`` example enables an AWS Control Tower control. ::

    aws controltower enable-control \
        --control-identifier arn:aws:controlcatalog:::control/497wrm2xnk1wxlf4obrxxxxxx \
        --target-identifier arn:aws:organizations::123456789012:ou/o-s64ryxxxxx/ou-oqxx-i5wnxxxx

Output::

    {
        "arn": "arn:aws:controltower:us-east-1:123456789012:enabledcontrol/18J5KBJ3W3VTIRLV",
        "operationIdentifier": "7691fc5a-de87-4540-8c95-b0aabd56382c"
    }

For more information, see `About controls in AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.