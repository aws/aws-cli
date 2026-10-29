**To get the status for AWS Config**

The following ``get-status`` example returns the status of the delivery channel and configuration recorder. ::

    aws configservice get-status

Output::

    Configuration Recorders:

    name: default
    recorder: ON
    last status: SUCCESS

    Delivery Channels:

    name: default
    last stream delivery status: SUCCESS
    last history delivery status: SUCCESS
    last snapshot delivery status: SUCCESS

For more information, see `Setting Up AWS Config with the AWS CLI <https://docs.aws.amazon.com/config/latest/developerguide/gs-cli.html>`__ in the *AWS Config Developer Guide*.
