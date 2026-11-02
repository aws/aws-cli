**To dissociate a thing from a device**

The following ``dissociate-entity-from-thing`` example dissociates a thing from a device. ::

    aws iotthingsgraph dissociate-entity-from-thing \
        --thing-name "MotionSensorName" \
        --entity-type "DEVICE"

This command produces no output.
