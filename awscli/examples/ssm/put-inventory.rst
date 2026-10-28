**To assign customer metadata to an instance**

The following ``put-inventory`` example assigns rack location information to an instance. This command produces no output.

Linux version. ::

    aws ssm put-inventory --instance-id "i-016648b75dd622dab" --items '[{"TypeName": "Custom:RackInfo","SchemaVersion": "1.0","CaptureTime": "2019-01-22T10:01:01Z","Content":[{"RackLocation": "Bay B/Row C/Rack D/Shelf E"}]}]'

Windows version. ::

    aws ssm put-inventory --instance-id "i-016648b75dd622dab" --items "TypeName=Custom:RackInfo,SchemaVersion=1.0,CaptureTime=2019-01-22T10:01:01Z,Content=[{RackLocation='Bay B/Row C/Rack D/Shelf F'}]"