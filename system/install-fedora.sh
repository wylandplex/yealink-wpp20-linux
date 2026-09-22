#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then
    echo 'Dieses Hilfsskript wird durch ./install.sh --system mit sudo gestartet.' >&2
    exit 1
fi
source /etc/os-release
if [[ $ID != fedora || $(uname -m) != x86_64 ]]; then
    echo 'Automatische Paketinstallation unterstützt Fedora x86_64. Siehe README.' >&2
    exit 1
fi
dnf install -y python3-gobject gstreamer1-plugins-base gstreamer1-plugins-good \
    pipewire-gstreamer xorg-x11-server-Xvfb xorg-x11-xauth \
    xdg-desktop-portal xdg-desktop-portal-gnome curl \
    glibc.i686 libgcc.i686 freetype.i686 fontconfig.i686 \
    libX11.i686 libXext.i686 libXcursor.i686 libXi.i686 libXrandr.i686 \
    libXrender.i686 libXinerama.i686 libXfixes.i686 libusb1.i686
install -m 644 -- "$(dirname -- "${BASH_SOURCE[0]}")/70-yealink-wpp20.rules" \
    /etc/udev/rules.d/70-yealink-wpp20.rules
udevadm control --reload-rules
echo 'Geräteregel installiert. Den WPP20-Button vor der nächsten Nutzung neu einstecken.'
