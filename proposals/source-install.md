# Installing the AWS CLI v2 from source

Proposal         | Metadata
---------------- | -------------
**Author**       | Kyle Knapp
**Status**       | Finalized
**Created**      | 24-August-2021

## Abstract

This document proposes an official mechanism to install the AWS CLI v2 from
source along with an official source distribution artifact.


## Motivation

The AWS CLI v2 is available as pre-built executables for macOS,
glibc-based Linux x86_64, glibc-based Linux aarch64, and Windows (64-bit). The AWS CLI v2 is also
available as a Docker image. Generally, these artifacts provide coverage for
most platforms and environments, but they do not satisfy all use cases:

* The desired platform (e.g, [ARM 32-bit](https://github.com/aws/aws-cli/issues/5426))
  is not supported by any of the pre-built executables.

* The environment lacks system dependencies that are required for the pre-built
  executable. For example, Alpine Linux uses [musl](https://musl.libc.org/),
  but the current executables require glibc. This causes the pre-built
  executables to not work out of the box for
  [Alpine Linux](https://github.com/aws/aws-cli/issues/4685).

* The environment restricts access to resources only needed by the
  pre-built executable. For example, on security hardened systems, it does not
  give permission to shared memory
  [which is needed](https://github.com/aws/aws-cli/issues/5769)
  during the bootloading process of the frozen `aws` executable.

* Users want to be able to install the AWS CLI using the package manager
  standard to their environment (e.g., `brew`, `yum`, `apt`) instead of having
  to download and use a ZIP, PKG,  MSI, etc. The software available through
  these package managers are typically maintained by upstream distribution
  maintainers. When maintainers import software, they  build from source to
  maintain full control over the code and  packages being imported into their
  distribution. Therefore, importing a pre-built executable is generally a
  [non-starter for distro maintainers](https://github.com/aws/aws-cli/issues/4842).

* Users may want to patch AWS CLI v2 functionality, but in order to use the
  patched functionality, it requires building and installing the AWS CLI v2 from
  source. This is especially important for community members that want to test
  changes they've made to the source prior to proposing/contributing the change in
  the upstream GitHub repository.

Full support for installing the AWS CLI v2 from source will unblock these use
cases because users will be able to build and install the AWS CLI v2 for their
particular environment.


### Goals

The approach for installing the AWS CLI v2 from source should satisfy the
following goals:

1. The source installation process maximizes the number of environments the
   AWS CLI v2 can be installed on.

2. The source installation process is straightforward and intuitive. It minimizes
   the number of cycles required to figure out how to install the AWS CLI from
   source.

3. The source installation process is language agnostic. While the AWS CLI v2
   requires Python, users should not require experience in Python and Python
   tooling to build from source. Furthermore, if the AWS CLI was to be
   rewritten in a different programming language, users installing
   from source should not have to learn a new set of build and install steps
   and should be able to stay largely unaware of the change other
   than possibly needing to install a new dependency.


### Non-goals

While this proposal helps distribution maintainers make the
AWS CLI v2 available through standard package managers, it does not address
adding official support for installing the AWS CLI v2 through them.
It is focused on providing a mechanism for users that want or need
to install the AWS CLI v2 from source.


## Specification

This section defines:

* [The interface for installing from source](#source-buildinstall-interface)
* [The build and install mechanics when installing from source](#buildinstall-mechanics)
* [The details of a hosted source distribution artifact](#hosted-source-distribution)
* [Provisional support for packaging AWS CLI v2 according to PEP517](#provisional-support-for-pep-517)

### Source build/install interface

The AWS CLI v2 leverages [GNU Autotools](https://www.gnu.org/software/automake/faq/autotools-faq.html)
to install from source. In the simplest case, the AWS CLI v2 can be installed
from source by running the following commands from the root of the repository:
```bash
./configure
make
make install
```
These commands are specific to Autotools where:

* `./configure` -  Checks the system for all required dependencies and
  generates a `Makefile` for building and installing the AWS CLI v2 based on
  detected and explicitly specified configurations. See the
  [Configuration section](#configuration) for the available configuration
  options.

* `make` - Builds the AWS CLI v2. For details on the build mechanics,
   see the [Build/install mechanics section](#buildinstall-mechanics).

* `make install` - Installs the built AWS CLI v2 to the configured location
   on the system. For details on the install mechanics, see the
   [Build/install mechanics section](#buildinstall-mechanics).

After the above commands complete, the AWS CLI v2 is installed at the default
location of `/usr/local/lib/aws-cli` and creates symlinks for the `aws` and
`aws_completer` executables in the `/usr/local/bin` directory. These
locations  are configurable through Autotools. See the
[Install location configuration section](#install-location) for more
information.

#### Requirements

These are the requirements to build the AWS CLI v2 from source:

* An environment that can run Autotools generated files (e.g.,
  `configure`, `Makefile`). These files are widely portable across POSIX
  platforms, and for systems that do not come with POSIX-compliant shells like
  Windows, there is additional software available (e.g., MSYS2) that allow users
  to run Autotools generated files. For more information, see the
  [Appendix on Windows usage](#windows).

* Python 3.8+ interpreter. The minimum Python version required will increase
  over time and follow the same timelines as the [official Python support policy
  for AWS SDKs and Tools](https://aws.amazon.com/blogs/developer/python-support-policy-updates-for-aws-sdks-and-tools/)
  where an interpreter will only continue to be supported 6 months after its end-of-support date. For example,
  Python 3.8 reaches end of support in October 2024, and thus in April 2025, Python 3.8 will no longer be supported
  for installing the AWS CLI v2 from source and instead require a Python 3.9+ interpreter.

* (Optional) All build and runtime Python library dependencies
  of the AWS CLI v2. This can be opted out of through configuration that
  downloads and uses the dependencies as part of the build step.
  See the [Downloading dependencies configuration section](#downloading-dependencies)
  for more information.

#### Configuration

Configuration for the build and install of the AWS CLI v2 is specified using
the `configure` script. For the documentation of all configuration options, run
the `configure` script with the `--help` option:
```bash
./configure --help
```
This is a sample output from the help page:
```
✗ ./configure -h
Configures builds and installs of the AWS CLI

Usage: ./configure [OPTION]... [ENV_VAR=VALUE]...

Help options:
  -h, --help              Display help
  -V, --version           Display version

Installation directories:
  --prefix=PREFIX         Set installation prefix. By default, this value is
                          "/usr/local".
  --libdir=LIBDIR         Set parent directory for AWS CLI installation. The
                          full path to the AWS CLI installation is "LIBDIR/aws-cli".
                          The default value for "LIBDIR" is "PREFIX/lib"
                          (i.e., "/usr/local/lib" if "--prefix" is not set).
  --bindir=BINDIR         Set install directory for AWS CLI executables. The
                          default value for "BINDIR" is "PREFIX/bin"
                          (i.e., "/usr/local/bin" if "--prefix" is not set).
Optional arguments:
  --with-install-type=system-sandbox|portable-exe
                          Specify type of AWS CLI installation. Options are:
                          "portable-exe", "system-sandbox" (default is
                          "system-sandbox")
  --with-download-deps    Download all dependencies and use those when
                          building the AWS CLI. If not specified, the
                          dependencies (including all python packages) must be
                          installed on your system
Some influential environment variables:
  PYTHON      the Python interpreter

```
The sections below describes the most pertinent options.


##### Install location

Source installation of the AWS CLI v2 uses two configurable directories to
install the AWS CLI v2:

* `libdir` - Parent directory where the AWS CLI v2 will be installed. The
  path to the AWS CLI v2 installation is `<libdir-value>/aws-cli`. The default
  `libdir` value is `/usr/local/lib` making the default installation directory
  `/usr/local/lib/aws-cli`

* `bindir` - Directory where the AWS CLI v2 executables
  (e.g., `aws`, `aws_completer`) will be installed. The default location is
  `/usr/local/bin`.

The following `configure` options are offered to control the directories used:

* `--prefix` - Sets the directory prefix to use for the installation. The
  default value is `/usr/local`.

* `--libdir` - Sets the `libdir` to use for installing the AWS CLI v2. The
  default value is `<prefix-value>/lib` (i.e., `/usr/local/lib/` if
  `--prefix` is not specified).

* `--bindir` - Sets the `bindir` to use for installing the AWS CLI v2
  executables. The default value is `<prefix-value>/bin`
  (i.e., `/usr/local/bin/` if both `--prefix` is not specified).

For example, users can use the `--prefix` option to do a user install of the
AWS CLI:
```
./configure --prefix=$HOME/.local
```
This command results in the AWS CLI v2 being installed at
`$HOME/.local/lib/aws-cli` and its executables located in `$HOME/.local/bin`

Users can also use more granular options such as the `--libdir` option to
install the AWS CLI v2 as an add-on application in the `/opt` directory:
```
./configure --libdir=/opt
```
This command results in the AWS CLI v2 being installed at `/opt/aws-cli` and
the executables being installed at their default location of `/usr/local/bin`.

In addition, the `make install` rule supports:

* [`DESTDIR`](https://www.gnu.org/software/make/manual/html_node/DESTDIR.html#DESTDIR) variable - The path
  to prepend to the configured installation prefix path when installing the AWS CLI. By default, no value is set
  for this variable.

The `DESTDIR` variable allows users to install the AWS CLI to an alternative location to the finalized installation
location. For example, users can use the variable to install to a temporary location:
```
./configure --prefix=/usr/local
make
make DESTDIR=/tmp/stage install
```
These commands result in the AWS CLI v2 being installed at `/tmp/stage/usr/local/lib/aws-cli` and its
executables located in `/tmp/stage/usr/local/bin`.


##### Python interpreter

Through the [`AM_PATH_PYTHON`](https://www.gnu.org/software/automake/manual/html_node/Python.html)
Autoconf macro, the `./configure` script automatically selects a Python
interpreter installed on the system that is of version 3.8 or higher to use
in building and running the AWS CLI v2. The Python interpreter to use can
be explicitly set using the `PYTHON` environment variable when running the
`configure` script:
```bash
PYTHON=/path/to/python ./configure
```


##### Downloading dependencies

By default, it is required that all build and runtime dependencies of
the AWS CLI v2 are installed on the system. This includes any dependencies
that are Python libraries. All dependencies are checked when the `configure`
script is run, and if the system is missing any Python dependencies, the
`configure` script errors out. For example:
```
$ ./configure
checking for a Python interpreter with version >= 3.8... python3.8
checking for python3.8... /usr/local/bin/python3.8
checking for python3.8 version... 3.8
checking for python3.8 platform... darwin
checking for python3.8 script directory... ${prefix}/lib/python3.8/site-packages
checking for python3.8 extension module directory... ${exec_prefix}/lib/python3.8/site-packages
checking for --with-install-type... portable-exe
checking for --with-download-deps... Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/runpy.py", line 194, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/runpy.py", line 87, in _run_code
    exec(code, run_globals)
  File "./scripts/build/__main__.py", line 71, in <module>
    main()
  File "./scripts/build/__main__.py", line 63, in main
    validate(parsed_args.artifact)
  File "./scripts/build/__main__.py", line 28, in validate
    validate_env(artifact)
  File "./scripts/build/validate_env.py", line 27, in validate_env
    raise UnmetDependenciesException(unmet_deps)
validate_env.UnmetDependenciesException: Environment requires following Python dependencies:

awscrt (required: awscrt==0.11.13) (version installed: None)

configure: error: "Python dependencies not met"
```

Users can specify the `--with-download-deps` option to avoid having to install
all required Python dependencies themselves:
```
./configure --with-download-deps
```
In specifying this flag, the build process:

* Skips the configuration check to make sure all Python library dependencies
  are installed on the system.

* During the `make` step, downloads **all** required dependencies and uses
  **only** the downloaded dependencies to build the AWS CLI v2.

Currently, this flag only downloads Python packages, but may be expanded in
the future for non-Python dependencies.


##### Install type

The source install process supports two different installation types:

* `system-sandbox` - (Default) Creates an isolated Python virtual environment,
  installs the AWS CLI v2 into the virtual environment, and symlinks to the
  `aws` and `aws_completer` executable in the virtual environment.

* `portable-exe` - Freezes the AWS CLI v2 into a standalone executable that
  can be distributed to environments of similar architectures. This is the
  same process used to generate the official pre-built executables of the AWS
  CLI v2.

The primary difference between the two installation types is that the
`portable-exe` freezes in a copy of the Python interpreter chosen in the
`configure` step to use for the runtime of the AWS CLI v2. This allows it to
be moved to other machines that may not have a Python interpreter.
While for the `system-sandbox`, the install of the AWS CLI v2 depends directly
on the selected Python interpreter for its runtime.

By default, the installation type is `system-sandbox`. To configure the
installation type, use the `--with-install-type` option and specify a value
of `portable-exe` or `system-sandbox`. For example:
```bash
./configure --with-install-type=portable-exe
```

For more information about the build details for these two installation types,
see the [Build/install mechanics section](#buildinstall-mechanics).
For more information on reasons to use one installation type over the over, see the
[Rationale section](#q-why-are-there-two-different-installation-types).


#### Supported make targets and usage

Once the `Makefile` is generated from the `configure` script, users can run a
variety of targets to manage the building and installing the AWS CLI v2 via
the command pattern:
```
make <target>
```
The supported targets are:

* `all` - Builds the AWS CLI v2 based on configuration. This is synonymous
  to running `make` without a `<target>` argument.
* `install` - Installs the built AWS CLI v2 onto the system.
* `clean` - Removes all build artifacts from the `all` rule.
* `uninstall` - Uninstalls the AWS CLI v2 from the system.

Any other targets found in the `Makefile` are considered implementation details
and should not be used.

Below sections show how to use these targets to manage the installation of the
AWS CLI v2 beyond initially installing it.

##### Upgrade the AWS CLI v2

To upgrade the AWS CLI v2, users first re-download the latest source code
for the AWS CLI v2 and rerun the Autotools steps from the initial install
process:
```
./configure
make
make install
```
These steps completely remove any preexisting installation and replaces the
installation with the newly built version of the AWS CLI v2, assuming the same
installation configurations were used.


##### Uninstall AWS CLI v2

To remove the AWS CLI v2, users run:
```
make uninstall
```
Assuming the same `./configure` options were used in generating the
Makefile that installed the AWS CLI v2, this deletes both the installation of
the AWS CLI v2 and its symlinks in the `bindir` to its executables.

#### Backwards compatibility

In regard to backwards compatibility, these are the aspects of installing
from source that are backwards compatible:

* Autotools usage patterns for installing, upgrading, and uninstalling the
  AWS CLI v2. For example, the commands to install/upgrade the
  AWS CLI v2 will always be: `./configure`, `make`, and `make install`, and
  the command to uninstall the AWS CLI v2 will always be `make uninstall`.

* Documented `configure` options.

* Documented `make` targets.

* Usage of `libdir` and `bindir` in the installation process. All bits
  related to the  AWS CLI v2 installation will be located in the `libdir` and
  all publicly accessible executables (e.g., `aws` and `aws_completer`) will
  be located in the `bindir`.

These are the aspects that have **no** backwards compatibility guarantees:

* Dependencies. The AWS CLI v2 will add new dependencies in the future. This
  means users must install any new dependencies to their system in order to
  install the AWS CLI v2 from source. This includes anything from:

  * Increasing minimum required Python version
  * Pulling in a new Python library dependency
  * Requiring a new system dependency

  Furthermore, the `--with-download-deps` option does not guarantee that all
  possible new dependencies in the future will be accounted for by the flag. For
  example, a new programming language may  be required in the future
  (e.g., Go, Rust) and the `--with-download-deps` option would likely not account
  for that new requirement.

In general, users cannot make the assumption that when upgrading versions of
the AWS CLI v2, using the same environment and same build steps will
always result in a successful install. If building from source in a CI/CD
setting, users should pin to a specific version of the AWS CLI v2 code base
using repository tags or a versioned source distribution
(see [Hosted source distribution section](#hosted-source-distribution)) to
ensure automation does not break.

### Build/install mechanics

Below details the steps taken in building and installing the AWS CLI v2 from
source. Note the build directory in these steps refers to a directory that is
created in the same directory as the `Makefile` and hosts artifacts related to
the build.

#### Build steps

When running `make`, the following steps are run:

1. Use the [`venv`](https://docs.python.org/3/library/venv.html) module
   built into the Python standard library to create a new virtual environment
   in the build directory. The virtual environment is also bootstraped with
   a [version of pip that is vendored in the Python standard library](https://docs.python.org/3/library/ensurepip.html).

2. If `--with-download-deps` was specified in the `configure` command, it
   pip installs all Python packages required to build and run the AWS CLI v2.
   This includes: `wheel`, `setuptools`, all CLI runtime dependencies, and
   `pyinstaller` (if building the `portable-exe`). These requirements are all
   specified in lock files generated from [`pip-compile`](https://github.com/jazzband/pip-tools).

   If `--with-download-deps` was not specified in the `configure` command, it
   copies all Python libraries from the Python interpreter's site package plus
   any scripts (e.g., `pyinstaller`) into the virtual environment being used
   for the build.

3. Run `pip install` directly on the AWS CLI v2 codebase to do an offline,
   in-tree build and install of the AWS CLI v2 into the build virtual
   environment. This is done by including the follow pip flags:
   * [`--no-build-isolation`](https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-no-build-isolation)
   * [`--no-cache-dir`](https://pip.pypa.io/en/stable/cli/pip_install/#caching)
   * [`--no-index`](https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-no-index)

4. If the `--install-type` was set to `portable-exe` in the `configure`
   command, run [`pyinstaller`](https://www.pyinstaller.org/) to build a
   standalone executable.


#### Install steps

When running `make install`, the following steps are run:

1. Move the built virtual environment (if the install type is `system-sandbox`)
   or standalone executable (if the install type is a `portable-exe`) to the
   configured install directory (i.e., `<libdir>/awscli`).

2. Create symlinks for both the `aws` and `aws_completer` in the configured
   bin directory (i.e., at `<bindir>/aws` and `<bindir>/aws_completer`).


### Provisional support for PEP 517

[PEP 517](https://www.python.org/dev/peps/pep-0517/) specifies a build-system
independent format for building Python packages. The AWS CLI v2 code base
is PEP 517 compliant in that a PEP 517 compliant build tool can build sdists
and wheels of the AWS CLI v2, which in turn can be used to install the
AWS CLI v2 onto a system. For example, users can build a wheel and install it
through pip:
```
pip wheel . --wheel-dir dist/
pip install dist/awscli-2.2.1-py3-none-any.whl
```

#### Meaning of "provisional support"

Provisional support means that PEP 517 compliance is maintained as a best
effort, and there is no guarantee that compliance will be maintained in the
future. Users should only directly rely on this functionality as a last resort
because its support is contingent on the implementation detail that the AWS
CLI is written in Python.


#### Required code base changes for PEP 517 support

To make the AWS CLI v2 codebase compliant, it requires the following changes:

* Introduce a `pyproject.toml` file (see [PEP 518](https://www.python.org/dev/peps/pep-0518/))
  and in-tree build backend that builds the autocomplete index when building
  both the sdist and wheel
  (see [PEP 517](https://www.python.org/dev/peps/pep-0517/#in-tree-build-backends)).

* Port all information from the `setup.py` and `setup.cfg` to `pyproject.toml
  that can be programmatically parsed for runtime dependencies.

* Pull in and maintain the unreleased `botocore` `v2` branch along with
  `s3transfer` into the AWS CLI v2 codebase.


### Hosted source distribution

Users can install from source by either checking out the git repository or
by downloading a hosted source distribution of the AWS CLI v2.

The source distribution is a Python sdist generated from a PEP 517 compliant
build tool.

The source distribution of the latest version of the AWS CLI v2 is hosted at:
```
https://awscli.amazonaws.com/awscli.tar.gz
```

The source distribution of any particular version of the AWS CLI v2 is hosted
at:
```
https://awscli.amazonaws.com/awscli-<version>.tar.gz
```
where `<version>` is the literal version of the AWS CLI. For example, if a
user wants version `2.3.0`, they should download the source distribution at:
```
https://awscli.amazonaws.com/awscli-2.3.0.tar.gz
```

In addition, users can download detached PGP signatures for each hosted source
distribution by appending `.sig` to the artifact name. For example the
detached signature for the latest source distribution is hosted at:
```
https://awscli.amazonaws.com/awscli.tar.gz.sig
```

#### Sample usage

Below shows how a user can download and install version `2.3.0` of the AWS
CLI v2 from source using the hosted source distribution:

```bash
curl -O https://awscli.amazonaws.com/awscli-2.3.0.tar.gz
curl -O https://awscli.amazonaws.com/awscli-2.3.0.tar.gz.sig
gpg --verify awscli-2.3.0.tar.gz.sig awscli-2.3.0.tar.gz  # Assuming public AWS CLI key is imported
tar -xf awscli-2.3.0.tar.gz
cd awscli-2.3.0
./configure
make
make install
```

## Rationale/FAQ

#### Q. What are the reasons for choosing Autotools for installing from source?

Autotools was chosen because it met all of [the goals in the motivation section](#goals).
Specifically:

* It specializes on portability and requires no additional dependencies for
  POSIX environments. This should help maximize the number of
  environments the AWS CLI v2 can be installed on. For systems that do not
  have a POSIX-compatible shell (e.g., Windows), there is software available
  to install to help run the scripts (e.g., MSYS2).

* Autotools is one of the most common build systems. This improves familiarity
  for any users looking to install the AWS CLI v2 from source as Autotools
  enabled projects follow the same `configure`, `make`, `make install` command
  flow and share similar configuration flags.

* Autotools is language agnostic. It shields users from having to understand
  Python build tool usage and details and provides stability if we needed to
  change the underlying programming language and corresponding build tools.


#### Q. What alternatives to Autotools were considered?

These were some of the alternative options considered:

##### Cmake

Use [CMake](https://cmake.org/) as the entry point to building and installing
the AWS CLI v2 from source. See [Appendix B](#b-exploration-of-cmake) for
notes on what this interface would look like.

**Pros**

* It is language agnostic (e.g., can abstract over the underlying
  programming language).

* It is a commonly used build tool.

* It supports a wide range of build systems. Unlike Autotools that can only
  generate GNU Makefiles, CMake can target GNU Makefiles as well as common
  Windows build systems such as NMake and Visual Studio.

* The CMake CLI has built-in commands that allows you to build and install the
  project (e.g., `cmake --build` and `cmake --install`) without having to
  directly use the underlying build system (e.g., `make`). Therefore, you could
  use the exact same build and install commands on Linux as in on Windows
  (without the use of MSYS2).

**Cons**

* It requires that a user has CMake installed on their system. Unlike `make`
  which is likely to be pre-installed on a user's system, `cmake` is likely
  not installed unless the user is already building projects that use `cmake`.
  Furthermore, for Windows, users would still need to install
  Microsoft Visual Studio in order to access build systems that `cmake` would
  target (e.g., `nmake`).

* It introduces a new tool that users will have to know how to use in order to
  build and install the AWS CLI. While we can provide quick getting started
  instructions, there is still the possibility that users will have to learn
  about CMake concepts such as cache variables and build system generators.
  With Autotools, it is scoped to just running a single `configure` shell
  script followed by `make` commands. From the end user's perspective, there
  is no additional concepts/knowledge needed past that single usage pattern.

* If we want to take advantage of new features in CMake, we will have to force
  users to upgrade to new versions of CMake. This is different from Autotools
  where the authors generate the `configure` script so only the authors need
  to upgrade their Autotools utilities to access new features.

**Verdict**

In general, Autotools and CMake are similar in terms of functionality and
usage patterns. Arguably, CMake offers more functionality such as offering
unified CLI commands to build/install projects and being able to target more
than just GNU Makefiles for build systems. However, with respect
to building/installing the AWS CLI from source, these tools are just providing
thin, familiar wrappers over Python-specific build/install logic; none of the
tools' core functionality around building C/C++ libraries is actually
leveraged. For the purpose of being a thin, familiar interface, Autotools is
advantageous over CMake because:

* Minimal dependencies required to use the build/install interface.

* The end user interface is more minimal as it is scoped to running a single
  `configure` script followed by `make` commands. Users do not have to
  potentially learn the usage and concepts for a new tool (e.g., `cmake`).

In addition, one important note is that the decision between Autotools and
CMake is **not** a one-way door. It is possible for a project to allow users to
build and install it using either Autotools or CMake. So, CMake support can
always be added in the future if needed.

##### Custom build/install script

Building and installing would be exposed through a custom shell script or
Makefile.

**Pros**

* It is language agnostic (e.g., can abstract over the underlying
  programming language).

* Can have greater control over build and install interface instead of trying
  to fit the interface into the patterns of an established build tool.

**Cons:**

* Does not bring the same potential familiarity as an Autotools/CMake
  project for users new to the project. Users will have to learn a new
  usage pattern.

* Anything custom-built would not be able to match the maintainability and
  portability of a more mature build system (e.g., Autotools and CMake)

* Easier to deviate from conventions established by other build systems,
  which could make it more difficult to understand how to customize the
  build and install of the AWS CLI.

**Verdict:**

While this option gives similar benefits to Autotools and CMake, it still does
not match up to these options when compared to portability and immediate
familiarity users gained from using Autotools or CMake.

##### Only expose PEP 517 support

This would entail having users directly rely on PEP 517 compliant Python
tools to build and then install the AWS CLI v2.

**Pros**

* It reduces complexity of the project (e.g., we would not have to add
  another layer of abstraction over the Python build logic)

* It introduces no new dependencies. Python is already required to
  build the AWS CLI and it comes with `pip` which is PEP 517 compliant.
  Also, the Python build tools generally have cross-platform support.

**Cons:**

* Requires users to be familiar with Python build and install tooling and
  be familiar how to use them safely (e.g., not install the AWS CLI into
  the global site packages).

* If we were to change programming languages or add new build steps, it
  will require users to rewrite any build logic.

**Verdict**

This not a viable option as it only really meets one (i.e., the first goal) of
the three goals from the motivation section.


#### Q. Why are there two different installation types?

By having the two different installations types, we're able to provide
more flexibility in how to build and install the AWS CLI v2.

The `system-sandbox` provides a lightweight install mechanism to get the
AWS CLI  v2 installed on a system, while following best Python practices by
sandboxing the installation in a virtual environment. This installation is
intended for users that want to install the CLI from source in the
most frictionless way possible and don't necessary want/care that the
installation is coupled to their installation of Python.

The `portable-exe` allows users to build the same pre-built artifact
that is used in the other official pre-built artifacts (e.g., MSI, PKG,
Linux pre-built ZIP). These types of builds are useful because:

* Users can ensure their installation of AWS CLI v2 is not coupled to their
  system installation of Python.

* Users can distribute their build to other similar systems that may not have
  Python installed.

In general, a user may want to use their own version of the pre-built artifact
instead of one of the official artifacts because:

* They want to customize the build (e.g., hand select what dependencies are
  bundled into the executable).

* They have compliance/security reasons to not rely on executables built
  by third-parties and want to be able to build it themselves.


#### Q. Why is `system-sandbox` the default installation type?

It is the easier, more straightforward way out of the two options to install
the AWS CLI v2. Ideally, when users come to install the AWS CLI v2 from
source, they should be able to run `./configure`, `make`, `make install` in
a minimal amount of cycles and get a working version of the AWS CLI v2 quickly.

With the `portable-exe` install, it utilizes a library called
[PyInstaller](https://www.pyinstaller.org/) to freeze the AWS CLI v2 and
Python interpreter into an executable. While generally users should be able
to install and use PyInstaller to build the AWS CLI v2 with minimal to no
friction, it can be tedious to figure out how to fix issues when the
PyInstaller install/build does not work whether:

* There is not a pre-compiled PyInstaller bootloader available compatible for
  their environment and have to
  [build the bootloader themselves](https://pyinstaller.readthedocs.io/en/stable/bootloader-building.html).

* The Python interpreter may need to be recompiled to enable it as a shared
  library (e.g., compile with `--enable-shared` on Linux or
  `--enable-framework` for Mac).

In general, the benefit of having the installation not requiring a system
Python is not worth the potential problems users will have to work through
when building the exe when:

* The source install already requires Python to be on the system to build the
  AWS CLI v2.

* One of the main reasons users will be building from source is because there
  is not an official pre-built artifact available for their environment.
  However, these types of environments will likely be the ones where
  users will have to build the PyInstaller bootloader themselves or not be even
  [fully tested](https://github.com/pyinstaller/pyinstaller#untested-platforms),
  and be more prone to running into the issues.


#### Q. Why have `--with-download-deps` flag?

It makes it simpler for users to build the AWS CLI from source, especially
those who are not familiar with the Python ecosystem. Without this flag,
users would have to learn how to install the appropriate Python libraries and
may do so in a way that can be detrimental to their environment setup such as
install packages into their global site packages directory, which can break
other system tools.


#### Q. Why is there provisional support for PEP 517?

By supporting PEP 517, it helps achieve the goal of maximizing the number
of environments that are able to install the AWS CLI v2 by offering a path
forward to build the AWS CLI v2 as a standard-compliant wheel and sdist.

In general, assuming there is a Python interpreter available, wheels and sdist
are the most minimal artifact required to install a Python package onto a
system. Thus, given the AWS CLI v2 is currently a pure Python package and
requires a Python interpreter for source installs, wheel and sdist support
provide a sharp, no-frills escape hatch for installing the AWS CLI v2 whether:

* The environment is a non-POSIX compliant system, and the user does not want
  or is unable to use additional software (e.g., MSYS2) to be able to run
  the Autotools workflow in order to install the AWS CLI v2.

* The user actually wants the AWS CLI v2 installed directly as part of
  the global or user site-packages directory, which would help minimize the
  number of copies of third-party Python packages managed on the system.


However, it is only supported at a provisional capacity because the fact that
the AWS CLI runs on Python is still considered an implementation detail. This
means there is no guarantee that there will not be a change to the AWS CLI
in the future that will force a break in compliance to PEP 517 (e.g., rewriting
the code base to be primarily a Rust or Go-based project) and not be
installable as a wheel/sdist.


#### Q: Why is a custom in-tree build backend being introduced?

Builds of the AWS CLI v2 include a SQLite index for performing faster
auto-completions. This index is a large, ever-increasing in size
(currently at 9 MB) binary file that generally must be regenerated for every
release (which is generally happens daily). Committing this index as part of
every release to the repository would make the size of the repository bloated
and eventually unmanageable over time.

Therefore, the custom in-tree backend allows for the auto-completion index
to be generated and injected as part of building the wheel and sdist. This
allows the AWS CLI v2 be installable from a wheel or sdist without needing to
run any additional steps/scripts nor committing the index to the repository.


#### Q: Why are copies of botocore and s3transfer being maintained in the AWS CLI source?

The AWS CLI v2 currently relies on an unreleased version of botocore that
contains all the breaking changes that needed to happen in botocore in
order to make the desired breaking changes in the AWS CLI. Prior to this
proposal, building of the AWS CLI v2 required checking out and installing
botocore at the appropriate commit in order to install the AWS CLI v2 from
source.

This unreleased version of botocore is being maintained as part of the AWS CLI
v2 codebase for the following reasons:

* It simplifies the building and installing of the AWS CLI v2 as it removes
  the need to download, checkout, and install a specific commit of the
  botocore source in order to install the AWS CLI v2.

* For users that leverage provisional support for PEP 517 to install the
  AWS CLI v2, they do not need to be concerned about the unreleased backwards
  incompatible version of botocore breaking their installation of other Python
  packages that rely on an officially released version of botocore.

* The AWS CLI team maintains the unreleased botocore branch as a
  fork of botocore specifically for the AWS CLI v2, and this is already a
  significant amount of work. From a maintenance perspective, there is little
  difference in effort between maintaining the logic in a branch in the
  botocore repository or as part of the AWS CLI codebase.

* There is no timetable for releasing these changes in an official
  major version bump of botocore. Pulling in the botocore fork into the AWS
  CLI v2 codebase allows the AWS CLI team to make larger changes to the
  fork while minimizing the potential unintended directional impact on a
  future official major version bump of botocore. It is also worth noting
  that in the future, the team may also be able to stop maintaining its fork
  of botocore in favor of an officially released major version of botocore.


The reason s3transfer is being maintained as part of the AWS CLI v2
codebase because it has a direct dependency on botocore. This is specifically
problematic because:

* If s3transfer was not pulled in, it would automatically pull in the official
  version of botocore, which would unnecessarily bloat the size of the
  dependency closure.

* It ensures that any changes that are made to the AWS CLI v2 maintained
  version of botocore is compatible with s3transfer interfaces.


However, in the future if s3transfer removes botocore as a direct dependency,
the AWS CLI v2 would no longer need to maintain a copy of s3transfer in its
codebase.


## Future considerations

### Adding more make targets

In the future, we may want to add support for more GNU
[standard make targets](https://www.gnu.org/prep/standards/html_node/Standard-Targets.html)
for better managing source installs such as:

* `dist` - Generates a source distribution that could be distributed similar
  to the official hosted source distributions.

* `check` - Runs smoke tests on the built AWS CLI v2 to make sure the
  AWS CLI v2 is working correctly before actually installing it to the system.

* `html`/`install-html` - Generates the HTML references and installs them
  to the configured location on the system.

### Accounting for more dependencies

Currently, the `--with-download-deps` flag only downloads Python packages that
are required to run the AWS CLI. However, in the future, this could include
some optional dependencies used in running the CLI. For example:

* Pager (e.g., `less`) if not available on the system for redirecting command
  output

* Any standalone executable plugins required for customized commands
  such as the [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)
  to use the `ssm start-session` command.

These could be either exposed via:

* Including them as part of default value when `--with-download-deps` is
  specified.

* Adding more opt-in values options to the `--with-download-deps` flag
  (e.g., `--with-download-deps=pager`).

* Adding completely separate flags for downloading these optional dependencies
  that is completely separate from `-with-download-deps`
  (e.g., `--with-download-pager`, `--with-download-plugins`).

## Appendix

### A. Examples of source installs on various environments

#### Windows

In order to install the AWS CLI v2 from source on Windows, additional software
is required because it does not come with a POSIX-compliant shell out of the
box. One option to install the AWS CLI from source is to use
[MSYS2](https://www.msys2.org/). It provides a collection of tools and
libraries to help build and install Windows software, especially
for POSIX-based scripting (e.g., Autotools).

To get started with MSYS2, follow these
[install and usage instructions](https://www.msys2.org/). In a CI setting,
MSYS2 can be installed and used in an [automated fashion](https://www.msys2.org/docs/ci/).
Below is a sample of the steps that can be automated if trying to build and
install the AWS CLI v2 from PowerShell using MSYS2:
```powershell
> $env:CHERE_INVOKING = 'yes'  # Preserve the current working directory
> C:\msys64\usr\bin\bash -lc "PYTHON='C:\path\to\python.exe' ./configure --prefix='C:\Program Files\AWSCLI' --with-download-deps"
> C:\msys64\usr\bin\bash -lc "make"
> C:\msys64\usr\bin\bash -lc "make install"
> $Env:PATH += ";C:\Program Files\AWSCLI\bin\"
> aws --version
```

#### Alpine Linux

Below is an example Dockerfile that can be used to get a working
installation of the AWS CLI v2 in an Alpine Linux container as an
[alternative to pre-built binaries for Alpine](https://github.com/aws/aws-cli/issues/4685):
```dockerfile
FROM python:3.8-alpine

ENV AWSCLI_VERSION=2.2.1

RUN apk add --no-cache \
    curl \
    make \
    cmake \
    gcc \
    libc-dev \
    libffi-dev \
    openssl-dev \
    && curl https://awscli.amazonaws.com/awscli-${AWSCLI_VERSION}.tar.gz | tar -xz \
    && cd awscli-${AWSCLI_VERSION} \
    && ./configure --prefix=/opt/aws-cli/ --with-download-deps \
    && make \
    && make install

FROM python:3.8-alpine

RUN apk --no-cache add groff

COPY --from=builder /opt/aws-cli/ /opt/aws-cli/

ENTRYPOINT ["/opt/aws-cli/bin/aws"]
```
This image can be built, and the CLI invoked from a container similar to the
one that is built on Amazon Linux 2:
```
$ docker build --tag awscli-alpine .
$ docker run --rm -it awscli-alpine --version
aws-cli/2.2.1 Python/3.8.11 Linux/5.10.25-linuxkit source/x86_64.alpine.3 prompt/off
```
The final size of this image is 150 MB, which is less than half the size of the
official [AWS CLI Docker image](https://hub.docker.com/r/amazon/aws-cli).


### B. Exploration of CMake

Below shows a sample `CMakeLists.txt` to enable building the AWS CLI via
CMake:
```cmake
cmake_minimum_required(VERSION 3.20)
project(awscli NONE)

set(
  DOWNLOAD_DEPS FALSE
  CACHE BOOL "Whether to download all dependencies and use those when \
building the AWS CLI. If not specified, the dependencies \
(including all python packages) must be installed on your system."
)
set(
  INSTALL_TYPE system-sandbox
  CACHE STRING "Type of AWS CLI installation. Options are: \
system-sandbox and portable-exe. The default is system-sandbox"
)
set(
  Python_EXECUTABLE ""
  CACHE FILEPATH "Path to Python interepreter to use. If not set, cmake \
will find an appropriate Python intrepreter."
)

cmake_path(APPEND CMAKE_SOURCE_DIR scripts buildctl OUTPUT_VARIABLE BUILDCTL)
cmake_path(APPEND CMAKE_BINARY_DIR build OUTPUT_VARIABLE BUILD_DIR)
cmake_path(APPEND CMAKE_INSTALL_PREFIX lib OUTPUT_VARIABLE CMAKE_INSTALL_LIBDIR)
cmake_path(APPEND CMAKE_INSTALL_PREFIX bin OUTPUT_VARIABLE CMAKE_INSTALL_BINDIR)

find_package(Python 3.8...<3.10 REQUIRED)

if (NOT DOWNLOAD_DEPS)
  set(DOWNLOAD_DEPS_FLAG "")
  execute_process(
    COMMAND "${Python_EXECUTABLE}" "${BUILDCTL}" validate-env --artifact "${INSTALL_TYPE}"
    RESULT_VARIABLE RESULT
    ERROR_VARIABLE ERROR_MSG
  )
  if(RESULT AND NOT RESULT EQUAL 0)
    message(FATAL_ERROR "${ERROR_MSG}")
  endif()
else()
  set(DOWNLOAD_DEPS_FLAG "--download-deps")
endif()


add_custom_target(
  _build
  ALL "${Python_EXECUTABLE}" "${BUILDCTL}" build --artifact "${INSTALL_TYPE}" --build-dir "${BUILD_DIR}" "${DOWNLOAD_DEPS_FLAG}"
)

install(
    CODE
    "execute_process(
        COMMAND
        ${Python_EXECUTABLE}
        ${BUILDCTL}
        install
        --build-dir ${BUILD_DIR}
        --lib-dir ${CMAKE_INSTALL_LIBDIR}
        --bin-dir ${CMAKE_INSTALL_BINDIR}
    )"
)

add_custom_target(
  uninstall
  "${Python_EXECUTABLE}" "${BUILDCTL}" uninstall --lib-dir "${CMAKE_INSTALL_LIBDIR}"  --bin-dir "${CMAKE_INSTALL_BINDIR}"
)
```
The entry point to using CMake is calling the `cmake` CLI:
```bash
$ cmake .
```
This is the equivalent to the Autotools `configure` script where the
command resolves configuration and generates a `Makefile` (assuming the
target build system is GNU Makefiles). From there, users can use `make`
to build and install the project:
```bash
$ make
$ make install
```

CMake CLI provides built-in commands that abstracts over the generated build
system that can be used to build and install the project instead:
```bash
$ cmake --build .
$ cmake --install .
```

Similar to Autotools, users can configure the build and install of the project.
Users do so by providing `-D` argument to the initial call to `cmake`. For
example, in the code snippet below, the `-D` argument sets the
`CMAKE_INSTALL_PREFIX` variable (i.e., `--prefix` argument for the `configure` script)
to customize where to install the AWS CLI:
```bash
$ cmake -DCMAKE_INSTALL_PREFIX=/opt/aws-cli/ .
```
Users can also specify custom parameters such as the `DOWNLOAD_DEPS` to
determine whether to download dependencies as part of the build process:
```bash
$ cmake -DDOWNLOAD_DEPS=True .
```
To list all configuration parameters, users can run the following:
```bash
$ cmake -LH
// Specify type of AWS CLI installation. Options are: system-sandbox and portable-exe. The default is system-sandbox
ARTIFACT_TYPE:STRING=system-sandbox

// Install path prefix, prepended onto install directories.
CMAKE_INSTALL_PREFIX:PATH=/usr/local

// Build architectures for OSX
CMAKE_OSX_ARCHITECTURES:STRING=

// Minimum OS X version to target for deployment (at runtime); newer APIs weak linked. Set to empty string for default value.
CMAKE_OSX_DEPLOYMENT_TARGET:STRING=

// The product will be built against the headers and libraries located inside the indicated SDK.
CMAKE_OSX_SYSROOT:STRING=

// Download all dependencies and use those when building the AWS CLI. If not specified, the dependencies (including all python packages) must be installed on your system.
DOWNLOAD_DEPS:BOOL=FALSE

// Type of AWS CLI installation. Options are: system-sandbox and portable-exe. The default is system-sandbox
INSTALL_TYPE:STRING=system-sandbox

// Path to Python interepreter to use. If not set, cmake will find an appropriate Python intrepreter.
Python_EXECUTABLE:FILEPATH=

```
