# Credo OS - Fedora-based live/installable image for the ThinkPad X1 Carbon Gen 11
# Built with livemedia-creator (see build/build.sh). @SELINUX@ is replaced by the build script.

lang en_US.UTF-8
keyboard us
timezone UTC --utc
selinux --@SELINUX@
firewall --enabled --service=mdns
# credo-thinkpad is enabled in post.ks: its unit only exists after the overlay is copied.
services --enabled=NetworkManager,ModemManager,tuned,thermald --disabled=sshd
network --bootproto=dhcp --device=link --activate
# Root stays locked; the live user (livesys) and the installer's user use sudo.
# Anaconda needs a password value and prefixes "!" for --lock. Fedora 45's chpasswd
# rejects "!locked", so this is a well-formed SHA-512 value made from no password.
rootpw --lock --iscrypted $6$credoos.locked$0000000000000000000000000000000000000000000000000000000000000000000000000000000000000.
shutdown

url --mirrorlist="https://mirrors.fedoraproject.org/mirrorlist?repo=fedora-$releasever&arch=$basearch"
repo --name=updates --mirrorlist="https://mirrors.fedoraproject.org/mirrorlist?repo=updates-released-f$releasever&arch=$basearch"

zerombr
clearpart --all
part / --size=14336 --fstype=ext4
bootloader --location=none

%include packages.ks
%include post.ks
