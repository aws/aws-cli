**Example 1: To describe your LOA-CFA for an interconnect (Linux and macOS)**

The following ``describe-interconnect-loa`` example describes your LOA-CFA for interconnect ``dxcon-fh6ayh1d``. The contents of the LOA-CFA are base64-encoded. This command uses the ``--output`` and ``--query`` parameters to control the output and extract the contents of the ``loaContent`` structure. The final part of the command decodes the content using the ``base64`` utility, and sends the output to a PDF file. ::

    aws directconnect describe-interconnect-loa \
        --interconnect-id dxcon-fh6ayh1d \
        --query loa.loaContent \
        --output text | base64 --decode > myLoaCfa.pdf

This command produces no output. The decoded content is written to the file.

For more information, see `Download the Direct Connect LOA-CFA <https://docs.aws.amazon.com/directconnect/latest/UserGuide/download-loa-cfa.html>`__ in the *AWS Direct Connect User Guide*.

**Example 2: To describe your LOA-CFA for an interconnect (Windows)**

The following ``describe-interconnect-loa`` example describes your LOA-CFA for interconnect ``dxcon-fh6ayh1d`` on a Windows computer. The previous example requires the use of the ``base64`` utility to decode the output, but on Windows you can use ``certutil`` instead. The first command uses the ``--output`` and ``--query`` parameters to control the output and extract the contents of the ``loaContent`` structure to a file called ``myLoaCfa.base64``. ::

    aws directconnect describe-interconnect-loa ^
        --interconnect-id dxcon-fh6ayh1d ^
        --query loa.loaContent ^
        --output text > myLoaCfa.base64

This command produces no output. Its output is redirected to ``myLoaCfa.base64``.

The second command uses the ``certutil`` utility to decode the file and send the output to a PDF file. ::

    certutil -decode myLoaCfa.base64 myLoaCfa.pdf

For more information, see `Download the Direct Connect LOA-CFA <https://docs.aws.amazon.com/directconnect/latest/UserGuide/download-loa-cfa.html>`__ in the *AWS Direct Connect User Guide*.

For more information about controlling AWS CLI output, see `Controlling command output in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-output.html>`__ in the *AWS Command Line Interface User Guide*.
