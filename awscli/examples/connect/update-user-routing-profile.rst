**To update a user's routing profile**

The following ``update-user-routing-profile`` example updates the routing profile for the specified Amazon Connect user. ::

    aws connect update-user-routing-profile \
        --routing-profile-id 12345678-1111-3333-2222-4444EXAMPLE \
        --user-id a1b2c3d4-5678-90ab-cdef-EXAMPLE33333 \
        --instance-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 
        
This command produces no output.
    
For more information, see `Configure Agent Settings <https://docs.aws.amazon.com/connect/latest/adminguide/configure-agents.html>`__ in the *Amazon Connect Administrator Guide*.
