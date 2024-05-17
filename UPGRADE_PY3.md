# CLI Python 3 Migration Guide

Python 2.7 was deprecated by the [Python Software Foundation](https://www.python.org/psf-landing/)
back on January 1, 2020 following a multi-year process of phasing it out. Because of this, AWS has
deprecated support for Python 2.7, meaning versions the AWS CLI v1 released after the deprecation
date no longer work with Python 2.7.

-----

**Note**

Since the AWS CLI v2 bundles its own copy of Python, this transition only impacts users of the CLI 
v1. You can upgrade to the AWS CLI v2 to avoid these deprecations in the future.

----
## Timeline

Going forward, customers using the CLI v1 should transition to using Python 3, with Python 3.8 becoming
the minimum by the end of the transition. The deprecation dates for the affected versions of Python are:

|Python version|Deprecation date|
|--------------|----------------|
| Python 2.7|          7/15/2021|
| Python 3.4 and 3.5|   2/1/2021|
| Python 3.6|          5/30/2022|
| Python 3.7|         12/13/2023|

## Impact on the AWS CLI

The AWS Command Line Interface is built using the Python SDK, so it's affected by this transition. 
AWS CLI v2 isn't affected by this transition, since it bundles its own copy of Python 3. However, 
if you still use the AWS CLI v1, you need to decide whether to 
[upgrade to Python 3](#upgrading-to-python-3) or transition to the 
[AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html).

## Upgrading to Python 3

Before starting this process, we highly recommend 
[upgrading to AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html). 
This will avoid the requirement for future upgrades and isolate your CLI usage from conflicts 
with other packages like boto3 and botocore.

### Do I need to upgrade?

First, let’s check if you need to upgrade to Python 3. If you have the AWS CLI installed, 
you can quickly check which version of Python it’s using with this command.
```bash
$ aws --version
aws-cli/1.18.191 Python/2.7.18 Darwin/19.6.0 botocore/1.19.31
```

If the second portion of the version string, starting with **Python/** isn’t Python/3.8.x
or higher, you should review the options below.

### Installing CLI with Python 3

If you’re using the **MSI installer**, you can simply start using these Python 3 based installers
[[32 bit](https://s3.amazonaws.com/aws-cli/AWSCLI32PY3.msi)] 
[[64 bit](https://s3.amazonaws.com/aws-cli/AWSCLI64PY3.msi)].

Otherwise, upgrading Python versions isn’t difficult.

1. To begin, uninstall your existing copy of the AWS CLI. You can find instructions in the 
[CLI v1 installation guide](https://docs.aws.amazon.com/cli/latest/userguide/install-linux.html).
2. Now we’ll install Python 3.8 or later. You can get Python from
[Python.org](https://www.python.org/downloads) or using your local package manager. 
In this example, we’ll use a recent version, Python 3.8.7, to ensure the longest support window. 
3. Next, depending on your installation method, the new Python installation should be available at 
one of these locations. Use these commands to verify:
```bash
    $ python --version
    Python 3.8.7
    
    $ python3 --version
    Python 3.8.7
    
    $ python3.8 --version
    Python 3.8.7
```
5.  Here, we're using the **python** command from above to make sure we're installing with the right 
version. Use whichever alias provided the desired Python version.
```bash
$ python -m pip install awscli
```
Alternatively, if you're using the bundled installer you can use:
```bash
$ python awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws
```
7. If you wish, you may verify that the newly installed copy of the AWS CLI tool, **aws**, is 
using the correct version of Python. The **aws --version** command reports the **aws** tool's 
version number, followed by the version of Python it's running under, then the operating system 
version and the version of botocore. As long as the Python version is at least 3.8,
you're ready to go:
```bash
    $ aws --version
    aws-cli/1.18.191 Python/3.8.7 Darwin/19.6.0 botocore/1.19.31
```

## If you're unable to upgrade to Python 3

It may be possible that you're unable to upgrade to Python 3. Under these circumstances, you 
should be prepared for the deprecation date, in order to not be inconvenienced when the time 
arrives. If you're using a version of the AWS CLI v1 released prior to the deprecation date, 
it will continue to function after end of support. These versions however will no longer be 
receiving security or feature updates. If those are required, you will need to migrate to 
Python 3 to start receiving updates again.

### Upgrade a pip-based install

If you install the AWS CLI using pip, as long as you use pip 10.0 and later, you will 
automatically install the last available version compatible with Python 2.7.

### Windows MSI Installer

If you installed the AWS CLI v1 using the Windows MSI Installer for Python 3 
[[32 bit](https://s3.amazonaws.com/aws-cli/AWSCLI32PY3.msi)] 
[[64 bit](https://s3.amazonaws.com/aws-cli/AWSCLI64PY3.msi)], 
you're not impacted by this transition. These installers stay up-to-date with each release.

If you're still using the AWS CLI v1 as installed using the Windows MSI Installer for Python 2, 
be aware that after the deprecation date, the download links for the latest version of the CLI v1 
Windows MSI Installer will point to the Python 3 MSIs. Previous releases, including those for 
Python 2, will remain available at their version-specific URLs: 
* `https://s3.amazonaws.com/aws-cli/AWSCLI32-{VERSION}.msi`
* `https://s3.amazonaws.com/aws-cli/AWSCLI64-{VERSION}.msi`

### Upgrade with the AWS CLI bundled installer

If you use the AWS CLI bundled installer to install the AWS CLI v1 and cannot upgrade, 
you will need to ensure you’re downloading a Python 2 compatible version. 
All versions released prior to the deprecation date should be compatible. 
You can download a specific installer using the URL 
`https://s3.amazonaws.com/aws-cli/awscli-bundle-{VERSION}.zip`, 
where "`{VERSION}`" is the AWS CLI version you wish to install.

For example, you could choose version 1.18.200 using the following command:

```bash
curl https://s3.amazonaws.com/aws-cli/awscli-bundle-1.18.200.zip -o awscli-bundle.zip
```

Once you've downloaded the bundle, proceed with step 2 of the bundle-based installation 
instructions for your platform:

* [Linux](https://docs.aws.amazon.com/cli/latest/userguide/install-linux.html#install-linux-bundled)
* [macOS](https://docs.aws.amazon.com/cli/latest/userguide/install-macos.html#install-macosos-bundled-sudo)
