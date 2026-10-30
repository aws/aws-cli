**To delete an OTA update**

The following ``delete-ota-update`` example deletes the specified OTA update. ::

    aws iot delete-ota-update \
        --ota-update-id ota12345 \
        --delete-stream \
        --force-delete-aws-job

This command produces no output.

For more information, see `Creating an OTA update with the AWS CLI <https://docs.aws.amazon.com/freertos/latest/userguide/ota-cli-workflow.html>`__ in the *FreeRTOS User Guide*.
