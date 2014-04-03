**To retrieve history for an alarm**

The following example uses the ``describe-alarm-history`` command to retrieve history for the Amazon
CloudWatch alarm named myalarm::

  aws cloudwatch describe-alarm-history --alarm-name "my estimated charges" --history-item-type
  StateUpdate

Output::

This command returns to the prompt if successful.
