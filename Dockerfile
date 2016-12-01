FROM centos/python-35-centos7
MAINTAINER Nick Coghlan <ncoghlan@redhat.com>

# Add "rpmdevtools" so we can use it for RPM processing
USER 0

RUN rpmkeys --import file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7 && \
  INSTALL_PKGS="rpmdevtools" && \
  yum install -y --setopt=tsflags=nodocs $INSTALL_PKGS && \
  rpm -V $INSTALL_PKGS && \
  yum clean all -y

USER 1001

# Set a sensible environment for operating system interfaces
# (CentOS 7 doesn't currently provide C.UTF-8)
ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8
