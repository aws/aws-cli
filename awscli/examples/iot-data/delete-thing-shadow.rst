**To delete a device's shadow document**

The following ``delete-thing-shadow`` example deletes the entire shadow document for the device named ``MyRPi``. ::

    aws iot-data delete-thing-shadow "output.txt" \
        --thing-name MyRPi

This command produces no output. The ``output.txt`` file contains information that confirms the version and timestamp of the shadow document that you deleted. ::

    {"version":2,"timestamp":1560270384}

For more information, see `Using Shadows <https://docs.aws.amazon.com/iot/latest/developerguide/using-device-shadows.html>`__ in the *AWS IoT Developers Guide*.

