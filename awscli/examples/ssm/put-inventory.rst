**To assign customer metadata to an instance**

This example assigns rack location information to an instance. There is no output if the command succeeds.

Command::

  aws ssm put-inventory --instance-id "i-0cb2b964d3e14fd9f" --items '[{"CaptureTime": "2016-08-22T10:01:01Z", "TypeName": "Custom:RackInfo", "Content":[{"RackLocation": "Bay B/Row C/Rack D/Shelf E"}], "SchemaVersion": "1.0"}]'
  