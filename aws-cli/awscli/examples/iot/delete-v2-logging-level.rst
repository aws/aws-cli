**To delete the logging level for a thing group**

The following ``delete-v2-logging-level`` example deletes the logging level for the specified thing group. ::

    aws iot delete-v2-logging-level \
        --target-type THING_GROUP \
        --target-name LightBulbs

This command produces no output.

For more information, see `Configure AWS IoT logging <https://docs.aws.amazon.com/iot/latest/developerguide/configure-logging.html>`__ in the *AWS IoT Developer Guide*.
