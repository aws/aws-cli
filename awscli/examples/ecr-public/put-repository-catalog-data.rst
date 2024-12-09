**To creates or updates the catalog data for a repository in a public registry.**

The following ``put-repository-catalog-data`` example update catalog data for repository named ``project-a/nginx-web-app`` in a public registry, along with ``logoImageBlob``, ``aboutText``, ``usageText`` and tags information. ::

    aws ecr-public put-repository-catalog-data \
        --cli-input-json file://myfile.json

Contents of ``myfile.json``::

    {
        "repositoryName": "project-a/nginx-web-app",
        "catalogData": {
            "description": "My project-a ECR Public Repository",
            "architectures": [
                "ARM",
                "ARM 64",
                "x86",
                "x86-64"
            ],
            "operatingSystems": [
                "Linux"
            ],
            "logoImageBlob": "iVBORw0KGgoA<<truncated-for-better-reading>>ErkJggg==",
            "aboutText": "## Quick reference\n\nMaintained by: [the Amazon Linux Team](https://github.com/aws/amazon-linux-docker-images)\n\nWhere to get help: [the Docker Community Forums](https://forums.docker.com/), [the Docker Community Slack](https://dockr.ly/slack), or [Stack Overflow](https://stackoverflow.com/search?tab=newest&q=docker)\n\n## Supported tags and respective `dockerfile` links\n\n* [`2.0.20200722.0`, `2`, `latest`](https://github.com/amazonlinux/container-images/blob/03d54f8c4d522bf712cffd6c8f9aafba0a875e78/Dockerfile)\n* [`2.0.20200722.0-with-sources`, `2-with-sources`, `with-sources`](https://github.com/amazonlinux/container-images/blob/1e7349845e029a2e6afe6dc473ef17d052e3546f/Dockerfile)\n* [`2018.03.0.20200602.1`, `2018.03`, `1`](https://github.com/amazonlinux/container-images/blob/f10932e08c75457eeb372bf1cc47ea2a4b8e98c8/Dockerfile)\n* [`2018.03.0.20200602.1-with-sources`, `2018.03-with-sources`, `1-with-sources`](https://github.com/amazonlinux/container-images/blob/8c9ee491689d901aa72719be0ec12087a5fa8faf/Dockerfile)\n\n## What is Amazon Linux?\n\nAmazon Linux is provided by Amazon Web Services (AWS). It is designed to provide a stable, secure, and high-performance execution environment for applications running on Amazon EC2. The full distribution includes packages that enable easy integration with AWS, including launch configuration tools and many popular AWS libraries and tools. AWS provides ongoing security and maintenance updates to all instances running Amazon Linux.\n\nThe Amazon Linux container image contains a minimal set of packages. To install additional packages, [use `yum`](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/managing-software.html).\n\nAWS provides two versions of Amazon Linux: [Amazon Linux 2](https://aws.amazon.com/amazon-linux-2/) and [Amazon Linux AMI](https://aws.amazon.com/amazon-linux-ami/).\n\nFor information on security updates for Amazon Linux, please refer to [Amazon Linux 2 Security Advisories](https://alas.aws.amazon.com/alas2.html) and [Amazon Linux AMI Security Advisories](https://alas.aws.amazon.com/). Note that Docker Hub's vulnerability scanning for Amazon Linux is currently based on RPM versions, which does not reflect the state of backported patches for vulnerabilities.\n\n## Where can I run Amazon Linux container images?\n\nYou can run Amazon Linux container images in any Docker based environment. Examples include, your laptop, in Amazon EC2 instances, and Amazon ECS clusters.\n\n## License\n\nAmazon Linux is available under the [GNU General Public License, version 2.0](https://github.com/aws/amazon-linux-docker-images/blob/master/LICENSE). Individual software packages are available under their own licenses; run `rpm -qi [package name]` or check `/usr/share/doc/[package name]-*` and `/usr/share/licenses/[package name]-*` for details.\n\nAs with all Docker images, these likely also contain other software which may be under other licenses (such as Bash, etc from the base distribution, along with any direct or indirect dependencies of the primary software being contained).\n\nSome additional license information which was able to be auto-detected might be found in [the `repo-info` repository's `amazonlinux/` directory](https://github.com/docker-library/repo-info/tree/master/repos/amazonlinux).\n\n## Security\n\nFor information on security updates for Amazon Linux, please refer to [Amazon Linux 2 Security Advisories](https://alas.aws.amazon.com/alas2.html) and [Amazon Linux AMI Security Advisories](https://alas.aws.amazon.com/). Note that Docker Hub's vulnerability scanning for Amazon Linux is currently based on RPM versions, which does not reflect the state of backported patches for vulnerabilities.",
            "usageText": "## Supported architectures\n\namd64, arm64v8\n\n## Where can I run Amazon Linux container images?\n\nYou can run Amazon Linux container images in any Docker based environment. Examples include, your laptop, in Amazon EC2 instances, and ECS clusters.\n\n## How do I install a software package from Extras repository in Amazon Linux 2?\n\nAvailable packages can be listed with the `amazon-linux-extras` command. Packages can be installed with the `amazon-linux-extras install <package>` command. Example: `amazon-linux-extras install rust1`\n\n## Will updates be available for Amazon Linux containers?\n\nSimilar to the Amazon Linux images for Amazon EC2 and on-premises use, Amazon Linux container images will get ongoing updates from Amazon in the form of security updates, bug fix updates, and other enhancements. Security bulletins for Amazon Linux are available at https://alas.aws.amazon.com/\n\n## Will AWS Support the current version of Amazon Linux going forward?\n\nYes; in order to avoid any disruption to your existing applications and to facilitate migration to Amazon Linux 2, AWS will provide regular security updates for Amazon Linux 2018.03 AMI and container image for 2 years after the final LTS build is announced. You can also use all your existing support channels such as AWS Support and Amazon Linux Discussion Forum to continue to submit support requests."
        }
    }

Output::

    {
        "catalogData": {
            "description": "My project-a ECR Public Repository",
            "architectures": [
                "ARM",
                "ARM 64",
                "x86",
                "x86-64"
            ],
            "operatingSystems": [
                "Linux"
            ],
            "logoUrl": "https://d3g9o9u8re44ak.cloudfront.net/logo/df86cf58-ee60-4061-b804-0be24d97ccb1/4a9ed9b2-69e4-4ede-b924-461462d20ef0.png",
            "aboutText": "## Quick reference\n\nMaintained by: [the Amazon Linux Team](https://github.com/aws/amazon-linux-docker-images)\n\nWhere to get help: [the Docker Community Forums](https://forums.docker.com/), [the Docker Community Slack](https://dockr.ly/slack), or [Stack Overflow](https://stackoverflow.com/search?tab=newest&q=docker)\n\n## Supported tags and respective `dockerfile` links\n\n* [`2.0.20200722.0`, `2`, `latest`](https://github.com/amazonlinux/container-images/blob/03d54f8c4d522bf712cffd6c8f9aafba0a875e78/Dockerfile)\n* [`2.0.20200722.0-with-sources`, `2-with-sources`, `with-sources`](https://github.com/amazonlinux/container-images/blob/1e7349845e029a2e6afe6dc473ef17d052e3546f/Dockerfile)\n* [`2018.03.0.20200602.1`, `2018.03`, `1`](https://github.com/amazonlinux/container-images/blob/f10932e08c75457eeb372bf1cc47ea2a4b8e98c8/Dockerfile)\n* [`2018.03.0.20200602.1-with-sources`, `2018.03-with-sources`, `1-with-sources`]
            (https://github.com/amazonlinux/container-images/blob/8c9ee491689d901aa72719be0ec12087a5fa8faf/
            Dockerfile)\n\n## What is Amazon Linux?\n\nAmazon Linux is provided by Amazon Web Services (AWS
            ). It is designed to provide a stable, secure, and high-performance execution environment for a
            pplications running on Amazon EC2. The full distribution includes packages that enable easy int
            egration with AWS, including launch configuration tools and many popular AWS libraries and tool
            s. AWS provides ongoing security and maintenance updates to all instances running Amazon Linux.
            \n\nThe Amazon Linux container image contains a minimal set of packages. To install additional 
            packages, [use `yum`](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/managing-software.htm
            l).\n\nAWS provides two versions of Amazon Linux: [Amazon Linux 2](https://aws.amazon.com/amazo
            n-linux-2/) and [Amazon Linux AMI](https://aws.amazon.com/amazon-linux-ami/).\n\nFor informatio
            n on security updates for Amazon Linux, please refer to [Amazon Linux 2 Security Advisories](ht
            tps://alas.aws.amazon.com/alas2.html) and [Amazon Linux AMI Security Advisories](https://alas.a
            ws.amazon.com/). Note that Docker Hub's vulnerability scanning for Amazon Linux is currently ba
            sed on RPM versions, which does not reflect the state of backported patches for vulnerabilities
            .\n\n## Where can I run Amazon Linux container images?\n\nYou can run Amazon Linux container im
            ages in any Docker based environment. Examples include, your laptop, in Amazon EC2 instances, a
            nd Amazon ECS clusters.\n\n## License\n\nAmazon Linux is available under the [GNU General Publi
            c License, version 2.0](https://github.com/aws/amazon-linux-docker-images/blob/master/LICENSE).
            Individual software packages are available under their own licenses; run `rpm -qi [package nam
            e]` or check `/usr/share/doc/[package name]-*` and `/usr/share/licenses/[package name]-*` for d
            etails.\n\nAs with all Docker images, these likely also contain other software which may be und
            er other licenses (such as Bash, etc from the base distribution, along with any direct or indir
            ect dependencies of the primary software being contained).\n\nSome additional license informati
            on which was able to be auto-detected might be found in [the `repo-info` repository's `amazonli
            nux/` directory](https://github.com/docker-library/repo-info/tree/master/repos/amazonlinux).\n\
            n## Security\n\nFor information on security updates for Amazon Linux, please refer to [Amazon L
            inux 2 Security Advisories](https://alas.aws.amazon.com/alas2.html) and [Amazon Linux AMI Secur
            ity Advisories](https://alas.aws.amazon.com/). Note that Docker Hub's vulnerability scanning fo
            r Amazon Linux is currently based on RPM versions, which does not reflect the state of backport
            ed patches for vulnerabilities.",
                    "usageText": "## Supported architectures\n\namd64, arm64v8\n\n## Where can I run Amazon
            Linux container images?\n\nYou can run Amazon Linux container images in any Docker based envir
            onment. Examples include, your laptop, in Amazon EC2 instances, and ECS clusters.\n\n## How do 
            I install a software package from Extras repository in Amazon Linux 2?\n\nAvailable packages ca
            n be listed with the `amazon-linux-extras` command. Packages can be installed with the `amazon-
            linux-extras install <package>` command. Example: `amazon-linux-extras install rust1`\n\n## Wil
            l updates be available for Amazon Linux containers?\n\nSimilar to the Amazon Linux images for A
            mazon EC2 and on-premises use, Amazon Linux container images will get ongoing updates from Amaz
            on in the form of security updates, bug fix updates, and other enhancements. Security bulletins
            for Amazon Linux are available at https://alas.aws.amazon.com/\n\n## Will AWS Support the curr
            ent version of Amazon Linux going forward?\n\nYes; in order to avoid any disruption to your exi
            sting applications and to facilitate migration to Amazon Linux 2, AWS will provide regular secu
            rity updates for Amazon Linux 2018.03 AMI and container image for 2 years after the final LTS b
            uild is announced. You can also use all your existing support channels such as AWS Support and 
            Amazon Linux Discussion Forum to continue to submit support requests."
        }
    }

For more information, see `Repository catalog data <https://docs.aws.amazon.com/AmazonECR/latest/public/public-repository-catalog-data.html>`__ in the *Amazon ECR Public*.