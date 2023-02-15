FROM public.ecr.aws/amazonlinux/amazonlinux:2
ENV AUTOCONF_VERSION=2.71
ENV AUTOMAKE_VERSION=1.16.5

WORKDIR /build
COPY ./ /build
RUN yum -y update
RUN yum -y install curl xz gzip  m4 perl perl-Data-Dumper make tar help2man cpanminus
RUN cpanm Thread::Queue

WORKDIR /autoreconf
RUN curl https://ftp.gnu.org/gnu/autoconf/autoconf-${AUTOCONF_VERSION}.tar.gz | tar -xz
WORKDIR /autoreconf/autoconf-${AUTOCONF_VERSION}
RUN ./configure
RUN make
RUN make install

WORKDIR /automake
RUN curl https://ftp.gnu.org/gnu/automake/automake-${AUTOMAKE_VERSION}.tar.xz | tar -xJ
WORKDIR /automake/automake-${AUTOMAKE_VERSION}
RUN ./configure
RUN make
RUN make install

WORKDIR /build
RUN autoreconf