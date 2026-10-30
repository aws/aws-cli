**To delete a custom game build**

The following ``delete-build`` example removes a build from your Amazon GameLift account. After the build is deleted, you cannot use it to create new fleets. This operation cannot be undone. ::

    aws gamelift delete-build \
        --build-id build-a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Create a game server build for Amazon GameLift Servers <https://docs.aws.amazon.com/gameliftservers/latest/developerguide/gamelift-build-cli-uploading.html>`__ in the *Amazon GameLift Servers Developer Guide*.
