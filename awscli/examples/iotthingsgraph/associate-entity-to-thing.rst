**To associate a thing with a device**

The following ``associate-entity-to-thing`` example associates a thing with a device. The example uses a motion sensor device that is in the public namespace. ::

    aws iotthingsgraph associate-entity-to-thing \
        --thing-name "MotionSensorName" \
        --entity-id "urn:tdm:aws/examples:Device:HCSR501MotionSensor"

This command produces no output.
