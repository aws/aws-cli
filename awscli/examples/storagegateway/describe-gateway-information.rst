**To describe a gateway**

The following ``describe-gateway-information`` command returns metadata about the specified gateway.
To specify which gateway to describe, use the Amazon Resource Name (ARN) of the gateway in the command.
This examples specifies the gateway named "ExampleGateway".

::

    aws storagegateway describe-gateway-information --gateway-arn "arn:aws:storagegateway:us-east-1:111122223333:gateway/ExampleGateway"

This command outputs a JSON block that contains metadata about about the gateway such as its name,
network interfaces, configured time zone, and the state (whether the gateway is running or not).
