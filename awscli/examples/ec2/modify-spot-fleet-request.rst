**To modify a Spot fleet request**

The following ``modify-spot-fleet-request`` example updates the target capacity of the specified Spot fleet request. ::

    aws ec2 modify-spot-fleet-request \
        --target-capacity 20 \
        --spot-fleet-request-id sfr-73fbd2ce-aa30-494c-8788-1cee4EXAMPLE

Output::

    {
        "Return": true
    }

The following ``modify-spot-fleet-request`` example decreases the target capacity of the specified Spot fleet request without terminating any Spot Instances as a result. ::

    aws ec2 modify-spot-fleet-request \
        --target-capacity 10 \
        --excess-capacity-termination-policy NoTermination \
        --spot-fleet-request-id sfr-73fbd2ce-aa30-494c-8788-1cee4EXAMPLE

Output::

    {
        "Return": true
    }

For more information, see `Modify a Spot Fleet request <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/modify-spot-fleet.html>`__ in the *Amazon EC2 User Guide*.
