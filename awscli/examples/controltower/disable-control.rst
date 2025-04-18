**To Disable Control Tower Control**

The following ``disable-control`` example disables an AWS Control Tower enabled control::

    aws controltower disable-control \
        --control-identifier arn:aws:controlcatalog:::control/497wrm2xnk1wxlf4obrxxxxxx \
        --target-identifier arn:aws:organizations::123456789012:ou/o-s64ryxxxxx/ou-oqxx-i5wnxxxx

Output::

    {
        "operationIdentifier": "b8f0dxxx-08xx-43xx-a2xx-568e9922xxxx"
    }

For more information, see `AWS Control Tower Controls <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.