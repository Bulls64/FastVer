# FastVer

Une fenêtre « À propos » pour [Fastfetch](https://github.com/fastfetch-cli/fastfetch), inspirée de Winver (Windows 11) et dessinée avec les composants Fluent de WinUI 3 (PySide6 + QFluentWidgets).

*An “About” window for Fastfetch, inspired by Windows 11's Winver, built with PySide6 + QFluentWidgets.*

<p align="center">
  <img src="docs/screenshots/main.png" width="400" alt="Fenêtre principale de FastVer, thème clair">
  <img src="docs/screenshots/dark.png" width="400" alt="FastVer en thème sombre, spécifications de l'appareil dépliées">
</p>
<p align="center"><sub>Thème clair et thème sombre avec les spécifications dépliées (mode démo : <code>--demo</code>).</sub></p>

## Installation

- **Windows :** téléchargez `FastVer.exe` depuis la [dernière version](../../releases/latest). Fastfetch doit être installé (`winget install Fastfetch-cli.Fastfetch`).
- **Linux :** téléchargez `FastVer-x86_64.AppImage`, rendez-le exécutable (`chmod +x FastVer-x86_64.AppImage`) et lancez-le. Il embarque Python et Qt ; il faut seulement Fastfetch et une distribution avec glibc 2.34 ou plus (Ubuntu 22.04, Debian 12, Fedora 35, RHEL 9 et plus récentes). Si FUSE manque : `./FastVer-x86_64.AppImage --appimage-extract-and-run`.
- **Script :** `pip install PySide6-Fluent-Widgets`, puis `python fastver.py`.

L'exe n'est pas signé : au premier lancement, SmartScreen demande une confirmation (« Informations complémentaires » → « Exécuter quand même »).

## Mises à jour

<p align="center">
  <img src="docs/screenshots/settings.png" width="400" alt="Page Réglages de FastVer : langue, mise à jour de Fastfetch et de FastVer">
</p>

FastVer peut se mettre à jour lui-même depuis les releases de ce dépôt (Réglages → Application FastVer). Chaque fichier est vérifié avant d'être installé : son empreinte SHA-256 doit correspondre à celle publiée dans le fichier `.sha256` qui l'accompagne et à celle que GitHub calcule pour l'asset. Sans empreinte, ou si elles se contredisent, la mise à jour est refusée.

## Publier une version

1. Changer `APP_VERSION` et `BUILD` dans `fastver.py`.
2. `git tag v1.2.0 && git push origin v1.2.0`

Le workflow `.github/workflows/release.yml` compile alors l'exe sur Windows et l'AppImage sur Ubuntu 22.04, lance leur autotest (`--selftest`), calcule les empreintes et publie la release avec `FastVer.exe`, `FastVer-x86_64.AppImage`, `fastver.py`, leurs `.sha256` et `SHA256SUMS`.

Compilation locale (dépendances) : `pip install -r requirements-build.txt`, puis `pip install --no-deps -r requirements-nodeps.txt`.

- **Exe :** `python tools/make_version_info.py`, puis `python -m PyInstaller --noconfirm --clean FastVer.spec`.
- **AppImage :** `bash tools/build_appimage.sh` (binutils requis ; appimagetool est téléchargé s'il manque).

## Licence

FastVer embarque [QFluentWidgets](https://pypi.org/project/pyside6-fluent-widgets), publié sous GPLv3 pour un usage non commercial. FastVer doit donc être distribué sous une licence compatible (GPLv3) avec ses sources.
