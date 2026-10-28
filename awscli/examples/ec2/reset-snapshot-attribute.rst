**To reset a snapshot attribute**

The following ``reset-snapshot-attribute`` example resets the create volume permissions for snapshot ``snap-1234567890abcdef0``. This command produces no output. ::

    aws ec2 reset-snapshot-attribute \
        --snapshot-id snap-1234567890abcdef0 \
        --attribute createVolumePermission

