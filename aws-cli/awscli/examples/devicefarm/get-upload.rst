**To view an upload**

The following ``get-upload`` example retrieves information about an upload. ::

    aws devicefarm get-upload \
        --arn "arn:aws:devicefarm:us-west-2:123456789012:upload:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"

You can get the upload ARN from the output of ``create-upload``.

Output::

    {
        "upload": {
            "status": "SUCCEEDED",
            "name": "app.apk",
            "created": 1505262773.186,
            "type": "ANDROID_APP",
            "arn": "arn:aws:devicefarm:us-west-2:123456789012:upload:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "metadata": "{\"device_admin\":false,\"activity_name\":\"ccom.example.client.LauncherActivity\",\"version_name\":\"1.0.2.94\",\"screens\":[\"small\",\"normal\",\"large\",\"xlarge\"],\"error_type\":null,\"sdk_version\":\"16\",\"package_name\":\"com.example.client\",\"version_code\":\"20994\",\"native_code\":[\"armeabi-v7a\"],\"target_sdk_version\":\"25\"}"
        }
    }

For more information, see `Creating a test run in Device Farm <https://docs.aws.amazon.com/devicefarm/latest/developerguide/how-to-create-test-run.html>`__ in the *AWS Device Farm Developer Guide*.
