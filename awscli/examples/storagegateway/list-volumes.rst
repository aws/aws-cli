**To list the volumes configured for a gateway**

The following ``list-volumes`` command returns a list of volumes configured for the specified gateway.
To specify which gateway to describe, use the Amazon Resource Name (ARN) of the gateway in the command.

This examples specifies the gateway named "ExampleGateway"::

    aws storagegateway list-volumes --gateway-arn "arn:aws:storagegateway:us-east-1:100447751468:gateway/ExampleGateway"

This command outputs a JSON block that a list of volumes that includes the type and ARN for each volume.
