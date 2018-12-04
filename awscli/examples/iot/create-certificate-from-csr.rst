Create Batches of Certificates from Batches of CSRs
---------------------------------------------------
The following example shows how to create a batch of certificates given a
batch of CSRs. Assuming a set of CSRs are located inside of the
directory ``my-csr-directory``::

    $ ls my-csr-directory/
    csr.pem		csr2.pem


a certificate can be created for each CSR in that directory
using a single command. On Linux and OSX, this command is::

    $ ls my-csr-directory/ | xargs -I {} aws iot create-certificate-from-csr --certificate-signing-request file://my-csr-directory/{}


This command lists all of the CSRs in ``my-csr-directory`` and
pipes each CSR filename to the ``aws iot create-certificate-from-csr`` AWS CLI
command to create a certificate for the corresponding CSR.

The ``aws iot create-certificate-from-csr`` part of the command can also be
ran in parallel to speed up the certificate creation process::

    $ ls my-csr-directory/ | xargs -P 10 -I {} aws iot create-certificate-from-csr --certificate-signing-request file://my-csr-directory/{}


On Windows PowerShell, the command to create certificates for all CSRs
in ``my-csr-directory`` is::

    > ls -Name my-csr-directory | %{aws iot create-certificate-from-csr --certificate-signing-request file://my-csr-directory/$_}


On Windows Command Prompt, the command to create certificates for all CSRs
in ``my-csr-directory`` is::

    > forfiles /p my-csr-directory /c "cmd /c aws iot create-certificate-from-csr --certificate-signing-request file://@path"
