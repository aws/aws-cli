**To assign customer metadata to an instance**

The following ``put-inventory`` example assigns rack location information to an instance.

Linux version. ::

    aws ssm put-inventory \
        --instance-id "i-016648b75dd622dab" \
        --items '[{"TypeName": "Custom:RackInfo","SchemaVersion": "1.0","CaptureTime": "2019-01-22T10:01:01Z","Content":[{"RackLocation": "Bay B/Row C/Rack D/Shelf E"}]}]'

Windows version. ::

    aws ssm put-inventory ^
        --instance-id "i-016648b75dd622dab" ^
        --items "TypeName=Custom:RackInfo,SchemaVersion=1.0,CaptureTime=2019-01-22T10:01:01Z,Content=[{RackLocation='Bay B/Row C/Rack D/Shelf F'}]"

This command produces no output.

For more information, see `Working with custom inventory <https://docs.aws.amazon.com/systems-manager/latest/userguide/inventory-custom.html>`__ in the *AWS Systems Manager User Guide*.
