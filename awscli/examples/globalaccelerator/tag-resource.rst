**To tag an accelerator**

The following ``tag-resource`` example adds tags Name and Project to an accelerator, along with corresponding values for each. ::

    aws globalaccelerator tag-resource \
        --resource-arn arn:aws:globalaccelerator::123456789012:accelerator/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --tags Key="Name",Value="Example Name" Key="Project",Value="Example Project"

This command produces no output.

For more information, see `Tagging in AWS Global Accelerator <https://docs.aws.amazon.com/global-accelerator/latest/dg/tagging-in-global-accelerator.html>`__ in the *AWS Global Accelerator Developer Guide*.