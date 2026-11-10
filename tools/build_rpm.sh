#!/usr/bin/env bash
# Construit le paquet fastver-<version>-1.<arch>.rpm à partir du dossier PyInstaller déjà préparé pour l'AppImage.
# Builds the fastver-<version>-1.<arch>.rpm package from the PyInstaller folder already prepared for the AppImage.
#
# À lancer après tools/build_appimage.sh (qui laisse build/FastVer.AppDir), ou avec BUNDLE=<dossier> pointant
# sur un dossier contenant FastVer et _internal (par exemple celui d'une AppImage extraite). Requiert rpmbuild
# (paquet « rpm » sous Debian et Ubuntu, « rpm-build » sous Fedora).
# Run after tools/build_appimage.sh (which leaves build/FastVer.AppDir), or with BUNDLE=<folder> pointing at a
# folder holding FastVer and _internal (for instance the one of an extracted AppImage). Requires rpmbuild
# (“rpm” package on Debian and Ubuntu, “rpm-build” on Fedora).
#
# Arborescence commune : tools/linux_tree.sh. / Shared tree: tools/linux_tree.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
PKG="$ROOT/build/rpm-root"
source "$ROOT/tools/linux_tree.sh"
ARCH=$(uname -m)
TOP="$ROOT/build/rpm"
rm -rf "$TOP"
mkdir -p "$TOP/SPECS" "$ROOT/release"
install -D -m 644 LICENSE "$PKG/usr/share/licenses/fastver/LICENSE"

# Dépendances : bibliothèques que l'AppImage laisse au système (voir SYSTEM_LIBS dans FastVer-linux.spec),
# exprimées par leur nom de bibliothèque (soname) pour valoir sous Fedora, RHEL et ses dérivées, et openSUSE.
# La détection automatique de rpm est coupée : elle déclarerait aussi les bibliothèques embarquées (Qt…)
# comme fournies par le paquet, qui pourrait alors satisfaire à tort d'autres paquets.
# Dependencies: libraries the AppImage leaves to the system (see SYSTEM_LIBS in FastVer-linux.spec), written as
# library names (sonames) so they hold on Fedora, RHEL and its derivatives, and openSUSE. rpm's automatic
# detection is off: it would also declare the bundled libraries (Qt…) as provided by the package, which could
# then wrongly satisfy other packages.
LIBS="libc.so.6(GLIBC_2.34) libstdc++.so.6 libgcc_s.so.1 libz.so.1 libzstd.so.1 libglib-2.0.so.0 \
libgthread-2.0.so.0 libfontconfig.so.1 libfreetype.so.6 libdbus-1.so.3 libX11.so.6 libX11-xcb.so.1 libxcb.so.1 \
libEGL.so.1 libGL.so.1 libdrm.so.2 libwayland-client.so.0 libwayland-cursor.so.0 libwayland-egl.so.1"
REQUIRES=""
for lib in $LIBS; do
  case "$lib" in *"("*) REQUIRES+="Requires: ${lib}(64bit)"$'\n' ;; *) REQUIRES+="Requires: ${lib}()(64bit)"$'\n' ;; esac
done

cat > "$TOP/SPECS/fastver.spec" <<EOF
# Paquet binaire : rien n'est compilé ni retouché (pas de strip, pas de debuginfo, pas de recompilation Python).
# Binary package: nothing is compiled or altered (no strip, no debuginfo, no Python recompilation).
%global debug_package %{nil}
%global __os_install_post %{nil}
%global _build_id_links none
%define _binary_payload w6.xzdio

Name:           fastver
Version:        $VERSION
Release:        1
Summary:        "About" window for Fastfetch, in the Windows 11 Winver style
License:        GPL-3.0-or-later
URL:            https://github.com/Bulls64/FastVer
AutoReqProv:    no
${REQUIRES}Recommends:     fastfetch

%description
FastVer shows the system information gathered by Fastfetch in a window
styled after Winver (Windows 11): ASCII logo, specifications, light and
dark themes with an acrylic material. "fastver-cli" (or "fastver --cli")
prints the same information in the terminal.

The package bundles Python, Qt 6 (PySide6, LGPL-3.0) and QFluentWidgets
(GPL-3.0). It is updated through the package manager: FastVer never
replaces its own files and only points to the release page.

%install
cp -a "$PKG/." %{buildroot}/

%files
%license /usr/share/licenses/fastver/LICENSE
/usr/lib/fastver
/usr/bin/fastver
/usr/bin/fastver-cli
/usr/share/applications/fastver.desktop
/usr/share/icons/hicolor/256x256/apps/fastver.png
/usr/share/man/man1/fastver.1.gz
/usr/share/man/man1/fastver-cli.1.gz

%changelog
* $(LC_ALL=C date '+%a %b %d %Y') Bulls64 <Bulls64@users.noreply.github.com> - $VERSION-1
- Release $VERSION: https://github.com/Bulls64/FastVer/releases/tag/v$VERSION
EOF

echo "▶ rpmbuild"
rpmbuild -bb --target "$ARCH" --define "_topdir $TOP" "$TOP/SPECS/fastver.spec"
OUT="$ROOT/release/fastver-$VERSION-1.$ARCH.rpm"
cp "$TOP/RPMS/$ARCH/fastver-$VERSION-1.$ARCH.rpm" "$OUT"
rpm -qp --info "$OUT" | sed -n '1,/^Summary/p'
rpm -qp --requires "$OUT"
ls -l "$OUT"
