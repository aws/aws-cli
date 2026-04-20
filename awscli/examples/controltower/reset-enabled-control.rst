**To reset a Control Tower enabled control**

The following ``reset-enabled-control`` example resets an AWS Control Tower enabled control. ::

    aws controltower reset-enabled-control \
        --enabled-control-identifier arn:aws:controltower:us-east-1:123456789012:enabledcontrol/2H2AWUG4SKG81855

Output::

    {
        "operationIdentifier": "8276XXXX-b4XX-4eXX-96XX-881d2a4XXXXX"
    }

For more information, see `About controls in AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.