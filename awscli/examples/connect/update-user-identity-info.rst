**To update a user's identity information**

The following ``update-user-identity-info`` example updates the identity information for the specified Amazon Connect user. ::

    aws connect update-user-identity-info \
        --identity-info FirstName=Mary,LastName=Major,Email=marym@example.com \
        --user-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --instance-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 

This command produces no output.

For more information, see `Configure Agent Settings <https://docs.aws.amazon.com/connect/latest/adminguide/configure-agents.html>`__ in the *Amazon Connect Administrator Guide*.
