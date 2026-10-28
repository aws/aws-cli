**Example 1: To describe your LOA-CFA for a connection (Linux and macOS)**

The following ``describe-connection-loa`` example describes your LOA-CFA for connection ``dxcon-fh6ayh1d``. The contents of the LOA-CFA are base64-encoded. This command uses the ``--output`` and ``--query`` parameters to control the output and extract the contents of the ``loaContent`` structure. The final part of the command decodes the content using the ``base64`` utility, and sends the output to a PDF file. ::

    aws directconnect describe-connection-loa --connection-id dxcon-fh6ayh1d --output text --query loa.loaContent|base64 --decode > myLoaCfa.pdf

**Example 2: To describe your LOA-CFA for a connection (Windows)**

The following ``describe-connection-loa`` example describes your LOA-CFA for connection ``dxcon-fh6ayh1d`` on a Windows computer. The previous example requires the use of the ``base64`` utility to decode the output, but on Windows you can use ``certutil`` instead. The first command uses the ``--output`` and ``--query`` parameters to control the output and extract the contents of the ``loaContent`` structure to a file called ``myLoaCfa.base64``. ::

    aws directconnect describe-connection-loa --connection-id dxcon-fh6ayh1d --output text --query loa.loaContent > myLoaCfa.base64

The second command uses the ``certutil`` utility to decode the file and send the output to a PDF file. ::

    certutil -decode myLoaCfa.base64 myLoaCfa.pdf

For more information about controlling AWS CLI output, see `Controlling Command Output from the AWS Command Line Interface <https://docs.aws.amazon.com/cli/latest/userguide/controlling-output.html>`_ in the *AWS Command Line Interface User Guide*.