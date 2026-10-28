**To modify a volume attribute**

The following ``modify-volume-attribute`` example sets the ``autoEnableIo`` attribute of the volume with the ID ``vol-1234567890abcdef0`` to ``true``. This command produces no output. ::

    aws ec2 modify-volume-attribute \
        --volume-id vol-1234567890abcdef0 \
        --auto-enable-io
