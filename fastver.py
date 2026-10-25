#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastVer — une fenêtre « À propos » pour Fastfetch, inspirée de Winver (Windows 11)
et dessinée avec les composants Fluent de WinUI 3 (PySide6 + QFluentWidgets).

Le logo ASCII de Fastfetch est rendu en couleurs, la couleur d'accent s'adapte au
logo de votre système, un fond acrylique (fond d'écran flouté et teinté) habille la fenêtre, et les
spécifications complètes se déplient comme dans Paramètres > Système > Informations système.

Installation :
    pip install PySide6-Fluent-Widgets
    (sinon FastVer propose de l'installer lui-même au premier lancement)

Utilisation :
    python fastver.py                  lit votre système via Fastfetch
    python fastver.py --demo           données de démonstration (sans Fastfetch)
    python fastver.py --theme dark     thème : auto (défaut) | light | dark
    python fastver.py --accent system  accent : logo (défaut) | system | #RRGGBB
    python fastver.py --backdrop solid fond uni au lieu de l'acrylique
    python fastver.py --wallpaper IMG  image à flouter pour l'acrylique (défaut : fond d'écran)
    python fastver.py --expand         ouvre directement les spécifications
    python fastver.py --fastfetch C:\\outils\\fastfetch.exe
    python fastver.py --lang en        langue pour cette session : auto | fr | en

Réglages (roue dentée, en bas de la fenêtre) : langue, vérification et mise à jour de
Fastfetch et de FastVer, manuellement ou automatiquement au démarrage. Ils sont enregistrés
dans %APPDATA%\\FastVer\\settings.json (Windows) ou ~/.config/FastVer/settings.json.

Raccourcis : Entrée / Échap = fermer · F5 = actualiser · Ctrl+Maj+C = tout copier
             D = déplier / replier les spécifications · T = changer de thème
Astuce : cliquez sur le logo.

──────────────────────────────────────────────────────────────────────────────

FastVer — an “About” window for Fastfetch, inspired by Winver (Windows 11)
and drawn with the Fluent components of WinUI 3 (PySide6 + QFluentWidgets).

Fastfetch's ASCII logo is rendered in color, the accent color adapts to your
system's logo, an acrylic background (blurred, tinted wallpaper) dresses the window, and the
full specifications expand like in Settings > System > About.

Installation:
    pip install PySide6-Fluent-Widgets
    (otherwise FastVer offers to install it by itself on first launch)

Usage:
    python fastver.py                  reads your system through Fastfetch
    python fastver.py --demo           sample data (without Fastfetch)
    python fastver.py --theme dark     theme: auto (default) | light | dark
    python fastver.py --accent system  accent: logo (default) | system | #RRGGBB
    python fastver.py --backdrop solid solid background instead of the acrylic
    python fastver.py --wallpaper IMG  image to blur for the acrylic (default: wallpaper)
    python fastver.py --expand         opens the specifications right away
    python fastver.py --fastfetch C:\\tools\\fastfetch.exe
    python fastver.py --lang en        language for this session: auto | fr | en

Settings (gear button, at the bottom of the window): language, checking and updating
Fastfetch and FastVer, manually or automatically at startup. They are saved
in %APPDATA%\\FastVer\\settings.json (Windows) or ~/.config/FastVer/settings.json.

Shortcuts: Enter / Esc = close · F5 = refresh · Ctrl+Shift+C = copy everything
           D = expand / collapse the specifications · T = switch theme
Tip: click the logo.

"""

import argparse
import colorsys
import ctypes
# Importé explicitement AVANT Qt : sous Python 3.15, le système d'import de PySide6 6.12
# casse les imports différés de concurrent.futures (« 'lazy_import' object is not callable »).
# Imported explicitly BEFORE Qt: under Python 3.15, PySide6 6.12's import system
# breaks the lazy imports of concurrent.futures (“'lazy_import' object is not callable”).
from concurrent.futures import ThreadPoolExecutor
import datetime
import getpass
import glob
import hashlib
import hmac
import importlib.util
import json
import locale
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import threading
import time
import traceback
import http.client  # noqa: F401 — utilisés en interne par urllib : chargés ici exprès, avant Qt
import ssl          # noqa: F401 — used internally by urllib: deliberately loaded here, before Qt
import urllib.error
import urllib.parse
import urllib.request
if os.name == "nt":
    import winreg
# Tous les modules de la bibliothèque standard sont chargés ici, avant Qt (cf. Python 3.15) :
# aucun import ne doit avoir lieu plus tard, dans une fonction appelée une fois Qt chargé.
# Every standard-library module is loaded here, before Qt (see Python 3.15):
# no import may happen later, inside a function called once Qt is loaded.

APP_NAME = "FastVer"
APP_VERSION = "1.2.1"   # version publiée (comparée aux releases GitHub pour la mise à jour)
                        # published version (compared with GitHub releases for updates)
BUILD = "2026-10-25-l"  # change à chaque correctif : permet de vérifier quelle version tourne
                        # changes with every fix: lets you check which version is running
UPDATE_REPO = "Bulls64/FastVer"   # dépôt GitHub où publier les nouvelles versions (assets « fastver.py »,
                                  # « FastVer.exe » et leurs empreintes « .sha256 »)
                                  # GitHub repository where new versions are published (assets “fastver.py”,
                                  # “FastVer.exe” and their “.sha256” checksums)
FF_REPO = "fastfetch-cli/fastfetch"
FF_WINGET_ID = "Fastfetch-cli.Fastfetch"
GITHUB_API = os.environ.get("FASTVER_GITHUB_API", "https://api.github.com").rstrip("/")
FASTFETCH_URL = "https://github.com/fastfetch-cli/fastfetch"
LICENSE_URL = FASTFETCH_URL + "/blob/dev/LICENSE"
JSON_STRUCTURE = "Title:OS:Host:Kernel:Uptime:Packages:Shell:DE:WM:Terminal:CPU:GPU:Memory:Swap:Disk:Locale"
FROZEN = bool(getattr(sys, "frozen", False))  # vrai dans FastVer.exe et l'AppImage (PyInstaller)
                                               # true inside FastVer.exe and the AppImage (PyInstaller)
# Chemin du fichier .AppImage lancé (variable posée par l'AppImage elle-même), sinon None.
# Path of the launched .AppImage file (variable set by the AppImage itself), otherwise None.
APPIMAGE = os.environ.get("APPIMAGE") if FROZEN and sys.platform.startswith("linux") else None
# Forme de FastVer en cours d'exécution : « exe » (Windows), « appimage » (Linux), « script » (fastver.py),
# ou « frozen » (compilé mais pas empaqueté : mises à jour via la page de la version seulement).
# Form of the running FastVer: “exe” (Windows), “appimage” (Linux), “script” (fastver.py),
# or “frozen” (compiled but not packaged: updates through the release page only).
PACKAGE = ("exe" if os.name == "nt" else "appimage" if APPIMAGE else "frozen") if FROZEN else "script"
# Fichier à télécharger lors d'une mise à jour, et nom de la copie gardée de l'ancienne version.
# File to download when updating, and name of the copy kept of the old version.
APP_ASSET, BACKUP_NAME = {
    "exe": ("FastVer.exe", "FastVer-{v}.bak.exe"),
    "appimage": (f"FastVer-{platform.machine()}.AppImage", "FastVer-{v}.bak.AppImage"),
    "script": ("fastver.py", "fastver-{v}.bak.py"),
}.get(PACKAGE, (None, None))
if FROZEN and sys.platform.startswith("linux"):
    # PyInstaller fait pointer LD_LIBRARY_PATH vers ses propres bibliothèques : les programmes lancés par
    # FastVer (fastfetch, navigateur, gsettings…) les chargeraient à la place de celles du système et
    # pourraient planter. On rétablit la valeur d'origine pour eux ; FastVer lui-même n'est pas affecté.
    # PyInstaller points LD_LIBRARY_PATH at its own libraries: programs started by FastVer (fastfetch,
    # browser, gsettings…) would load them instead of the system's and could crash. Restore the original
    # value for them; FastVer itself isn't affected.
    _orig = os.environ.pop("LD_LIBRARY_PATH_ORIG", None)
    if _orig:
        os.environ["LD_LIBRARY_PATH"] = _orig
    else:
        os.environ.pop("LD_LIBRARY_PATH", None)
NO_WINDOW = {"creationflags": 0x08000000} if os.name == "nt" else {}  # CREATE_NO_WINDOW
LOG_PATH = os.path.join(tempfile.gettempdir(), "fastver.log")
LOG_MAX = 512 * 1024   # au-delà, le journal est renommé en fastver.log.1 (un seul ancien journal gardé)
                       # beyond this, the log is renamed to fastver.log.1 (only one old log kept)
APP_PATH = os.path.abspath(APPIMAGE or (sys.executable if FROZEN else __file__))  # fichier lancé
                                                                                   # launched file


def write_log(text):
    try:
        if os.path.getsize(LOG_PATH) > LOG_MAX:
            os.replace(LOG_PATH, LOG_PATH + ".1")
    except OSError:
        pass
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n=== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} ===\n{text}\n")
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════════════════
#  Réglages (fichier JSON dans le dossier de configuration de l'utilisateur)
#  Settings (JSON file in the user's configuration folder)
# ════════════════════════════════════════════════════════════════════════════

def config_dir():
    if os.environ.get("FASTVER_CONFIG_DIR"):
        return os.environ["FASTVER_CONFIG_DIR"]
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, APP_NAME)


class Settings(dict):
    DEFAULTS = {"language": "auto", "fastfetch_auto_update": False, "app_auto_update": False}

    def __init__(self):
        super().__init__(self.DEFAULTS)
        self.path = os.path.join(config_dir(), "settings.json")
        try:
            with open(self.path, encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                self.update({k: v for k, v in saved.items() if k in self.DEFAULTS})
        except FileNotFoundError:
            pass
        except Exception as e:
            write_log(f"Réglages illisibles ({self.path}) : {e!r} — valeurs par défaut utilisées")
        if self["language"] not in ("auto", "fr", "en"):
            self["language"] = "auto"

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(dict(self), f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)
        except Exception as e:
            write_log(f"Impossible d'enregistrer les réglages ({self.path}) : {e!r}")


# ════════════════════════════════════════════════════════════════════════════
#  Traduction (français / anglais)
#  Translation (French / English)
# ════════════════════════════════════════════════════════════════════════════

STRINGS = {
    "fr": {
        # Fenêtre principale
        # Main window
        "about_fastfetch": "À propos de Fastfetch",
        "about": "À propos de {name}",
        "loading": "Interrogation de votre système…",
        "ff_missing_title": "Fastfetch est introuvable",
        "ff_missing_msg": "Installez Fastfetch (winget install fastfetch, scoop install fastfetch, "
                          "brew install fastfetch, ou le gestionnaire de paquets de votre distribution), "
                          "puis relancez FastVer. Vous pouvez aussi indiquer son chemin avec --fastfetch.",
        "ff_failed_title": "Fastfetch n'a pas pu répondre",
        "ff_no_data": "Fastfetch n'a renvoyé aucune donnée.",
        "exit_code": "code de sortie {code}",
        "get_fastfetch": "Obtenir Fastfetch",
        "demo_mode": "Mode démo",
        "close": "Fermer",
        "demo_tag": "Démo",
        "demo_user": "Utilisateur de démonstration",
        "copyright": "© {year} {owner}. Tous droits réservés.",
        "license": "Ce produit est concédé sous licence selon les {link} à :",
        "license_link": "termes de la licence MIT de Fastfetch",
        "specs_title": "Spécifications de l'appareil",
        "specs_sub": "{n} éléments · cliquez sur une ligne pour la copier",
        "copy": "Copier",
        "copied": "Copié",
        "copied_default": "Copié dans le presse-papiers.",
        "copied_row": "« {key} » copié dans le presse-papiers.",
        "copied_all": "Toutes les spécifications ont été copiées.",
        "status_demo": "Mode démo · données fictives",
        "status_refreshed": "actualisé à {time}",
        "refresh": "Actualiser",
        "ok": "OK",
        "theme_tip": "Thème clair / sombre (T)",
        "settings_tip": "Réglages",
        "click_me": "Cliquez-moi",
        "device_name": "Nom de l'appareil",
        "version_build": "Version {ver} (build {build})",
        "build_only": "Build {build}",
        "version_kernel": "Version {ver} (noyau {kern})",
        "kernel_only": "Noyau {kern}",
        "version": "Version {v}",
        "units": ("octets", "Kio", "Mio", "Gio", "Tio", "Pio"),
        "and": "et",
        "day": "jour", "days": "jours", "hour": "heure", "hours": "heures",
        "minute": "minute", "minutes": "minutes",
        # Réglages
        # Settings
        "settings": "Réglages",
        "settings_window": "Réglages de FastVer",
        "back": "Retour",
        "done": "Terminé",
        "general": "Général",
        "language": "Langue",
        "language_desc": "Langue de l'interface de FastVer",
        "lang_auto": "Langue du système",
        "group_fastfetch": "Fastfetch",
        "group_app": "Application FastVer",
        "auto_update": "Mise à jour automatique au démarrage",
        "auto_fastfetch_desc": "Installe la dernière version de Fastfetch à chaque lancement de FastVer",
        "auto_app_desc": "Installe la dernière version de FastVer à chaque lancement",
        "on": "Activé", "off": "Désactivé",
        "check": "Rechercher",
        "update": "Mettre à jour",
        "restart": "Redémarrer",
        "open_page": "Ouvrir la page",
        "ff_not_installed": "Fastfetch introuvable",
        "method_winget": "winget", "method_scoop": "Scoop", "method_choco": "Chocolatey",
        "method_brew": "Homebrew", "method_system": "paquet système", "method_manual": "installation manuelle",
        "st_idle": "Pas encore vérifié",
        "st_checking": "Recherche de mises à jour…",
        "st_uptodate": "À jour · dernière version : {latest}",
        "st_available": "Mise à jour disponible : {latest}",
        "st_hint": "Mise à jour disponible : {latest} · à installer avec « {cmd} »",
        "st_page": "Mise à jour disponible : {latest} · à télécharger sur la page de Fastfetch",
        "st_page_app": "Mise à jour disponible : {latest} · à télécharger sur la page de la version",
        "st_missing": "Dernière version : {latest} · Fastfetch n'est pas installé",
        "st_updating": "Mise à jour en cours…",
        "st_updated": "Mis à jour vers la version {latest}",
        "st_updated_restart": "Version {latest} installée · redémarrez FastVer pour l'utiliser",
        "st_dev": "Version plus récente que la dernière publiée ({latest})",
        "st_norelease": "Aucune version publiée sur github.com/{repo}",
        "st_error": "Échec : {msg}",
        "net_error": "GitHub injoignable ({err})",
        "rate_limited": "limite de requêtes GitHub atteinte, réessayez dans une heure",
        "bad_download": "le fichier téléchargé n'est pas une version valide de FastVer",
        "write_error": "impossible d'écrire {path} ({err})",
        "no_command": "aucune commande de mise à jour disponible pour cette installation",
        "toast_update": "Mise à jour",
        "toast_ff_updated": "Fastfetch a été mis à jour vers la version {v}.",
        "toast_ff_available": "Fastfetch {v} est disponible : installez-le depuis les réglages.",
        "toast_app_updated": "FastVer {v} est installé. Redémarrez FastVer pour l'utiliser.",
        "toast_failed": "La mise à jour automatique de {what} a échoué : {msg}",
        "toast_app_available": "FastVer {v} est disponible : téléchargez-le depuis les réglages.",
        "bad_checksum": "l'empreinte SHA-256 du fichier téléchargé ne correspond pas à celle publiée : "
                        "mise à jour refusée",
        "checksum_conflict": "les empreintes SHA-256 publiées pour {name} se contredisent : mise à jour refusée",
        "st_no_checksum": "Mise à jour disponible : {latest} · aucune empreinte SHA-256 publiée, "
                          "à télécharger sur la page de la version",
        "ff_not_yet": "{tool} ne propose pas encore la version {latest} (version installée : {local}). "
                      "Réessayez plus tard ou téléchargez-la sur la page de Fastfetch.",
        "group_backups": "Anciennes versions",
        "backups_title": "Copies de sauvegarde",
        "backups_desc": "{n} anciennes versions de FastVer gardées après des mises à jour · {size}",
        "backups_desc_1": "Une ancienne version de FastVer gardée après une mise à jour · {size}",
        "backups_delete": "Supprimer",
        "backups_deleted": "{n} copies supprimées.",
        "backups_deleted_1": "Copie supprimée.",
        "already_running": "FastVer est déjà ouvert.",
        # Démarrage, réparation des dépendances
        # Startup, dependency repair
        "fatal_title": "FastVer — erreur",
        "fatal_msg": "FastVer n'a pas pu démarrer.\n\n{tail}\n\nLe détail complet est dans :\n{log}",
        "deps_title": "FastVer — composants manquants",
        "deps_msg": "L'interface WinUI 3 de FastVer a besoin de PySide6 et de QFluentWidgets, qui ne sont "
                    "pas utilisables actuellement :\n\n{err}\n\nLes installer (ou les réparer) maintenant "
                    "avec pip ? (quelques minutes)",
        "deps_installing": "Installation de PySide6 et de QFluentWidgets…",
        "deps_repairing": "Réparation de PySide6 et de QFluentWidgets…",
        "deps_fail_title": "FastVer — échec de l'installation",
        "deps_fail_msg": "pip n'a pas pu installer {pkg}.\n\n{tail}\n\n{hint}\n\nDétails : {log}",
        "deps_locked": "Un fichier de PySide6 est encore utilisé par un autre programme Python. Fermez les "
                       "autres fenêtres FastVer, les terminaux Python et les éditeurs (VS Code, PyCharm…) "
                       "qui l'utilisent, puis cliquez sur Réessayer.",
        "deps_net": "Vérifiez votre connexion Internet et que Python {ver} est pris en charge par PySide6.",
        # Ligne de commande
        # Command line
        "cli_desc": "Fenêtre « À propos » pour Fastfetch, dans le style WinUI 3 de Windows 11.",
        "cli_demo": "utiliser des données de démonstration",
        "cli_theme": "thème : auto, light (clair) ou dark (sombre)",
        "cli_accent": "couleur d'accent : logo, system ou #RRGGBB",
        "cli_expand": "déplier les spécifications au démarrage",
        "cli_backdrop": "fond de la fenêtre : acrylic (défaut) ou solid",
        "cli_wallpaper": "image à flouter pour l'acrylique (défaut : fond d'écran)",
        "cli_fastfetch": "chemin vers l'exécutable fastfetch",
        "cli_lang": "langue de l'interface pour cette session : auto, fr ou en",
    },
    "en": {
        "about_fastfetch": "About Fastfetch",
        "about": "About {name}",
        "loading": "Querying your system…",
        "ff_missing_title": "Fastfetch not found",
        "ff_missing_msg": "Install Fastfetch (winget install fastfetch, scoop install fastfetch, "
                          "brew install fastfetch, or your distribution's package manager), then restart "
                          "FastVer. You can also give its path with --fastfetch.",
        "ff_failed_title": "Fastfetch didn't respond",
        "ff_no_data": "Fastfetch returned no data.",
        "exit_code": "exit code {code}",
        "get_fastfetch": "Get Fastfetch",
        "demo_mode": "Demo mode",
        "close": "Close",
        "demo_tag": "Demo",
        "demo_user": "Demo user",
        "copyright": "© {year} {owner}. All rights reserved.",
        "license": "This product is licensed under the {link} to:",
        "license_link": "Fastfetch MIT License terms",
        "specs_title": "Device specifications",
        "specs_sub": "{n} items · click a row to copy it",
        "copy": "Copy",
        "copied": "Copied",
        "copied_default": "Copied to the clipboard.",
        "copied_row": "“{key}” copied to the clipboard.",
        "copied_all": "All specifications copied.",
        "status_demo": "Demo mode · sample data",
        "status_refreshed": "refreshed at {time}",
        "refresh": "Refresh",
        "ok": "OK",
        "theme_tip": "Light / dark theme (T)",
        "settings_tip": "Settings",
        "click_me": "Click me",
        "device_name": "Device name",
        "version_build": "Version {ver} (build {build})",
        "build_only": "Build {build}",
        "version_kernel": "Version {ver} (kernel {kern})",
        "kernel_only": "Kernel {kern}",
        "version": "Version {v}",
        "units": ("bytes", "KiB", "MiB", "GiB", "TiB", "PiB"),
        "and": "and",
        "day": "day", "days": "days", "hour": "hour", "hours": "hours",
        "minute": "minute", "minutes": "minutes",
        "settings": "Settings",
        "settings_window": "FastVer settings",
        "back": "Back",
        "done": "Done",
        "general": "General",
        "language": "Language",
        "language_desc": "Language of the FastVer interface",
        "lang_auto": "System language",
        "group_fastfetch": "Fastfetch",
        "group_app": "FastVer app",
        "auto_update": "Update automatically at startup",
        "auto_fastfetch_desc": "Installs the latest Fastfetch every time FastVer starts",
        "auto_app_desc": "Installs the latest FastVer every time it starts",
        "on": "On", "off": "Off",
        "check": "Check now",
        "update": "Update",
        "restart": "Restart",
        "open_page": "Open page",
        "ff_not_installed": "Fastfetch not found",
        "method_winget": "winget", "method_scoop": "Scoop", "method_choco": "Chocolatey",
        "method_brew": "Homebrew", "method_system": "system package", "method_manual": "manual install",
        "st_idle": "Not checked yet",
        "st_checking": "Checking for updates…",
        "st_uptodate": "Up to date · latest version: {latest}",
        "st_available": "Update available: {latest}",
        "st_hint": "Update available: {latest} · install it with “{cmd}”",
        "st_page": "Update available: {latest} · download it from the Fastfetch page",
        "st_page_app": "Update available: {latest} · download it from the release page",
        "st_missing": "Latest version: {latest} · Fastfetch isn't installed",
        "st_updating": "Updating…",
        "st_updated": "Updated to version {latest}",
        "st_updated_restart": "Version {latest} installed · restart FastVer to use it",
        "st_dev": "Newer than the latest published version ({latest})",
        "st_norelease": "No release published on github.com/{repo}",
        "st_error": "Failed: {msg}",
        "net_error": "can't reach GitHub ({err})",
        "rate_limited": "GitHub request limit reached, try again in an hour",
        "bad_download": "the downloaded file isn't a valid FastVer version",
        "write_error": "couldn't write {path} ({err})",
        "no_command": "no update command available for this installation",
        "toast_update": "Update",
        "toast_ff_updated": "Fastfetch was updated to version {v}.",
        "toast_ff_available": "Fastfetch {v} is available. Open Settings to install it.",
        "toast_app_updated": "FastVer {v} is installed. Restart to use it.",
        "toast_failed": "Automatic update of {what} failed: {msg}",
        "toast_app_available": "FastVer {v} is available. Open Settings to download it.",
        "bad_checksum": "the downloaded file's SHA-256 checksum doesn't match the published one: update refused",
        "checksum_conflict": "the SHA-256 checksums published for {name} contradict each other: update refused",
        "st_no_checksum": "Update available: {latest} · no SHA-256 checksum published, "
                          "download it from the release page",
        "ff_not_yet": "{tool} doesn't offer version {latest} yet (installed version: {local}). "
                      "Try again later or download it from the Fastfetch page.",
        "group_backups": "Previous versions",
        "backups_title": "Backup copies",
        "backups_desc": "{n} previous FastVer versions kept after updates · {size}",
        "backups_desc_1": "One previous FastVer version kept after an update · {size}",
        "backups_delete": "Delete",
        "backups_deleted": "{n} copies deleted.",
        "backups_deleted_1": "Copy deleted.",
        "already_running": "FastVer is already open.",
        "fatal_title": "FastVer — error",
        "fatal_msg": "FastVer couldn't start.\n\n{tail}\n\nFull details in:\n{log}",
        "deps_title": "FastVer — missing components",
        "deps_msg": "FastVer's WinUI 3 interface needs PySide6 and QFluentWidgets, which can't be used "
                    "right now:\n\n{err}\n\nInstall (or repair) them now with pip? (a few minutes)",
        "deps_installing": "Installing PySide6 and QFluentWidgets…",
        "deps_repairing": "Repairing PySide6 and QFluentWidgets…",
        "deps_fail_title": "FastVer — installation failed",
        "deps_fail_msg": "pip couldn't install {pkg}.\n\n{tail}\n\n{hint}\n\nDetails: {log}",
        "deps_locked": "A PySide6 file is still in use by another Python program. Close other FastVer "
                       "windows, Python terminals and editors (VS Code, PyCharm…) using it, then click Retry.",
        "deps_net": "Check your Internet connection and that Python {ver} is supported by PySide6.",
        "cli_desc": "An “About” window for Fastfetch, in the WinUI 3 style of Windows 11.",
        "cli_demo": "use sample data",
        "cli_theme": "theme: auto, light or dark",
        "cli_accent": "accent color: logo, system or #RRGGBB",
        "cli_expand": "expand the specifications at startup",
        "cli_backdrop": "window background: acrylic (default) or solid",
        "cli_wallpaper": "image to blur for the acrylic (default: desktop wallpaper)",
        "cli_fastfetch": "path to the fastfetch executable",
        "cli_lang": "interface language for this session: auto, fr or en",
    },
}
LANG = "fr"


def system_language():
    """'fr' si la langue d'affichage du système est le français, sinon 'en'.
    'fr' if the system display language is French, otherwise 'en'."""
    try:
        if os.name == "nt":
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return "fr" if (lcid & 0x3FF) == 0x0C else "en"  # LANG_FRENCH
        for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
            if os.environ.get(var):
                return "fr" if os.environ[var].lower().startswith("fr") else "en"
        code = locale.getlocale()[0] or ""
        return "fr" if code.lower().startswith("fr") else "en"
    except Exception:
        return "en"


def set_language(choice):
    global LANG
    LANG = system_language() if choice in (None, "auto") else ("fr" if choice == "fr" else "en")


def tr(key, **kw):
    s = STRINGS[LANG].get(key, STRINGS["fr"].get(key, key))
    return s.format(**kw) if kw and isinstance(s, str) else s


SETTINGS = Settings()
set_language(SETTINGS["language"])

# ════════════════════════════════════════════════════════════════════════════
#  Couleurs
#  Colors
# ════════════════════════════════════════════════════════════════════════════

def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb2hex(r, g, b):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(c)))) for c in (r, g, b))


def mix(a, b, t):
    ra, rb = hex2rgb(a), hex2rgb(b)
    return rgb2hex(*(x + (y - x) * t for x, y in zip(ra, rb)))


def luminance(h):
    r, g, b = (c / 255 for c in hex2rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def to_hls(h):
    return colorsys.rgb_to_hls(*(c / 255 for c in hex2rgb(h)))


def from_hls(h, l, s):
    l, s = max(0.0, min(1.0, l)), max(0.0, min(1.0, s))
    return rgb2hex(*(c * 255 for c in colorsys.hls_to_rgb(h % 1.0, l, s)))


# Palette « Campbell » de Windows Terminal pour les 16 couleurs ANSI.
# Windows Terminal's “Campbell” palette for the 16 ANSI colors.
ANSI_BASIC = ["#0C0C0C", "#C50F1F", "#13A10E", "#C19C00", "#0037DA", "#881798", "#3A96DD", "#CCCCCC"]
ANSI_BRIGHT = ["#767676", "#E74856", "#16C60C", "#F9F1A5", "#3B78FF", "#B4009E", "#61D6D6", "#F2F2F2"]


def xterm256(n):
    if n < 8:
        return ANSI_BASIC[n]
    if n < 16:
        return ANSI_BRIGHT[n - 8]
    if n < 232:
        n -= 16
        steps = [0, 95, 135, 175, 215, 255]
        return rgb2hex(steps[n // 36], steps[(n // 6) % 6], steps[n % 6])
    v = 8 + (n - 232) * 10
    return rgb2hex(v, v, v)


# ════════════════════════════════════════════════════════════════════════════
#  Analyse des séquences ANSI (logo coloré de Fastfetch)
#  ANSI sequence parsing (Fastfetch's colored logo)
# ════════════════════════════════════════════════════════════════════════════

OSC_RE = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
CSI_RE = re.compile(r"\x1b\[([0-9;?]*)([ -/]*[@-~])")


def strip_ansi(s):
    return CSI_RE.sub("", OSC_RE.sub("", s))


def parse_ansi(text):
    """Découpe une sortie ANSI en lignes de segments (texte, couleur|None, gras).
    Splits ANSI output into lines of segments (text, color|None, bold)."""
    text = OSC_RE.sub("", text).replace("\r", "").expandtabs(4)
    lines = [[]]
    state = {"fg": None, "bold": False}

    def emit(chunk):
        for i, part in enumerate(chunk.split("\n")):
            if i:
                lines.append([])
            if part:
                lines[-1].append((part, state["fg"], state["bold"]))

    pos = 0
    for m in CSI_RE.finditer(text):
        emit(text[pos:m.start()])
        pos = m.end()
        if m.group(2) != "m":
            continue
        params = [int(p) if p.isdigit() else 0 for p in m.group(1).split(";")] if m.group(1) else [0]
        i = 0
        while i < len(params):
            p = params[i]
            if p == 0:
                state["fg"], state["bold"] = None, False
            elif p == 1:
                state["bold"] = True
            elif p == 22:
                state["bold"] = False
            elif 30 <= p <= 37:
                state["fg"] = ANSI_BASIC[p - 30]
            elif 90 <= p <= 97:
                state["fg"] = ANSI_BRIGHT[p - 90]
            elif p == 39:
                state["fg"] = None
            elif p == 38 and i + 1 < len(params):
                if params[i + 1] == 5 and i + 2 < len(params):
                    state["fg"] = xterm256(params[i + 2])
                    i += 2
                elif params[i + 1] == 2 and i + 4 < len(params):
                    state["fg"] = rgb2hex(*params[i + 2:i + 5])
                    i += 4
            elif p == 48 and i + 1 < len(params):  # couleurs de fond : ignorées
                                                   # background colors: ignored
                i += 2 if params[i + 1] == 5 else 4
            i += 1
    emit(text[pos:])

    def blank(line):
        return not "".join(s[0] for s in line).strip()

    while lines and blank(lines[-1]):
        lines.pop()
    while lines and blank(lines[0]):
        lines.pop(0)
    return lines


# ════════════════════════════════════════════════════════════════════════════
#  Mise en forme (selon la langue)
#  Formatting (depending on the language)
# ════════════════════════════════════════════════════════════════════════════

def fmt_num(x, d=1):
    s = f"{x:,.{d}f}"
    return s.replace(",", " ").replace(".", ",") if LANG == "fr" else s


def fmt_bytes(n):
    units = tr("units")
    v, i = float(n), 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    if i == 0 or abs(v - round(v)) < 0.05:
        return f"{fmt_num(round(v), 0)} {units[i]}"
    return f"{fmt_num(v, 1 if v >= 10 else 2)} {units[i]}"


def join_list(items):
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f" {tr('and')} " + items[-1]


def fmt_uptime(ms):
    s = int(ms // 1000)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m = s // 60
    parts = []
    if d:
        parts.append(f"{d} {tr('days') if d > 1 else tr('day')}")
    if h:
        parts.append(f"{h} {tr('hours') if h > 1 else tr('hour')}")
    if (m and d < 2) or not parts:
        parts.append(f"{m} {tr('minutes') if m > 1 else tr('minute')}")
    return join_list(parts)


KEY_FR = {
    "OS": "Système", "Host": "Modèle", "Kernel": "Noyau", "Uptime": "Temps de fonctionnement",
    "Packages": "Paquets", "Shell": "Shell", "Display": "Écran", "DE": "Environnement de bureau",
    "WM": "Gestionnaire de fenêtres", "WM Theme": "Thème du gestionnaire", "Theme": "Thème",
    "Icons": "Icônes", "Font": "Police", "Cursor": "Curseur", "Terminal": "Terminal",
    "Terminal Font": "Police du terminal", "CPU": "Processeur", "GPU": "Carte graphique",
    "Memory": "Mémoire", "Physical Memory": "Mémoire physique", "Swap": "Mémoire d'échange",
    "Disk": "Disque", "Physical Disk": "Disque physique", "Local IP": "IP locale",
    "Public IP": "IP publique", "Battery": "Batterie", "Power Adapter": "Alimentation",
    "Locale": "Langue", "Board": "Carte mère", "BIOS": "BIOS", "Bios": "BIOS",
    "Chassis": "Châssis", "Bootmgr": "Gestionnaire de démarrage", "Media": "Média",
    "Player": "Lecteur", "Wifi": "Wi-Fi", "Sound": "Son", "Camera": "Caméra",
    "Gamepad": "Manette", "Bluetooth": "Bluetooth", "Processes": "Processus",
    "Users": "Utilisateurs", "Date & Time": "Date et heure", "Brightness": "Luminosité",
    "Monitor": "Moniteur", "Weather": "Météo", "Editor": "Éditeur", "Init System": "Système d'init",
    "Login Manager": "Gestionnaire de session", "Loadavg": "Charge moyenne", "Version": "Version",
}
# Fastfetch nomme ses rubriques en anglais ; on en détaille quelques abréviations.
# Fastfetch names its sections in English; a few abbreviations are spelled out.
KEY_EN = {"OS": "Operating system", "DE": "Desktop environment", "WM": "Window manager",
          "WM Theme": "Window manager theme", "CPU": "Processor", "GPU": "Graphics", "Host": "Model",
          "Bios": "BIOS", "Loadavg": "Load average"}
GAUGE_KEYS = ("Memory", "Swap", "Disk", "Battery", "Physical Memory")
# Clés triées une fois pour toutes, de la plus longue à la plus courte (« WM Theme » avant « WM »).
# Keys sorted once and for all, longest first (“WM Theme” before “WM”).
KEY_TABLES = {lang: (t, sorted(t, key=len, reverse=True)) for lang, t in (("fr", KEY_FR), ("en", KEY_EN))}


def translate_key(k):
    table, order = KEY_TABLES[LANG]
    for orig in order:
        if k == orig or k.startswith(orig + " "):
            return table[orig] + k[len(orig):]
    return k


VERSION_RE = re.compile(r"(\d+\.\d+(?:\.\d+)?)")


def extract_version(text):
    """Premier numéro de version trouvé dans `text` (« fastfetch 2.70.0 (x86_64) » → « 2.70.0 »).
    First version number found in `text` (“fastfetch 2.70.0 (x86_64)” → “2.70.0”)."""
    m = VERSION_RE.search(text or "")
    return m.group(1) if m else ""


# ════════════════════════════════════════════════════════════════════════════
#  Collecte des données Fastfetch
#  Fastfetch data collection
# ════════════════════════════════════════════════════════════════════════════

class FFData:
    def __init__(self):
        self.version = ""
        self.modules = {}
        self.rows = []
        self.title = ""
        self.logo = []
        self.errors = []
        self.demo = False
        self.when = datetime.datetime.now()


def find_fastfetch(custom=None):
    if custom:
        return custom if (os.path.isfile(custom) or shutil.which(custom)) else None
    exe = shutil.which("fastfetch")
    if exe:
        return exe
    if os.name == "nt":
        cands = [r"%LOCALAPPDATA%\Microsoft\WinGet\Links\fastfetch.exe",
                 r"%USERPROFILE%\scoop\shims\fastfetch.exe",
                 r"%ProgramData%\chocolatey\bin\fastfetch.exe",
                 r"%ProgramFiles%\fastfetch\fastfetch.exe"]
        cands = [os.path.expandvars(c) for c in cands]
    else:
        cands = ["/opt/homebrew/bin/fastfetch", "/usr/local/bin/fastfetch", "/usr/bin/fastfetch",
                 os.path.expanduser("~/.local/bin/fastfetch")]
    return next((c for c in cands if os.path.isfile(c)), None)


def run_ff(exe, args, timeout=25):
    p = subprocess.run([exe] + list(args), stdin=subprocess.DEVNULL, capture_output=True,
                       timeout=timeout, **NO_WINDOW)
    out = p.stdout.decode("utf-8", errors="replace")
    if p.returncode != 0 and not out.strip():
        err = p.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(err or tr("exit_code", code=p.returncode))
    return out


def parse_rows(txt):
    title, rows = "", []
    for ln in strip_ansi(txt).replace("\r", "").split("\n"):
        s = ln.strip()
        if not s or set(s) <= set("-─═"):
            continue
        if ": " in s:
            k, v = s.split(": ", 1)
            rows.append((k.strip(), v.strip()))
        elif not rows and not title and "@" in s:
            title = s
    return title, rows


def own_pids():
    """PID de FastVer : le processus Python et, dans l'exe ou l'AppImage, le lanceur PyInstaller qui l'a créé.
    FastVer's PIDs: the Python process and, in the exe or the AppImage, the PyInstaller launcher that started it."""
    pids = {os.getpid()}
    if FROZEN:
        try:
            pids.add(os.getppid())
        except (AttributeError, OSError):
            pass
    return pids


def login_shell():
    """Shell de connexion de l'utilisateur (Linux, macOS) avec sa version, ex. « bash 5.2.21 », ou None.
    The user's login shell (Linux, macOS) with its version, e.g. “bash 5.2.21”, or None."""
    if os.name == "nt":
        return None
    path = os.environ.get("SHELL") or ""
    if not path:
        try:
            import pwd
            path = pwd.getpwuid(os.getuid()).pw_shell
        except (ImportError, KeyError, OSError):
            return None
    name = os.path.basename(path)
    if not name or name in ("nologin", "false"):
        return None
    try:
        out = subprocess.run([path, "--version"], stdin=subprocess.DEVNULL, capture_output=True,
                             timeout=3).stdout.decode("utf-8", "replace")
        m = re.search(r"\d+(?:\.\d+)+", out)
    except (OSError, subprocess.SubprocessError):
        m = None
    return f"{name} {m.group(0)}" if m else name


def fix_self_detection(d):
    """Fastfetch prend pour shell (ou pour terminal) le premier processus parent qu'il trouve : lancé par FastVer,
    c'est FastVer lui-même (« FastVer », « python3 »…). Ces lignes sont corrigées : le shell devient le shell de
    connexion de l'utilisateur (Linux, macOS), sinon la ligne est retirée ; le terminal est retiré.
    Fastfetch takes the first parent process it finds for the shell (or the terminal): launched by FastVer, that is
    FastVer itself (“FastVer”, “python3”…). These rows are fixed: the shell becomes the user's login shell
    (Linux, macOS), otherwise the row is removed; the terminal is removed."""
    mine = own_pids()
    names = {os.path.basename(p).lower() for p in (sys.executable, APP_PATH or "", APPIMAGE or "") if p}

    def is_self(mod):
        r = d.modules.get(mod)
        if not isinstance(r, dict):
            return False
        if r.get("pid") in mine:
            return True
        exe = os.path.basename(str(r.get("exePath") or r.get("exe") or "")).lower()
        return bool(exe) and exe in names

    rows = []
    for k, v in d.rows:
        if k == "Shell" and is_self("shell"):
            sh = login_shell()
            if not sh:
                continue
            v = sh
            d.modules["shell"] = dict(d.modules["shell"], prettyName=sh, pid=None)
        elif k == "Terminal" and is_self("terminal"):
            continue
        rows.append((k, v))
    d.rows = rows


def load_fastfetch(exe):
    d = FFData()
    with ThreadPoolExecutor(4) as ex:
        f_ver = ex.submit(run_ff, exe, ["--version"])
        f_json = ex.submit(run_ff, exe, ["--format", "json", "--logo", "none", "-s", JSON_STRUCTURE])
        f_txt = ex.submit(run_ff, exe, ["--logo", "none", "--pipe", "true"])
        f_logo = ex.submit(run_ff, exe, ["--logo-position", "top", "-s", "break", "--pipe", "false"])

        try:
            d.version = extract_version(f_ver.result())
        except Exception as e:
            d.errors.append(f"version : {e}")
        try:
            for mod in json.loads(f_json.result()):
                if isinstance(mod, dict) and "result" in mod:
                    d.modules[str(mod.get("type", "")).lower()] = mod["result"]
        except Exception as e:
            d.errors.append(f"JSON : {e}")
        try:
            d.title, d.rows = parse_rows(f_txt.result())
        except Exception as e:
            d.errors.append(f"texte : {e}")
        try:
            raw = f_logo.result()
        except Exception:  # anciennes versions : pas de --logo-position
                           # old versions: no --logo-position
            try:
                raw = run_ff(exe, ["-s", "break", "--pipe", "false"])
            except Exception as e:
                raw = ""
                d.errors.append(f"logo : {e}")
        if "\x1bP" in raw or "\x1b_G" in raw:  # logo image (sixel / kitty) → logo ASCII intégré
                                               # image logo (sixel / kitty) → built-in ASCII logo
            try:
                raw = run_ff(exe, ["--logo-type", "builtin", "--logo-position", "top", "-s", "break",
                                   "--pipe", "false"])
            except Exception:
                raw = ""
        d.logo = parse_ansi(raw)

    if not d.rows and not d.modules:
        raise RuntimeError(tr("ff_no_data") + "\n" + "\n".join(d.errors))
    fix_self_detection(d)
    if not d.title:
        t = d.modules.get("title") or {}
        if t.get("userName") and t.get("hostName"):
            d.title = f"{t['userName']}@{t['hostName']}"
    return d


def demo_data():
    def sgr(h):
        return "\x1b[38;2;%d;%d;%dm" % hex2rgb(h)

    tiles = [("#1E90FF", "#41A6FF"), ("#0067C0", "#1C84DC")]
    logo = []
    for half, (a, b) in enumerate(tiles):
        logo += [f"{sgr(a)}{'█' * 10}  {sgr(b)}{'█' * 10}\x1b[0m"] * 5
        if half == 0:
            logo.append("")

    d = FFData()
    d.demo = True
    d.version = "2.70.0"
    d.title = "demo@PC-DEMO"
    d.logo = parse_ansi("\n".join(logo))
    gib = 1024 ** 3
    d.modules = {
        "title": {"userName": "demo", "fullUserName": tr("demo_user"), "hostName": "PC-DEMO"},
        "os": {"name": "Windows", "prettyName": "Windows 11 Pro", "id": "windows", "version": "24H2"},
        "host": {"name": "MS-7D75", "vendor": "Micro-Star International Co., Ltd."},
        "kernel": {"name": "WIN32_NT", "release": "10.0.26100.2033", "version": "24H2", "architecture": "x86_64"},
        "uptime": {"uptime": (2 * 86400 + 4 * 3600 + 17 * 60) * 1000},
        "packages": {"all": 160},
        "de": {"prettyName": "Fluent"},
        "cpu": {"cpu": "AMD Ryzen 7 7800X3D", "cores": {"physical": 8, "logical": 16}},
        "gpu": [{"name": "NVIDIA GeForce RTX 4070 SUPER", "type": "Discrete"}],
        "memory": {"total": int(31.15 * gib), "used": int(12.41 * gib)},
        "disk": [{"mountpoint": "C:\\", "bytes": {"total": int(931.51 * gib), "free": int(319.13 * gib)}},
                 {"mountpoint": "D:\\", "bytes": {"total": int(1863 * gib), "free": int(112 * gib)}}],
    }
    d.rows = [
        ("OS", "Windows 11 Pro x86_64"),
        ("Host", "MS-7D75 (Micro-Star International Co., Ltd.)"),
        ("Kernel", "WIN32_NT 10.0.26100.2033 (24H2)"),
        ("Uptime", "2 days, 4 hours, 17 mins"),
        ("Packages", "112 (scoop), 48 (winget)"),
        ("Shell", "PowerShell 7.4.6"),
        ("Display (LG ULTRAGEAR)", "2560x1440 @ 165 Hz in 27\" [External] *"),
        ("DE", "Fluent"),
        ("WM", "Desktop Window Manager 10.0.26100.1"),
        ("WM Theme", "Custom - Blue (System: Dark, Apps: Dark)"),
        ("Font", "Segoe UI (12pt) [Caption / Menu / Message / Status]"),
        ("Cursor", "Windows Default (32px)"),
        ("Terminal", "Windows Terminal 1.21.2911.0"),
        ("Terminal Font", "Cascadia Mono (12pt)"),
        ("CPU", "AMD Ryzen 7 7800X3D (16) @ 5.05 GHz"),
        ("GPU", "NVIDIA GeForce RTX 4070 SUPER (11.72 GiB) [Discrete]"),
        ("Memory", "12.41 GiB / 31.15 GiB (40%)"),
        ("Swap", "1.02 GiB / 4.75 GiB (21%)"),
        ("Disk (C:\\)", "612.38 GiB / 931.51 GiB (66%) - NTFS"),
        ("Disk (D:\\)", "1.71 TiB / 1.82 TiB (94%) - NTFS"),
        ("Local IP (Ethernet)", "192.168.1.42/24"),
        ("Locale", "fr-FR"),
    ]
    return d


# ════════════════════════════════════════════════════════════════════════════
#  Lecture des réglages système (thème, couleur d'accent)
#  Reading system settings (theme, accent color)
# ════════════════════════════════════════════════════════════════════════════

def command_output(cmd, timeout=2):
    """Sortie texte d'une commande, ou "" si elle est absente, échoue ou dépasse le délai.
    Text output of a command, or "" if it's missing, fails or times out."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=timeout,
                              stdin=subprocess.DEVNULL, **NO_WINDOW).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def gsettings(schema, key):
    """Valeur d'un réglage GNOME, sans les guillemets (« 'zoom' » → « zoom »).
    Value of a GNOME setting, without the quotes (“'zoom'” → “zoom”)."""
    return command_output(["gsettings", "get", schema, key]).strip("'")


def system_is_dark():
    try:
        if os.name == "nt":
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
                return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
        if sys.platform == "darwin":
            return "dark" in command_output(["defaults", "read", "-g", "AppleInterfaceStyle"]).lower()
        return any("dark" in gsettings("org.gnome.desktop.interface", key).lower()
                   for key in ("color-scheme", "gtk-theme"))
    except Exception:
        pass
    return False


def system_accent():
    if os.name != "nt":
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM") as k:
            v = winreg.QueryValueEx(k, "AccentColor")[0]  # format ABGR
                                                          # ABGR format
        return rgb2hex(v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF)
    except Exception:
        return None



# ════════════════════════════════════════════════════════════════════════════
#  Mises à jour (Fastfetch et FastVer) — sans Qt, appelées depuis un fil d'arrière-plan
#  Updates (Fastfetch and FastVer) — without Qt, called from a background thread
# ════════════════════════════════════════════════════════════════════════════

WINGET_NO_UPDATE = 0x8A15002B  # winget : « aucune mise à jour applicable »
                               # winget: “no applicable update”


class UpdateError(Exception):
    pass


class NoRelease(UpdateError):
    pass


def parse_version(s):
    """(nombres de la version, rang de préversion) : « 1.2.0-rc1 » < « 1.2.0 » < « 1.2.1 ».
    (version numbers, pre-release rank): “1.2.0-rc1” < “1.2.0” < “1.2.1”."""
    m = re.search(r"\d+(?:\.\d+){0,3}", s or "")
    if not m:
        return ()
    nums = tuple(int(n) for n in m.group(0).split("."))
    rest = (s[m.end():] or "").strip().lstrip("-+._ ").lower()
    if not rest or rest.startswith(("final", "release", "stable")) or rest[0] == "(":
        return nums, (1,)              # version finale / final release
    pre = re.match(r"(dev|a|alpha|b|beta|pre|preview|rc|c)\.?(\d*)", rest)
    if not pre:
        return nums, (1,)              # suffixe inconnu (« x86_64 »…) : traité comme final
                                       # unknown suffix (“x86_64”…): treated as final
    order = {"dev": 0, "a": 1, "alpha": 1, "b": 2, "beta": 2, "pre": 3, "preview": 3, "c": 4, "rc": 4}
    return nums, (0, order[pre.group(1)], int(pre.group(2) or 0))


def is_newer(a, b):
    """Vrai si la version a est strictement plus récente que b.
    True if version a is strictly newer than b."""
    va, vb = parse_version(a), parse_version(b)
    if not va or not vb:
        return False
    n = max(len(va[0]), len(vb[0]))
    pad = lambda v: v[0] + (0,) * (n - len(v[0]))
    return (pad(va), va[1]) > (pad(vb), vb[1])


def _open_url(url, accept, timeout, extra_headers=None):
    local_test = GITHUB_API.startswith("http://127.0.0.1") and url.startswith("http://127.0.0.1")
    if not (url.startswith("https://") or local_test):
        raise UpdateError(f"URL refusée : {url}")
    headers = {"Accept": accept, "User-Agent": f"{APP_NAME}/{APP_VERSION}"}
    headers.update(extra_headers or {})
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout)


def _http_error(e, url):
    if e.code == 404:
        return NoRelease(url)
    if e.code == 429 or (e.code == 403 and (e.headers or {}).get("X-RateLimit-Remaining") == "0"):
        return UpdateError(tr("rate_limited"))
    return UpdateError(f"HTTP {e.code}")


def _fetch(url, accept, timeout, limit, extra_headers=None):
    """GET `url` → (contenu, en-têtes), ou (None, en-têtes) si GitHub répond « 304 Non modifiée ».
    GET `url` → (body, headers), or (None, headers) when GitHub replies “304 Not Modified”."""
    try:
        with _open_url(url, accept, timeout, extra_headers) as r:
            data, headers = r.read(limit + 1), r.headers
    except urllib.error.HTTPError as e:
        if e.code == 304 and extra_headers:
            return None, e.headers
        raise _http_error(e, url) from e
    except (urllib.error.URLError, OSError) as e:
        raise UpdateError(tr("net_error", err=getattr(e, "reason", e))) from e
    if len(data) > limit:
        raise UpdateError("réponse trop volumineuse")
    return data, headers


def http_get(url, accept="application/vnd.github+json", timeout=20, limit=8 * 1024 * 1024):
    return _fetch(url, accept, timeout, limit)[0]


def _cache_path():
    return os.path.join(config_dir(), "github_cache.json")


def github_json(url):
    """Requête à l'API GitHub avec cache ETag : une réponse « 304 Non modifiée » ne compte pas dans la
    limite de 60 requêtes par heure, ce qui permet de vérifier à chaque démarrage sans l'atteindre.
    GitHub API request with an ETag cache: a “304 Not Modified” reply doesn't count against the
    60-requests-per-hour limit, so checking at every startup doesn't hit it."""
    try:
        with open(_cache_path(), encoding="utf-8") as f:
            cache = json.load(f)
        if not isinstance(cache, dict):
            cache = {}
    except Exception:
        cache = {}
    entry = cache.get(url) if isinstance(cache.get(url), dict) else None
    extra = {"If-None-Match": entry["etag"]} if entry and entry.get("etag") and "body" in entry else None
    body, headers = _fetch(url, "application/vnd.github+json", 20, 8 * 1024 * 1024, extra)
    if body is None:
        return entry["body"]     # inchangé depuis la dernière fois / unchanged since last time
    data = json.loads(body.decode("utf-8"))
    etag = headers.get("ETag")
    if etag:
        cache[url] = {"etag": etag, "body": data}
        try:
            os.makedirs(config_dir(), exist_ok=True)
            tmp = _cache_path() + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(cache, f)
            os.replace(tmp, _cache_path())
        except OSError as e:
            write_log(f"Cache GitHub non enregistré : {e!r}")
    return data


def latest_release(repo):
    rel = github_json(f"{GITHUB_API}/repos/{repo}/releases/latest")
    if not isinstance(rel, dict):
        raise UpdateError("réponse GitHub inattendue")
    return rel


def _last_line(text):
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    return lines[-1][:200] if lines else ""


# ── Fastfetch ─────────────────────────────────────────────────────────────

def ff_local_version(exe):
    try:
        return extract_version(run_ff(exe, ["--version"]))
    except Exception:
        return ""


def winget_exe():
    """winget est un alias d'application Windows que shutil.which ne trouve pas toujours.
    winget is a Windows app alias that shutil.which doesn't always find."""
    found = shutil.which("winget")
    if found or os.name != "nt":
        return found
    alias = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe")
    return alias if os.path.lexists(alias) else None


def ff_install_method(exe):
    """Comment Fastfetch a été installé, d'après son emplacement : winget, scoop, choco, brew, system, manual.
    How Fastfetch was installed, based on its location: winget, scoop, choco, brew, system, manual."""
    p = os.path.realpath(exe).replace("\\", "/").lower()
    if os.name == "nt":
        if "/winget/" in p:
            return "winget"
        if "/scoop/" in p:
            return "scoop"
        if "chocolatey" in p:
            return "choco"
        winget = winget_exe()
        if winget:
            try:
                out = subprocess.run([winget, "list", "--id", FF_WINGET_ID, "-e", "--accept-source-agreements"],
                                     capture_output=True, text=True, errors="replace", timeout=60,
                                     stdin=subprocess.DEVNULL, **NO_WINDOW)
                if out.returncode == 0 and FF_WINGET_ID.lower() in out.stdout.lower():
                    return "winget"
            except Exception:
                pass
        return "manual"
    if any(k in p for k in ("/homebrew/", "/cellar/", "linuxbrew")):
        return "brew"
    if p.startswith(("/usr/", "/bin/", "/nix/", "/run/current-system/", "/snap/")):
        return "system"
    return "manual"


FF_UPDATE_ARGS = {
    "winget": ["upgrade", "--id", FF_WINGET_ID, "-e", "--silent",
               "--accept-source-agreements", "--accept-package-agreements"],
    "scoop": ["update", "fastfetch"],
    "choco": ["upgrade", "fastfetch", "-y"],
    "brew": ["upgrade", "fastfetch"],
}


def ff_update_command(method):
    if method not in FF_UPDATE_ARGS:
        return None
    tool = winget_exe() if method == "winget" else shutil.which(method)
    return [tool] + FF_UPDATE_ARGS[method] if tool else None


def system_update_hint():
    """Commande à lancer soi-même quand Fastfetch vient d'un paquet système (il faut les droits admin).
    Command to run yourself when Fastfetch comes from a system package (admin rights required)."""
    for tool, cmd in (("apt", "sudo apt install --only-upgrade fastfetch"), ("pacman", "sudo pacman -S fastfetch"),
                      ("dnf", "sudo dnf upgrade fastfetch"), ("zypper", "sudo zypper update fastfetch"),
                      ("apk", "sudo apk upgrade fastfetch"), ("xbps-install", "sudo xbps-install -Su fastfetch"),
                      ("emerge", "sudo emerge -u app-misc/fastfetch")):
        if shutil.which(tool):
            return cmd
    return None


def ff_check(exe):
    rel = latest_release(FF_REPO)
    info = dict(latest=str(rel.get("tag_name", "")).lstrip("vV"),
                url=rel.get("html_url") or FASTFETCH_URL + "/releases/latest",
                local=ff_local_version(exe) if exe else "", method=None, action=None, hint=None)
    info["action"] = "page"
    if exe:
        info["method"] = ff_install_method(exe)
        hint = system_update_hint() if info["method"] == "system" else None
        if ff_update_command(info["method"]):
            info["action"] = "update"
        elif hint:
            info["action"], info["hint"] = "hint", hint
    return info


def ff_update(exe, method, latest=None):
    cmd = ff_update_command(method)
    if not cmd:
        raise UpdateError(tr("no_command"))
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=900,
                           stdin=subprocess.DEVNULL, **NO_WINDOW)
    except subprocess.TimeoutExpired:
        raise UpdateError(tr("exit_code", code="timeout"))
    out = (p.stdout or "") + (p.stderr or "")
    write_log("Mise à jour de Fastfetch : " + " ".join(cmd) + f"\ncode {p.returncode}\n" + out[-4000:])
    if p.returncode != 0 and (p.returncode & 0xFFFFFFFF) != WINGET_NO_UPDATE:
        raise UpdateError(_last_line(out) or tr("exit_code", code=p.returncode))
    local = ff_local_version(exe)
    # winget, Scoop… publient souvent une nouvelle version quelques jours après GitHub : la commande
    # réussit alors sans rien installer. On le signale au lieu d'annoncer une mise à jour qui n'a pas eu lieu.
    # winget, Scoop… often publish a new version a few days after GitHub: the command then succeeds
    # without installing anything. Report it instead of announcing an update that didn't happen.
    if latest and local and is_newer(latest, local):
        raise UpdateError(tr("ff_not_yet", tool=tr(f"method_{method}"), latest=latest, local=local))
    return local


# ── FastVer ───────────────────────────────────────────────────────────────

SHA_RE = re.compile(r"\b([0-9a-fA-F]{64})\b")
SUMS_FILES = ("sha256sums", "sha256sums.txt", "checksums.txt", "checksums.sha256")


def release_sha256(rel, name):
    """Empreinte SHA-256 publiée pour l'asset `name` de la release, ou None si aucune n'est publiée.

    Trois sources sont lues : le fichier « <asset>.sha256 » joint par le workflow de compilation, un fichier
    d'empreintes groupées (SHA256SUMS…) et l'empreinte que GitHub calcule lui-même pour chaque asset.
    Si deux sources se contredisent, l'asset a été remplacé après sa publication : on refuse.

    SHA-256 checksum published for the release's `name` asset, or None if none is published.

    Three sources are read: the “<asset>.sha256” file attached by the build workflow, a grouped checksum
    file (SHA256SUMS…) and the checksum GitHub computes itself for every asset.
    If two sources contradict each other, the asset was replaced after publication: refuse.
    """
    assets = {str(a.get("name", "")).lower(): a for a in rel.get("assets") or [] if isinstance(a, dict)}
    found = set()
    side = assets.get(name.lower() + ".sha256")
    if side and side.get("browser_download_url"):
        m = SHA_RE.search(http_get(side["browser_download_url"], accept="application/octet-stream",
                                   limit=4096).decode("ascii", "replace"))
        if m:
            found.add(m.group(1).lower())
    for sums in SUMS_FILES:
        a = assets.get(sums)
        if a and a.get("browser_download_url"):
            text = http_get(a["browser_download_url"], accept="application/octet-stream",
                            limit=64 * 1024).decode("utf-8", "replace")
            for line in text.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[-1].lstrip("*").lower() == name.lower() and SHA_RE.fullmatch(parts[0]):
                    found.add(parts[0].lower())
            break
    digest = str((assets.get(name.lower()) or {}).get("digest") or "")
    if digest.lower().startswith("sha256:") and SHA_RE.fullmatch(digest[7:]):
        found.add(digest[7:].lower())
    if len(found) > 1:
        raise UpdateError(tr("checksum_conflict", name=name))
    return found.pop() if found else None


def app_check():
    try:
        rel = latest_release(UPDATE_REPO)
    except NoRelease:
        return dict(latest=None, url=None, action=None, sha256=None)
    tag = str(rel.get("tag_name", ""))
    page = rel.get("html_url") or f"https://github.com/{UPDATE_REPO}/releases/latest"
    asset = next((a.get("browser_download_url") for a in rel.get("assets") or []
                  if APP_ASSET and str(a.get("name", "")).lower() == APP_ASSET.lower()), None)
    sha = release_sha256(rel, APP_ASSET) if asset else None   # APP_ASSET None (« frozen ») → page
                                                              # APP_ASSET None (“frozen”) → page
    if not asset or not sha:
        # Sans le fichier attendu ou sans empreinte pour le vérifier, aucune installation automatique :
        # on propose seulement d'ouvrir la page de la version.
        # Without the expected file, or without a checksum to verify it, no automatic install:
        # only offer to open the release page.
        return dict(latest=tag.lstrip("vV"), url=page, action="page", sha256=None, no_checksum=bool(asset))
    return dict(latest=tag.lstrip("vV"), url=asset, action="update", sha256=sha, no_checksum=False)


def _download_verified(url, sha256, limit):
    """Télécharge `url` et vérifie son empreinte SHA-256 avant de l'utiliser.
    Downloads `url` and checks its SHA-256 checksum before using it."""
    if not sha256 or not SHA_RE.fullmatch(sha256):
        raise UpdateError(tr("bad_checksum"))
    data = http_get(url, accept="application/octet-stream", timeout=120, limit=limit)
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), sha256.lower()):
        write_log(f"Empreinte refusée pour {url} : attendu {sha256}, obtenu {hashlib.sha256(data).hexdigest()}")
        raise UpdateError(tr("bad_checksum"))
    return data


def _looks_genuine(data):
    """Contrôle de forme en plus de l'empreinte : un vrai FastVer.exe commence par « MZ » et porte le nom du
    produit dans ses infos de version (UTF-16) ; une AppImage est un exécutable ELF marqué « AI\\x02 ».
    Shape check on top of the checksum: a genuine FastVer.exe starts with “MZ” and carries the product name in
    its version info (UTF-16); an AppImage is an ELF executable marked “AI\\x02”."""
    if len(data) < 5 * 1024 * 1024:
        return False
    if PACKAGE == "exe":
        return data[:2] == b"MZ" and "FastVer".encode("utf-16-le") in data
    return data[:4] == b"\x7fELF" and data[8:11] == b"AI\x02"


def app_install_binary(url, sha256):
    """Remplace FastVer.exe ou l'AppImage. Un programme en cours d'exécution ne peut pas être écrasé, mais il
    peut être renommé (Windows comme Linux) : l'ancien fichier devient la copie de sauvegarde.
    Replaces FastVer.exe or the AppImage. A running program can't be overwritten, but it can be renamed
    (on Windows as on Linux): the old file becomes the backup copy."""
    data = _download_verified(url, sha256, 300 * 1024 * 1024)
    if not _looks_genuine(data):
        raise UpdateError(tr("bad_download"))
    target = APP_PATH
    backup = os.path.join(os.path.dirname(target), BACKUP_NAME.format(v=APP_VERSION))
    new = target + ".new"
    try:
        with open(new, "wb") as f:
            f.write(data)
        if os.name != "nt":
            os.chmod(new, 0o755)   # l'AppImage doit rester exécutable / the AppImage must stay executable
    except OSError as e:
        raise UpdateError(tr("write_error", path=new, err=e))
    try:
        os.replace(target, backup)   # renommer l'exe en cours d'exécution est autorisé
                                     # renaming the running exe is allowed
    except OSError as e:
        _silent_remove(new)
        raise UpdateError(tr("write_error", path=target, err=e))
    try:
        os.replace(new, target)
    except OSError as e:
        # Le nouvel exe n'a pas pu prendre la place : on remet l'ancien, pour ne jamais rester sans FastVer.
        # The new exe couldn't take its place: put the old one back, so FastVer is never left missing.
        try:
            os.replace(backup, target)
        except OSError as e2:
            write_log(f"Restauration impossible de {backup} vers {target} : {e2!r}")
        _silent_remove(new)
        raise UpdateError(tr("write_error", path=target, err=e))
    write_log(f"{os.path.basename(target)} mis à jour : {APP_VERSION} → nouvelle version, SHA-256 {sha256} "
              f"(copie de l'ancienne : {backup})")
    return None


def _silent_remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


def app_install(url, sha256):
    """Télécharge la nouvelle version, vérifie son empreinte, garde une copie de l'actuelle puis la remplace.
    Downloads the new version, checks its checksum, keeps a copy of the current one, then replaces it."""
    if PACKAGE in ("exe", "appimage"):
        return app_install_binary(url, sha256)
    if PACKAGE != "script":
        raise UpdateError(tr("no_command"))
    try:
        text = _download_verified(url, sha256, 8 * 1024 * 1024).decode("utf-8")
    except UnicodeDecodeError:
        raise UpdateError(tr("bad_download"))
    m = re.search(r'^APP_VERSION = "([^"]+)"', text, re.M)
    if 'APP_NAME = "FastVer"' not in text or not m:
        raise UpdateError(tr("bad_download"))
    try:
        compile(text, "fastver.py", "exec")
    except (SyntaxError, ValueError):
        raise UpdateError(tr("bad_download"))
    target = APP_PATH
    backup = os.path.join(os.path.dirname(target), BACKUP_NAME.format(v=APP_VERSION))
    tmp = target + ".new"
    try:
        shutil.copy2(target, backup)
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp, target)
    except OSError as e:
        _silent_remove(tmp)
        raise UpdateError(tr("write_error", path=target, err=e))
    write_log(f"FastVer mis à jour : {APP_VERSION} → {m.group(1)}, SHA-256 {sha256} "
              f"(copie de l'ancienne version : {backup})")
    return m.group(1)


def list_backups():
    """Copies gardées après les mises à jour, à côté du programme (jamais d'autres fichiers).
    Copies kept after updates, next to the program (never any other files)."""
    if not BACKUP_NAME:
        return []
    pattern = os.path.join(os.path.dirname(APP_PATH), BACKUP_NAME.format(v="*"))
    return sorted(p for p in glob.glob(pattern)
                  if os.path.isfile(p) and os.path.abspath(p) != APP_PATH)


def delete_backups(paths):
    done = 0
    for p in paths:
        try:
            os.remove(p)
            done += 1
        except OSError as e:
            write_log(f"Copie non supprimée ({p}) : {e!r}")
    return done


# ════════════════════════════════════════════════════════════════════════════
#  Préparation des informations à afficher
#  Preparing the information to display
# ════════════════════════════════════════════════════════════════════════════

def row_value(data, key):
    for k, v in data.rows:
        if k == key:
            return v
    return ""


ARCH_RE = re.compile(r"\s+(x86_64|x86|amd64|x64|aarch64|arm64|armv7l|i[3-6]86|riscv64)$", re.I)


def os_info(data):
    m = data.modules
    o, k, ti = m.get("os") or {}, m.get("kernel") or {}, m.get("title") or {}
    pretty = ARCH_RE.sub("", o.get("prettyName") or o.get("name") or row_value(data, "OS")
                         or platform.system()).strip()
    name = (o.get("name") or pretty.split(" ")[0]).strip()
    if pretty.startswith(name) and pretty != name:
        first, rest = name, pretty[len(name):].strip()
    else:
        parts = pretty.split(" ", 1)
        first, rest = parts[0], (parts[1] if len(parts) > 1 else "")
    os_id = (o.get("id") or name).lower()
    is_win = "windows" in os_id or "win32" in (k.get("name") or "").lower()
    is_mac = "mac" in os_id or "darwin" in (k.get("name") or "").lower()

    if is_win:
        full = "Microsoft Windows"
    elif is_mac:
        full = "Apple macOS"
    elif k.get("name") == "Linux" and "linux" not in name.lower() and "android" not in os_id:
        full = f"{name} GNU/Linux"
    else:
        full = name

    ver = o.get("versionID") or o.get("version") or ""
    if is_win:
        pool = " ".join(str(x) for x in (o.get("version"), o.get("prettyName"), k.get("version"),
                                          k.get("displayVersion"), row_value(data, "Kernel")) if x)
        mm = re.search(r"\b\d\d[Hh]\d\b", pool)
        ver = mm.group(0).upper() if mm else ver
        rel = (k.get("release") or "").split(".")
        build = ".".join(rel[2:]) if len(rel) >= 3 else (k.get("release") or "")
        line2 = tr("version_build", ver=ver, build=build) if ver else tr("build_only", build=build)
    else:
        kern = " ".join(x for x in (k.get("name"), k.get("release")) if x) or row_value(data, "Kernel")
        line2 = tr("version_kernel", ver=ver, kern=kern) if ver else tr("kernel_only", kern=kern)

    user = ti.get("userName") or (data.title.split("@")[0] if "@" in data.title else "") or getpass.getuser()
    owner = ti.get("fullUserName") or user
    host = ti.get("hostName") or (data.title.split("@", 1)[1] if "@" in data.title else platform.node())
    tags = [str(o.get("codename") or "").strip().title(), k.get("architecture") or platform.machine()]
    return dict(pretty=pretty, first=first, rest=rest, full=full, line2=line2, owner=owner,
                user=user, host=host, tags=[t for t in tags if t])


def spec_rows(data, inf):
    rows = []
    if inf["host"]:
        rows.append((tr("device_name"), "", inf["host"], None))
    up = (data.modules.get("uptime") or {}).get("uptime")
    for k, v in data.rows:
        pct = None
        base = k.split(" (")[0]
        if base == "Uptime":
            v = fmt_uptime(up) if up else v if LANG != "fr" else re.sub(
                r"\b(days?|hours?|mins?|secs?)\b",
                lambda mm: {"day": "jour", "days": "jours", "hour": "heure", "hours": "heures",
                            "min": "min", "mins": "min", "sec": "s", "secs": "s"}[mm.group(1)], v)
        if base in GAUGE_KEYS:
            mm = re.search(r"(\d{1,3}(?:[.,]\d+)?)\s?%", v)
            if mm:
                pct = min(100.0, float(mm.group(1).replace(",", ".")))
        rows.append((translate_key(k), k, v, pct))
    if data.version:
        rows.append(("Fastfetch", "", tr("version", v=data.version), None))
    return rows


def logo_accent(data):
    """Couleur dominante (saturée) du logo, pour teinter toute l'interface.
    Dominant (saturated) logo color, used to tint the whole interface."""
    weights = {}
    for line in (data.logo if data else []):
        for txt, fg, _ in line:
            if not fg:
                continue
            h, l, s = to_hls(fg)
            if s >= 0.3 and 0.08 < luminance(fg) < 0.95:
                weights[fg] = weights.get(fg, 0) + len(txt.strip())
    return max(weights, key=weights.get) if weights else None


def tame_accent(base):
    """Ramène l'accent dans la plage de luminosité des couleurs d'accent Windows.
    Brings the accent into the brightness range of Windows accent colors."""
    h, l, s = to_hls(base)
    return from_hls(h, min(max(l, 0.36), 0.48), max(s, 0.6))


# ════════════════════════════════════════════════════════════════════════════
#  Interface WinUI 3 (Fluent Design) — PySide6 + QFluentWidgets
#  WinUI 3 interface (Fluent Design) — PySide6 + QFluentWidgets
# ════════════════════════════════════════════════════════════════════════════

PIP_PACKAGE = "PySide6-Fluent-Widgets"


def _fix_streams():
    """Évite les plantages d'affichage : pythonw (pas de console) ou console non UTF-8.
    Prevents output crashes: pythonw (no console) or a non-UTF-8 console."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name)
        if stream is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
        else:
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def tk_message(title, message, ask=False):
    """Boîte de dialogue de secours (Tkinter, fourni avec Python sous Windows).
    Fallback dialog box (Tkinter, bundled with Python on Windows)."""
    if os.name == "nt":
        # Sous Windows, la boîte native suffit (et FastVer.exe n'embarque pas Tkinter).
        # On Windows the native box is enough (and FastVer.exe doesn't bundle Tkinter).
        try:
            flags = 0x24 if ask else 0x10  # MB_YESNO | MB_ICONQUESTION, ou MB_ICONERROR
                                           # MB_YESNO | MB_ICONQUESTION, or MB_ICONERROR
            return ctypes.windll.user32.MessageBoxW(None, str(message), str(title), flags | 0x10000) == 6  # IDYES
        except Exception:
            pass
    if "PySide6.QtWidgets" in sys.modules:
        # Qt déjà chargé (cas de l'AppImage, qui n'embarque pas Tkinter) : boîte de dialogue Qt.
        # Qt already loaded (the AppImage's case, which doesn't bundle Tkinter): Qt dialog box.
        try:
            qtw = sys.modules["PySide6.QtWidgets"]
            if qtw.QApplication.instance() is None:
                tk_message.app = qtw.QApplication([])   # gardée en vie le temps de la boîte / kept alive for the box
            box = qtw.QMessageBox
            if ask:
                return box.question(None, str(title), str(message)) == box.StandardButton.Yes
            box.critical(None, str(title), str(message))
            return False
        except Exception:
            pass
    try:
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        res = (messagebox.askyesno if ask else messagebox.showerror)(title, message, parent=root)
        root.destroy()
        return res
    except Exception:
        print(f"{title}\n{message}", file=sys.stderr)
        return False


def fatal_error(exc_text):
    write_log(exc_text)
    tail = "\n".join(exc_text.strip().splitlines()[-6:])
    tk_message(tr("fatal_title"), tr("fatal_msg", tail=tail, log=LOG_PATH))


REPAIR_FLAG = "--repair-deps"
WAIT_ENV = "FASTVER_WAIT_PID"   # PID de l'instance précédente à attendre (redémarrage après mise à jour)
                                # PID of the previous instance to wait for (restart after an update)


def console_python():
    """python.exe plutôt que pythonw.exe : pip a besoin d'une vraie console.
    python.exe rather than pythonw.exe: pip needs a real console."""
    py = sys.executable
    if py.lower().endswith("pythonw.exe"):
        alt = py[:-len("pythonw.exe")] + "python.exe"
        if os.path.isfile(alt):
            return alt
    return py


def offer_repair(err):
    """Qt n'a pas pu être chargé : propose la réparation, puis quitte AVANT d'appeler pip.

    Une tentative d'import de PySide6 peut laisser Qt6Core.dll chargée dans ce processus ;
    Windows la verrouille alors, et pip échoue avec « [WinError 5] Accès refusé ».
    La réparation tourne donc dans un nouveau processus, une fois celui-ci fermé.

    Qt couldn't be loaded: offers the repair, then quits BEFORE calling pip.

    An attempt to import PySide6 can leave Qt6Core.dll loaded in this process;
    Windows then locks it, and pip fails with “[WinError 5] Access is denied”.
    The repair therefore runs in a new process, once this one has closed.
    """
    write_log(f"Import de l'interface impossible : {err!r}")
    if not tk_message(tr("deps_title"), tr("deps_msg", err=err), ask=True):
        sys.exit(1)
    args = [a for a in sys.argv[1:] if a != REPAIR_FLAG]
    subprocess.Popen([console_python(), os.path.abspath(__file__), REPAIR_FLAG, str(os.getpid())] + args,
                     close_fds=True, **NO_WINDOW)
    sys.exit(0)


def _wait_for_exit(pid, timeout=15.0):
    """Attend la fin du processus FastVer précédent (pour libérer ses DLL).
    Waits for the previous FastVer process to end (to release its DLLs)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if os.name == "nt":
                h = ctypes.windll.kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
                if not h:
                    return
                ctypes.windll.kernel32.WaitForSingleObject(h, int((deadline - time.time()) * 1000))
                ctypes.windll.kernel32.CloseHandle(h)
                return
            os.kill(pid, 0)
        except (OSError, ValueError):
            return
        time.sleep(0.2)


def run_repair(argv):
    """Mode réparation : n'importe jamais Qt, installe les paquets puis relance FastVer.
    Repair mode: never imports Qt, installs the packages, then restarts FastVer."""
    import tkinter  # mode réparation : Qt n'est jamais chargé, l'import tardif est sans risque
                    # repair mode: Qt is never loaded, so a late import is safe
    from tkinter import messagebox, ttk

    rest = list(argv)
    if rest and rest[0].isdigit():
        _wait_for_exit(int(rest.pop(0)))

    # Paquet déjà présent mais inutilisable → installation abîmée : on force la réinstallation.
    # Package already present but unusable → broken install: force a reinstall.
    broken = any(importlib.util.find_spec(m) is not None
                 for m in ("PySide6", "qfluentwidgets", "qframelesswindow"))
    cmd = [console_python(), "-m", "pip", "install", "--disable-pip-version-check"]
    if sys.prefix == sys.base_prefix:  # hors environnement virtuel
                                       # outside a virtual environment
        cmd.append("--user")
        # Python « géré par le système » (Debian, Ubuntu, Fedora…) : pip refuse d'installer sans cette option,
        # même avec --user. Elle n'agit que dans le dossier de l'utilisateur.
        # “Externally managed” Python (Debian, Ubuntu, Fedora…): pip refuses to install without this option,
        # even with --user. It only affects the user's own folder.
        if os.path.isfile(os.path.join(sysconfig.get_path("stdlib") or "", "EXTERNALLY-MANAGED")):
            cmd.append("--break-system-packages")
    if broken:
        cmd.append("--force-reinstall")
    cmd.append(PIP_PACKAGE)

    while True:
        root = tkinter.Tk()
        root.title("FastVer")
        root.resizable(False, False)
        msg = tr("deps_repairing") if broken else tr("deps_installing")
        ttk.Label(root, text=msg, padding=(24, 20, 24, 8)).pack()
        bar = ttk.Progressbar(root, mode="indeterminate", length=320)
        bar.pack(padx=24, pady=(0, 24))
        bar.start(12)
        root.update_idletasks()
        root.geometry(f"+{(root.winfo_screenwidth() - root.winfo_reqwidth()) // 2}"
                      f"+{(root.winfo_screenheight() - root.winfo_reqheight()) // 3}")
        result = {}

        def work():
            write_log("Commande : " + " ".join(cmd))
            p = subprocess.run(cmd, capture_output=True, text=True, errors="replace", **NO_WINDOW)
            result.update(code=p.returncode, out=(p.stdout or "") + (p.stderr or ""))
            root.after(0, root.destroy)

        threading.Thread(target=work, daemon=True).start()
        root.mainloop()
        out = result.get("out", "")
        write_log(out)
        if result.get("code") == 0:
            break

        tail = "\n".join(out.strip().splitlines()[-4:])
        locked = "WinError 5" in out or "Accès refusé" in out or "Access is denied" in out
        hint = tr("deps_locked") if locked else tr("deps_net", ver=platform.python_version())
        r = tkinter.Tk()
        r.withdraw()
        again = messagebox.askretrycancel(tr("deps_fail_title"),
                                          tr("deps_fail_msg", pkg=PIP_PACKAGE, tail=tail, hint=hint, log=LOG_PATH),
                                          parent=r)
        r.destroy()
        if not again:
            sys.exit(1)

    # Relance FastVer dans un processus neuf, qui chargera les modules fraîchement installés.
    # Restart FastVer in a fresh process, which will load the newly installed modules.
    subprocess.Popen([sys.executable, os.path.abspath(__file__)] + rest, close_fds=True)
    sys.exit(0)


_fix_streams()

if __name__ == "__main__" and not FROZEN and len(sys.argv) > 1 and sys.argv[1] == REPAIR_FLAG:
    run_repair(sys.argv[2:])  # ne revient jamais
                              # never returns

try:
    from PySide6.QtCore import QEvent, QLockFile, QPoint, QPointF, QRect, QRectF, Qt, QTimer, QUrl
    from PySide6.QtGui import (QBrush, QColor, QDesktopServices, QFont, QFontMetricsF, QGuiApplication,
                               QIcon, QImage, QKeySequence, QPainter, QPainterPath, QPixmap, QRadialGradient,
                               QShortcut)
    from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsBlurEffect, QGraphicsPixmapItem,
                                   QGraphicsScene, QGridLayout, QHBoxLayout, QLabel,
                                   QVBoxLayout, QWidget)
    from qfluentwidgets import (BodyLabel, CaptionLabel, ComboBox, ExpandGroupSettingCard, FluentIcon as FIF,
                                FluentTitleBar, IconWidget, IndeterminateProgressRing, IndicatorPosition,
                                InfoBar, InfoBarPosition, PrimaryPushButton, ProgressBar, PushButton,
                                SettingCard, SimpleCardWidget, SmoothScrollArea,
                                StrongBodyLabel, SubtitleLabel, SwitchButton, Theme, TitleLabel,
                                ToolTipFilter, TransparentToolButton, isDarkTheme, setTheme,
                                setThemeColor, themeColor)
    from shiboken6 import isValid
    from qframelesswindow import FramelessWindow
except Exception as _e:  # pragma: no cover — absent, DLL manquante, version incompatible…
                         # missing, DLL not found, incompatible version…
    if __name__ == "__main__" and not FROZEN:  # dans l'exe, Qt est toujours embarqué
                                               # inside the exe, Qt is always bundled
        offer_repair(_e)  # ne revient jamais
                          # never returns
    raise


UI_FAMILIES = ["Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Inter", "Cantarell", "Ubuntu",
               "Noto Sans", "DejaVu Sans"]
TITLE_FAMILIES = ["Cascadia Mono", "Cascadia Code", "Consolas", "DejaVu Sans Mono", "Menlo", "Courier New"]
# Police de l'intitulé de l'OS (« Windows 11 Pro ») : Cascadia Mono, avec repli sur d'autres polices à chasse fixe.
# Font of the OS heading (“Windows 11 Pro”): Cascadia Mono, falling back to other monospaced fonts.
MONO_FAMILIES = ["Cascadia Mono", "Cascadia Code", "Consolas", "JetBrains Mono", "Fira Code",
                 "DejaVu Sans Mono", "Menlo", "Liberation Mono", "Courier New"]


def qfont(families, px, weight=QFont.Weight.Normal):
    f = QFont()
    f.setFamilies(families)
    f.setPixelSize(int(px))
    f.setWeight(weight)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


def wallpaper_path():
    """Chemin du fond d'écran du bureau, ou None s'il est introuvable (couleur unie, etc.).
    Path of the desktop wallpaper, or None if it can't be found (solid color, etc.)."""
    try:
        if os.name == "nt":
            buf = ctypes.create_unicode_buffer(1024)
            if ctypes.windll.user32.SystemParametersInfoW(0x0073, 1024, buf, 0) and os.path.isfile(buf.value):
                return buf.value  # SPI_GETDESKWALLPAPER
            cached = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Themes\TranscodedWallpaper")
            return cached if os.path.isfile(cached) else None
        if sys.platform == "darwin":
            out = command_output(["osascript", "-e", 'tell application "System Events" to get picture '
                                  'of current desktop'], timeout=3)
            return out if os.path.isfile(out) else None
        # GNOME : image du thème en cours (sombre ou clair) d'abord.
        # GNOME: the current theme's image (dark or light) first.
        keys = ("picture-uri-dark", "picture-uri") if system_is_dark() else ("picture-uri", "picture-uri-dark")
        for key in keys:
            out = gsettings("org.gnome.desktop.background", key)
            if out.startswith("file://"):
                path = urllib.parse.unquote(out[7:])
                if os.path.isfile(path):
                    return path
        return kde_wallpaper()
    except Exception:
        pass
    return None


def kde_wallpaper():
    """Fond d'écran de KDE Plasma, lu dans sa configuration (un fichier image ou un paquet de fonds d'écran).
    KDE Plasma wallpaper, read from its configuration (an image file or a wallpaper package)."""
    cfg = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
                       "plasma-org.kde.plasma.desktop-appletsrc")
    try:
        with open(cfg, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return None
    for m in re.finditer(r"^Image=(.+)$", text, re.M):
        path = m.group(1).strip()
        if path.startswith("file://"):
            path = urllib.parse.unquote(path[7:])
        if os.path.isdir(path):   # paquet : contents/images/<largeur>x<hauteur>.png… → la plus grande image
                                  # package: contents/images/<width>x<height>.png… → the largest image
            images = glob.glob(os.path.join(path, "contents", "images", "*.*"))
            path = max(images, key=os.path.getsize, default="")
        if os.path.isfile(path):
            return path
    return None


def wallpaper_layout():
    """Disposition du fond d'écran : (« fill » | « fit » | « stretch » | « center » | « tile » | « span »,
    couleur de fond « #RRGGBB » ou None), pour flouter exactement ce que montre le bureau.
    Wallpaper layout: (“fill” | “fit” | “stretch” | “center” | “tile” | “span”,
    background color “#RRGGBB” or None), so the blur matches what the desktop shows."""
    style, color = "fill", None
    try:
        if os.name == "nt":
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as k:
                    ws = str(winreg.QueryValueEx(k, "WallpaperStyle")[0]).strip()
                    try:
                        tile = str(winreg.QueryValueEx(k, "TileWallpaper")[0]).strip()
                    except OSError:
                        tile = "0"
            except OSError:   # valeur absente : Windows remplit l'écran par défaut
                ws, tile = "10", "0"   # value missing: Windows fills the screen by default
            style = {"10": "fill", "6": "fit", "2": "stretch", "22": "span"}.get(
                ws, ("tile" if tile == "1" else "center") if ws == "0" else "fill")
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Colors") as k:
                    rgb = [int(v) for v in str(winreg.QueryValueEx(k, "Background")[0]).split()[:3]]
                color = rgb2hex(*rgb) if len(rgb) == 3 else None
            except (OSError, ValueError):
                pass
        elif sys.platform != "darwin" and shutil.which("gsettings"):
            style = {"zoom": "fill", "scaled": "fit", "stretched": "stretch", "centered": "center",
                     "wallpaper": "tile", "spanned": "span"}.get(
                gsettings("org.gnome.desktop.background", "picture-options"), "fill")
            c = gsettings("org.gnome.desktop.background", "primary-color")
            color = c if re.fullmatch(r"#[0-9a-fA-F]{6}", c) else None
    except Exception as e:
        write_log(f"Disposition du fond d'écran illisible : {e!r}")
    return style, color


class AcrylicMaterial:
    """Matériau acrylique façon WinUI, dessiné par FastVer lui-même.

    Recette : le fond d'écran (ou, à défaut, une capture du bureau prise avant l'ouverture)
    est flouté, en partie désaturé, recouvert d'une teinte claire ou sombre puis d'un grain fin.
    La fenêtre reste une fenêtre normale et opaque : aucun effet système n'est utilisé,
    donc pas de fenêtre transparente, noire ou qui rame quand on la déplace.

    WinUI-style acrylic material, drawn by FastVer itself.

    Recipe: the wallpaper (or, failing that, a desktop capture taken before opening)
    is blurred, partly desaturated, covered with a light or dark tint, then a fine grain.
    The window stays a normal, opaque window: no system effect is used,
    so no transparent or black window, and no lag when moving it.
    """

    LIGHT = ("#FCFCFC", 0.60)   # teinte et opacité en mode clair
              # tint and opacity in light mode
    DARK = ("#202020", 0.70)    # teinte et opacité en mode sombre
             # tint and opacity in dark mode
    SATURATION = 0.55           # part de la saturation d'origine conservée
                                # share of the original saturation kept
    BLUR_RADIUS = 28            # rayon du flou, en pixels de l'image réduite au quart
                                # blur radius, in pixels of the quarter-size image
    GRAIN = 7                   # opacité du grain (0-255)
                                # grain opacity (0-255)

    def __init__(self, wallpaper=None):
        self.cache, self.captures = {}, {}
        # Une image donnée avec --wallpaper remplit l'écran ; sinon, on reprend la disposition du bureau.
        # An image given with --wallpaper fills the screen; otherwise, use the desktop's layout.
        self.layout = ("fill", None) if wallpaper else wallpaper_layout()
        path = wallpaper or wallpaper_path()
        img = QImage(path) if path else QImage()
        self.wallpaper = None if img.isNull() else img
        if self.wallpaper is None:
            for scr in QGuiApplication.screens():  # avant l'affichage : FastVer n'est pas encore visible
                                                   # before showing: FastVer isn't visible yet
                shot = scr.grabWindow(0).toImage()
                if not shot.isNull():
                    self.captures[scr.name()] = shot
        self.source = path if self.wallpaper is not None else "capture"
        self.grain = self._grain_tile()

    def ok(self):
        return self.wallpaper is not None or bool(self.captures)

    def _grain_tile(self, n=96):
        # Pixels gris aléatoires (toujours les mêmes), construits d'un bloc plutôt que pixel par pixel.
        # Random grey pixels (always the same ones), built in one go rather than pixel by pixel.
        a = self.GRAIN
        buf = b"".join(bytes((v, v, v, a)) for v in random.Random(64).randbytes(n * n))  # BGRA
        tile = QImage(buf, n, n, n * 4, QImage.Format.Format_ARGB32).copy()  # copie : buf est temporaire
                                                                            # copy: buf is temporary
        return QPixmap.fromImage(tile)

    def _blur(self, img):
        w, h = max(1, img.width() // 4), max(1, img.height() // 4)
        small = img.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        r = self.BLUR_RADIUS
        m = r * 2
        canvas = QImage(w + 2 * m, h + 2 * m, QImage.Format.Format_ARGB32_Premultiplied)
        p = QPainter(canvas)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawImage(QRectF(0, 0, canvas.width(), canvas.height()), small)  # bords prolongés : pas de halo sombre
                                                                           # extended edges: no dark halo
        p.drawImage(m, m, small)
        p.end()
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(QPixmap.fromImage(canvas))
        effect = QGraphicsBlurEffect()
        effect.setBlurRadius(r)
        effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
        item.setGraphicsEffect(effect)
        scene.addItem(item)
        out = QImage(canvas.size(), QImage.Format.Format_ARGB32_Premultiplied)
        out.fill(Qt.GlobalColor.transparent)
        p = QPainter(out)
        scene.render(p, QRectF(out.rect()), QRectF(0, 0, canvas.width(), canvas.height()))
        p.end()
        return out.copy(m, m, w, h).scaled(img.width(), img.height(), Qt.AspectRatioMode.IgnoreAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)

    @staticmethod
    def _place(src, W, H, style, color):
        """L'image telle que le bureau la dispose sur un écran de W × H pixels physiques.
        The image as the desktop lays it out on a W × H physical-pixel screen."""
        out = QImage(W, H, QImage.Format.Format_RGB32)
        out.fill(QColor(color or "#000000"))
        smooth = Qt.TransformationMode.SmoothTransformation
        p = QPainter(out)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if style == "tile":
            p.fillRect(out.rect(), QBrush(QPixmap.fromImage(src)))
        elif style == "center":
            p.drawImage((W - src.width()) // 2, (H - src.height()) // 2, src)
        elif style == "stretch":
            p.drawImage(0, 0, src.scaled(W, H, Qt.AspectRatioMode.IgnoreAspectRatio, smooth))
        elif style == "fit":
            img = src.scaled(W, H, Qt.AspectRatioMode.KeepAspectRatio, smooth)
            p.drawImage((W - img.width()) // 2, (H - img.height()) // 2, img)
        else:  # fill
            img = src.scaled(W, H, Qt.AspectRatioMode.KeepAspectRatioByExpanding, smooth)
            p.drawImage(0, 0, img, (img.width() - W) // 2, (img.height() - H) // 2, W, H)
        p.end()
        return out

    def _desktop_image(self, screen, W, H):
        style, color = self.layout
        if style != "span":
            return self._place(self.wallpaper, W, H, style, color)
        # « Étendre » : une seule image couvre tous les écrans ; on en découpe la part de cet écran.
        # “Span”: a single image covers every screen; cut out this screen's share.
        dpr = screen.devicePixelRatio()
        virt = screen.virtualGeometry()
        full = self._place(self.wallpaper, max(1, round(virt.width() * dpr)), max(1, round(virt.height() * dpr)),
                           "fill", color)
        geo = screen.geometry()
        return full.copy(round((geo.x() - virt.x()) * dpr), round((geo.y() - virt.y()) * dpr), W, H)

    def pixmap(self, screen, dark):
        """Matériau pour tout l'écran `screen` (mis en cache par écran et par thème).
        Material for the whole `screen` (cached per screen and per theme)."""
        geo, dpr = screen.geometry(), screen.devicePixelRatio()
        key = (screen.name(), geo.width(), geo.height(), dpr, dark)
        if key in self.cache:
            return self.cache[key]
        W, H = max(1, round(geo.width() * dpr)), max(1, round(geo.height() * dpr))
        if self.wallpaper is None:
            src = self.captures.get(screen.name()) or next(iter(self.captures.values()))
            img = self._place(src, W, H, "fill", None)
        else:
            img = self._desktop_image(screen, W, H)
        blurred = self._blur(img)

        out = QImage(W, H, QImage.Format.Format_RGB32)
        p = QPainter(out)
        p.drawImage(0, 0, blurred)
        p.setOpacity(1.0 - self.SATURATION)
        p.drawImage(0, 0, blurred.convertToFormat(QImage.Format.Format_Grayscale8))
        p.setOpacity(1.0)
        color, alpha = self.DARK if dark else self.LIGHT
        tint = QColor(color)
        tint.setAlphaF(alpha)
        p.fillRect(out.rect(), tint)
        p.fillRect(out.rect(), QBrush(self.grain))
        p.end()
        pm = QPixmap.fromImage(out)
        self.cache[key] = pm
        return pm


def text_color(alpha=1.0):
    c = QColor(255, 255, 255) if isDarkTheme() else QColor(0, 0, 0)
    c.setAlphaF(alpha * (1.0 if isDarkTheme() else 0.9))
    return c


class LogoWidget(QWidget):
    """Logo ASCII coloré de Fastfetch, posé sur un halo teinté par l'accent.
    Fastfetch's colored ASCII logo, on a halo tinted with the accent color."""

    BOX_W, BOX_H = 180, 160

    def __init__(self, lines, parent=None):
        super().__init__(parent)
        self.rows = len(lines)
        self.cols = max((sum(len(s[0]) for s in ln) for ln in lines), default=0)
        size = min(self.BOX_H / max(1, self.rows * 1.2), self.BOX_W / max(1, self.cols * 0.6), 15)
        self.font_ = QFont()
        self.font_.setFamilies(MONO_FAMILIES)
        self.font_.setStyleHint(QFont.StyleHint.Monospace)
        self.font_.setPixelSize(max(5, int(size)))
        self.bold_ = QFont(self.font_)
        self.bold_.setBold(True)
        fm = QFontMetricsF(self.font_)
        self.cw, self.lh, self.ascent = fm.horizontalAdvance("M"), fm.height(), fm.ascent()
        self.logo_w, self.logo_h = self.cols * self.cw, self.rows * self.lh
        pad = 18
        self.setFixedSize(int(self.logo_w + pad * 2), int(self.logo_h + pad * 2))
        self.pad = pad
        self.phase, self.fade = 0.0, 0.0
        # Découpage du logo calculé une seule fois : (colonne, longueur, bloc « █▀▄ » ou texte, couleur, gras).
        # Logo split computed only once: (column, length, “█▀▄” block or text, color, bold).
        self.pieces = []
        for li, ln in enumerate(lines):
            col = 0
            for txt, fg, bold in ln:
                for piece in re.findall(r"█+|▀+|▄+|[^█▀▄]+", txt):
                    if piece[0] in "█▀▄" or piece.strip():
                        self.pieces.append((li, col, piece, fg, bold))
                    col += len(piece)
        self._colors = {}   # (couleur Fastfetch, sombre) → couleur affichée / (Fastfetch color, dark) → shown color
        self.timer = QTimer(self, interval=16, timeout=self._tick)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tr("click_me"))
        self.installEventFilter(ToolTipFilter(self, 400))

    # Petit easter egg : une vague arc-en-ciel traverse le logo.
    # Little easter egg: a rainbow wave sweeps across the logo.
    def mousePressEvent(self, e):
        if not self.timer.isActive():
            self.frame = 0
            self.timer.start()

    def _tick(self):
        self.frame += 1
        total = 75
        self.phase = self.frame / total * 1.5
        self.fade = min(1.0, self.frame / 12, (total - self.frame) / 12)
        if self.frame >= total:
            self.timer.stop()
            self.fade = 0.0
        self.update()

    @staticmethod
    def _base_color(fg, dark):
        """Couleur lisible sur le thème : un blanc sur fond clair est assombri, un noir sur fond sombre éclairci.
        Color readable on the theme: white on a light background is darkened, black on a dark one lightened."""
        if not fg:
            return "#FFFFFF" if dark else "#1A1A1A"
        lum = luminance(fg)
        if not dark and lum > 0.75:
            return mix(fg, "#1A1A1A", 0.6)
        if dark and lum < 0.12:
            return mix(fg, "#FFFFFF", 0.55)
        return fg

    def color_for(self, fg, xpos, dark):
        key = (fg, dark)
        if key not in self._colors:
            self._colors[key] = self._base_color(fg, dark)
        base = self._colors[key]
        if self.fade <= 0:
            return QColor(base)
        h, _, _ = to_hls(base)
        wave = from_hls(h + self.phase + xpos * 0.6, 0.66 if dark else 0.45, 0.85)
        return QColor(mix(base, wave, self.fade))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        # Halo
        c = QPointF(self.width() / 2, self.height() / 2)
        g = QRadialGradient(c, max(self.width(), self.height()) / 2)
        acc = QColor(themeColor())
        acc.setAlphaF(0.20 if isDarkTheme() else 0.13)
        g.setColorAt(0.0, acc)
        acc.setAlphaF(0.0)
        g.setColorAt(1.0, acc)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawEllipse(self.rect())
        # Logo
        dark, cols, half = isDarkTheme(), max(1, self.cols), self.lh / 2
        for li, col, piece, fg, bold in self.pieces:
            x, y = self.pad + col * self.cw, self.pad + li * self.lh
            color = self.color_for(fg, col / cols, dark)
            block = piece[0]
            if block in "█▀▄":
                y1, h = (y, self.lh) if block == "█" else (y, half) if block == "▀" else (y + half, half)
                p.fillRect(QRectF(x, y1, len(piece) * self.cw + 0.5, h + 0.5), color)
            else:
                p.setFont(self.bold_ if bold else self.font_)
                p.setPen(color)
                p.drawText(QPointF(x, y + self.ascent), piece)


def argb(c):
    """Couleur Qt au format « #AARRGGBB » des feuilles de style.
    Qt color in the style sheets' “#AARRGGBB” format."""
    return c.name(QColor.NameFormat.HexArgb)


class Tag(QLabel):
    """Pastille d'information discrète (architecture, nom de code, version…).
    Discreet information pill (architecture, codename, version…)."""

    def __init__(self, text, parent=None, accent=False):
        super().__init__(text, parent)
        self.accent = accent
        self.setFont(qfont(UI_FAMILIES, 12))
        self.setContentsMargins(9, 2, 9, 3)
        self.restyle()

    def restyle(self):
        if self.accent:
            c = QColor(themeColor())
            bg = QColor(c)
            bg.setAlphaF(0.16 if isDarkTheme() else 0.10)
            fg = c.lighter(150) if isDarkTheme() else c
            border = QColor(c)
            border.setAlphaF(0.35)
        else:
            bg = text_color(0.06)
            fg = text_color(0.72)
            border = text_color(0.08)
        self.setStyleSheet(f"QLabel{{background:{argb(bg)};color:{argb(fg)};border:1px solid {argb(border)};"
                           f"border-radius:11px;}}")


class SpecRow(QWidget):
    """Ligne de la liste des spécifications : clic = copie, survol = surlignage.
    Row of the specifications list: click = copy, hover = highlight."""

    def __init__(self, key, value, pct, gauge_kind, on_copy, parent=None):
        super().__init__(parent)
        self.key, self.value, self.on_copy, self.hover = key, value, on_copy, False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        grid = QGridLayout(self)
        grid.setContentsMargins(56, 11, 52, 11)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)
        grid.setColumnMinimumWidth(0, 160)
        grid.setColumnStretch(1, 1)
        k = CaptionLabel(key, self)
        k.setWordWrap(True)
        k.setTextColor(QColor(0, 0, 0, 155), QColor(255, 255, 255, 170))
        k.setFont(qfont(UI_FAMILIES, 14))
        k.setFixedWidth(160)
        v = BodyLabel(value, self)
        v.setWordWrap(True)
        v.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        grid.addWidget(k, 0, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(v, 0, 1, Qt.AlignmentFlag.AlignTop)
        if pct is not None:
            bar = ProgressBar(self, useAni=False)
            bar.setFixedWidth(220)
            bar.setValue(int(round(pct)))
            if gauge_kind == "battery":
                level = "error" if pct < 15 else ("pause" if pct < 30 else None)
            else:
                level = "error" if pct >= 90 else ("pause" if pct >= 75 else None)
            if level:
                getattr(bar, level)()
            grid.addWidget(bar, 1, 1, Qt.AlignmentFlag.AlignLeft)
        self.copy_icon = IconWidget(FIF.COPY, self)
        self.copy_icon.setFixedSize(14, 14)
        self.copy_icon.hide()

    def resizeEvent(self, e):
        self.copy_icon.move(self.width() - 34, (min(self.height(), 44) - 14) // 2)

    def enterEvent(self, e):
        self.hover = True
        self.copy_icon.show()
        self.update()

    def leaveEvent(self, e):
        self.hover = False
        self.copy_icon.hide()
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.on_copy(self.value, tr("copied_row", key=self.key))

    def paintEvent(self, e):
        if self.hover:
            p = QPainter(self)
            p.fillRect(self.rect(), text_color(0.035))


class Footer(QFrame):
    """Barre de commandes du bas, comme le pied d'un ContentDialog WinUI.
    Bottom command bar, like the footer of a WinUI ContentDialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.hbox = QHBoxLayout(self)
        self.hbox.setContentsMargins(24, 0, 24, 0)
        self.hbox.setSpacing(8)

    def paintEvent(self, e):
        p = QPainter(self)
        translucent = self.window().backdrop != "solid"
        if isDarkTheme():
            bg, line = QColor(32, 32, 32, 150 if translucent else 200), QColor(255, 255, 255, 18)
        else:
            bg, line = QColor(243, 243, 243, 130 if translucent else 200), QColor(0, 0, 0, 15)
        p.fillRect(self.rect(), bg)
        p.fillRect(0, 0, self.width(), 1, line)


def restart_app():
    """Relance FastVer (pour charger une nouvelle version), puis ferme celle-ci.
    Restarts FastVer (to load a new version), then closes this one."""
    cmd = ([APP_PATH] if FROZEN else [sys.executable, APP_PATH]) + sys.argv[1:]   # exe, AppImage ou script
                                                                                  # exe, AppImage or script
    env = dict(os.environ)
    # Sans cette variable, l'exe relancé réutiliserait le dossier temporaire de celui-ci (l'ancienne
    # version), supprimé dès sa fermeture : la nouvelle version planterait au démarrage.
    # Without this variable, the restarted exe would reuse this one's temporary folder (the old
    # version), deleted as soon as it closes: the new version would crash at startup.
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    env[WAIT_ENV] = str(os.getpid())  # la nouvelle instance attend la fin de celle-ci (instance unique)
                                      # the new instance waits for this one to end (single instance)
    subprocess.Popen(cmd, close_fds=True, env=env)
    QApplication.quit()


class FastVerWindow(FramelessWindow):
    WIDTH = 620
    # Qt (via FramelessWindow) envoie des évènements pendant super().__init__() : ces valeurs
    # doivent donc exister avant que notre propre __init__ ne s'exécute.
    # Qt (via FramelessWindow) sends events during super().__init__(): these values
    # must therefore exist before our own __init__ runs.
    backdrop, material = "solid", None
    card = content = footer = None
    page = "main"
    _fit_pending = False

    def __init__(self, args):
        super().__init__()
        self.args = args
        self.data, self.error, self.expanded = None, None, args.expand
        self._executor = ThreadPoolExecutor(1)       # lecture de Fastfetch
                                                     # reading Fastfetch
        self._bg = ThreadPoolExecutor(2)             # mises à jour
                                                     # updates
        self._future, self._centered, self._auto_started = None, False, False
        self.ff_exe = None   # chemin de Fastfetch, relu à chaque actualisation / Fastfetch path, re-read on refresh
        self.upd = {"fastfetch": {"state": "idle"}, "app": {"state": "idle"}}
        self.ui = {}
        self.backdrop, self.material = args.backdrop or "acrylic", None
        if self.backdrop == "acrylic":
            try:  # à créer AVANT l'affichage (capture du bureau en secours)
                  # must be created BEFORE showing (desktop capture as a fallback)
                self.material = AcrylicMaterial(args.wallpaper)
                if not self.material.ok():
                    raise RuntimeError("ni fond d'écran ni capture disponible")
                write_log(f"Acrylique : source = {self.material.source}")
            except Exception as e:
                write_log(f"Acrylique indisponible, fond uni : {e!r}")
                self.backdrop, self.material = "solid", None

        if args.theme == "dark":
            self.theme = Theme.DARK
        elif args.theme == "light":
            self.theme = Theme.LIGHT
        else:
            self.theme = Theme.DARK if system_is_dark() else Theme.LIGHT
        setTheme(self.theme)

        self.setTitleBar(FluentTitleBar(self))
        self.titleBar.maxBtn.hide()
        self.titleBar.minBtn.hide()
        self.titleBar.setDoubleClickEnabled(False)
        self.titleBar.raise_()
        self.setResizeEnabled(False)
        self.setFixedWidth(self.WIDTH)
        self.setWindowTitle(tr("about_fastfetch"))

        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0, self.titleBar.height(), 0, 0)
        self.vbox.setSpacing(0)

        for keys, fn in (("Escape", self.on_escape), ("Return", self.on_escape), ("Enter", self.on_escape),
                         ("F5", self.refresh), ("Ctrl+Shift+C", self.copy_all),
                         ("D", self.toggle_specs), ("T", self.toggle_theme)):
            QShortcut(QKeySequence(keys), self, activated=fn)

        self.apply_theme()
        self.refresh()

    # ── Thème, accent, fond ───────────────────────────────────────────────
    # ── Theme, accent, background ─────────────────────────────────────────
    def apply_theme(self):
        choice = (self.args.accent or "logo").lower()
        base = None
        if choice == "system":
            base = system_accent()
        elif re.fullmatch(r"#[0-9a-f]{6}", choice):
            base = choice
        else:
            base = logo_accent(self.data) or system_accent()
        setThemeColor(QColor(tame_accent(base) if base else "#005FB8"))

        close = self.titleBar.closeBtn
        close.setNormalColor(QColor(255, 255, 255) if isDarkTheme() else QColor(0, 0, 0))
        close.setHoverColor(QColor(255, 255, 255))
        close.setPressedColor(QColor(255, 255, 255))
        self._set_icon()
        self.update()

    def _set_icon(self):
        pm = QPixmap(64, 64)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(themeColor())
        shades = [c, c.lighter(125), c.darker(115), c.lighter(110)]
        for i, (x, y) in enumerate([(4, 4), (34, 4), (4, 34), (34, 34)]):
            path = QPainterPath()
            path.addRoundedRect(QRectF(x, y, 26, 26), 3, 3)
            p.fillPath(path, shades[i])
        p.end()
        self.setWindowIcon(QIcon(pm))

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(32, 32, 32) if isDarkTheme() else QColor(243, 243, 243))
        if not self.material:
            return
        # Chaque écran que la fenêtre recouvre fournit sa part du matériau : rien ne déborde si la fenêtre
        # est à cheval sur deux écrans ou poussée en partie hors de l'écran.
        # Every screen the window overlaps supplies its share of the material: nothing spills over when the
        # window straddles two screens or is pushed partly off-screen.
        win = QRect(self.mapToGlobal(QPoint(0, 0)), self.size())
        for scr in QGuiApplication.screens():
            geo = scr.geometry()
            part = win.intersected(geo)
            if part.isEmpty():
                continue
            pm = self.material.pixmap(scr, isDarkTheme())
            dpr = scr.devicePixelRatio()
            src = QRectF((part.x() - geo.x()) * dpr, (part.y() - geo.y()) * dpr,
                         part.width() * dpr, part.height() * dpr)
            p.drawPixmap(QRectF(part.translated(-win.topLeft())), pm, src)

    def moveEvent(self, e):
        super().moveEvent(e)
        if self.material:
            self.update()  # le matériau suit la position de la fenêtre sur le fond d'écran
                           # the material follows the window's position on the wallpaper

    def toggle_theme(self):
        self.theme = Theme.LIGHT if isDarkTheme() else Theme.DARK
        setTheme(self.theme)
        self.apply_theme()
        if self.data or self.error or self.page == "settings":
            self.render()

    # ── Cycle de vie ──────────────────────────────────────────────────────
    # ── Lifecycle ─────────────────────────────────────────────────────────
    def closeEvent(self, e):
        self._executor.shutdown(wait=False)
        self._bg.shutdown(wait=False)
        super().closeEvent(e)

    def on_escape(self):
        if self.page == "settings":
            self.close_settings()
        else:
            self.close()

    def clear(self):
        while self.vbox.count():
            item = self.vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.card, self.ui = None, {}

    def refresh(self):
        if self._future and not self._future.done():
            return
        self.page = "main"
        self.show_loading()
        self.ff_exe = exe = find_fastfetch(self.args.fastfetch)
        if self.args.demo:
            self._future = self._executor.submit(demo_data)
        elif not exe:
            self.data, self.error = None, ("ff_missing", "")
            QTimer.singleShot(350, self._loaded)
            return
        else:
            self._future = self._executor.submit(load_fastfetch, exe)
        QTimer.singleShot(60, self._poll)

    def _poll(self):
        if not self._future.done():
            QTimer.singleShot(60, self._poll)
            return
        try:
            self.data, self.error = self._future.result(), None
        except Exception as e:
            self.data, self.error = None, ("ff_failed", str(e).strip() or e.__class__.__name__)
        self._loaded()

    def _loaded(self):
        self.apply_theme()  # l'accent dépend du logo
                            # the accent depends on the logo
        self.render()
        if not self._auto_started:
            self._auto_started = True
            QTimer.singleShot(1200, self.start_auto_updates)

    def render(self):
        self.clear()
        if self.page == "settings":
            self.build_settings()
        elif self.error and not self.data:
            self.show_error(*self.error)
        elif self.data:
            self.build()
        QTimer.singleShot(0, self.fit_height)

    # ── Taille et position ────────────────────────────────────────────────
    # ── Size and position ─────────────────────────────────────────────────
    def fit_height(self):
        if not self.content:
            return
        self._fit_pending = False
        try:
            hint = self.content.sizeHint().height()
            lay = self.content.layout()
            if lay is not None and lay.hasHeightForWidth():
                width = self.content.width() if self.content.width() > 100 else self.WIDTH
                hint = max(hint, lay.totalHeightForWidth(width))
        except RuntimeError:
            return
        screen = self.screen().availableGeometry()
        want = self.titleBar.height() + hint + (self.footer.height() if self.footer else 0)
        h = min(want, screen.height() - 24)
        if h != self.height():
            self.setFixedHeight(h)
        if not self._centered:
            self.move(screen.x() + (screen.width() - self.width()) // 2,
                      screen.y() + max(0, (screen.height() - h) // 3))
            self._centered = True
        elif self.y() + h > screen.bottom():
            self.move(self.x(), max(screen.y(), screen.bottom() - h))

    def eventFilter(self, obj, e):
        if e.type() == QEvent.Type.Resize and obj is self.card and not self._fit_pending:
            self._fit_pending = True
            QTimer.singleShot(0, self.fit_height)
        return super().eventFilter(obj, e)

    # ── Briques de mise en page ───────────────────────────────────────────
    # ── Layout building blocks ────────────────────────────────────────────
    def _scroll_page(self):
        scroll = SmoothScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none}")
        content = QWidget()
        content.setObjectName("content")
        content.setStyleSheet("#content{background:transparent}")
        scroll.setWidget(content)
        scroll.viewport().setStyleSheet("background:transparent")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(32, 8, 32, 28)
        lay.setSpacing(0)
        self.vbox.addWidget(scroll, 1)
        self.content = content
        return lay

    def _tool(self, icon, tip, fn, parent):
        b = TransparentToolButton(icon, parent)
        b.setToolTip(tip)
        b.installEventFilter(ToolTipFilter(b, 300))
        b.clicked.connect(fn)
        return b

    def _footer(self, status, buttons, tools=False):
        self.footer = Footer(self)
        hb = self.footer.hbox
        self.status = CaptionLabel(status, self.footer)
        self.status.setTextColor(QColor(0, 0, 0, 140), QColor(255, 255, 255, 140))
        hb.addWidget(self.status, 1)
        if tools:  # roue dentée juste à gauche du bouton de thème
                   # gear button just left of the theme button
            self.settings_btn = self._tool(FIF.SETTING, tr("settings_tip"), self.open_settings, self.footer)
            hb.addWidget(self.settings_btn)
            hb.addWidget(self._tool(FIF.CONSTRACT, tr("theme_tip"), self.toggle_theme, self.footer))
        for text, icon, fn, primary in buttons:
            b = (PrimaryPushButton if primary else PushButton)(text, self.footer)
            if icon:
                b.setIcon(icon)
            if primary:
                b.setMinimumWidth(120)
            b.clicked.connect(fn)
            hb.addWidget(b)
        self.vbox.addWidget(self.footer)

    @staticmethod
    def _icon(icon, size, parent):
        w = IconWidget(icon, parent)
        w.setFixedSize(size, size)
        return w

    def body(self, text, parent, secondary=False, size=14):
        lbl = BodyLabel(text, parent)
        lbl.setWordWrap(True)
        lbl.setFont(qfont(UI_FAMILIES, size))
        if secondary:
            lbl.setTextColor(QColor(0, 0, 0, 150), QColor(255, 255, 255, 160))
        return lbl

    # ── Écrans de chargement et d'erreur ──────────────────────────────────
    # ── Loading and error screens ─────────────────────────────────────────
    def show_loading(self):
        self.clear()
        self.footer = None
        page = QWidget(self)
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 64, 32, 96)
        lay.setSpacing(16)
        ring = IndeterminateProgressRing(page)
        ring.setFixedSize(48, 48)
        ring.setStrokeWidth(4)
        lay.addWidget(ring, 0, Qt.AlignmentFlag.AlignHCenter)
        t = SubtitleLabel("Fastfetch", page)
        lay.addWidget(t, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(self.body(tr("loading"), page, True), 0, Qt.AlignmentFlag.AlignHCenter)
        self.vbox.addWidget(page)
        self.content = page
        QTimer.singleShot(0, self.fit_height)

    def show_error(self, kind, detail):
        title, message = (tr("ff_missing_title"), tr("ff_missing_msg")) if kind == "ff_missing" else \
            (tr("ff_failed_title"), detail)
        self.setWindowTitle(APP_NAME)
        lay = self._scroll_page()
        lay.setContentsMargins(32, 16, 32, 32)
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(self._icon(FIF.INFO, 28, self.content), 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(SubtitleLabel(title, self.content))
        col.addWidget(self.body(message, self.content, True))
        row.addLayout(col, 1)
        lay.addLayout(row)
        self._footer("", [(tr("get_fastfetch"), FIF.LINK, lambda: QDesktopServices.openUrl(QUrl(FASTFETCH_URL)), False),
                          (tr("demo_mode"), FIF.PLAY, self._go_demo, False),
                          (tr("close"), None, self.close, True)], tools=True)

    def _go_demo(self):
        self.args.demo, self.error = True, None
        self.refresh()

    # ── Fenêtre principale ────────────────────────────────────────────────
    # ── Main window ───────────────────────────────────────────────────────
    def build(self):
        d = self.data
        inf = os_info(d)
        self.setWindowTitle(tr("about", name=inf["pretty"]))
        lay = self._scroll_page()
        c = self.content

        # Bandeau : logo + mot-symbole
        # Banner: logo + wordmark
        hero = QHBoxLayout()
        hero.setSpacing(20)
        hero.addStretch(1)
        logo = LogoWidget(d.logo, c) if d.logo else None
        if logo:
            hero.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)
        words = QVBoxLayout()
        words.setSpacing(10)
        words.addStretch(1)
        logo_w = logo.width() if logo else 0
        avail = self.WIDTH - 64 - logo_w - 20 - 8

        def wordmark_width(px):
            bold = QFontMetricsF(qfont(TITLE_FAMILIES, px, QFont.Weight.DemiBold))
            light = QFontMetricsF(qfont(TITLE_FAMILIES, px, QFont.Weight.Light))
            return bold.horizontalAdvance(inf["first"]) + light.horizontalAdvance(" " + inf["rest"])

        # Plus grande taille (34 → 20 px) qui tient sur une ligne ; sinon le nom passe sur deux lignes.
        # Largest size (34 → 20 px) that fits on one line; otherwise the name wraps onto two lines.
        size = next((px for px in range(34, 20, -1) if wordmark_width(px) <= avail), 20)
        split = wordmark_width(size) > avail
        fam = ",".join(f"'{f}'" for f in TITLE_FAMILIES)
        mark = QLabel(c)
        mark.setTextFormat(Qt.TextFormat.RichText)
        mark.setWordWrap(False)
        mark.setText(f"<span style=\"font-family:{fam}; font-size:{size}px; font-weight:600\">"
                     f"{html_escape(inf['first'])}</span>"
                     f"{'<br>' if split else ' '}"
                     f"<span style=\"font-family:{fam}; font-size:{size}px; font-weight:300\">"
                     f"{html_escape(inf['rest'])}</span>")
        mark.setStyleSheet(f"color:{argb(text_color())}; background:transparent")
        words.addWidget(mark)
        tags = QHBoxLayout()
        tags.setSpacing(6)
        for t in inf["tags"]:
            tags.addWidget(Tag(t, c))
        if d.version:
            tags.addWidget(Tag(f"Fastfetch {d.version}", c, accent=True))
        if d.demo:
            tags.addWidget(Tag(tr("demo_tag"), c, accent=True))
        tags.addStretch(1)
        words.addLayout(tags)
        words.addStretch(1)
        hero.addLayout(words)
        hero.addStretch(1)
        lay.addLayout(hero)
        lay.addSpacing(20)

        # Carte « Winver » : version, droits, licence
        # “Winver” card: version, rights, license
        card = SimpleCardWidget(c)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 18)
        cl.setSpacing(2)
        head = QHBoxLayout()
        head.setSpacing(12)
        head.addWidget(self._icon(FIF.INFO, 20, card), 0, Qt.AlignmentFlag.AlignTop)
        tcol = QVBoxLayout()
        tcol.setSpacing(2)
        tcol.addWidget(StrongBodyLabel(inf["full"], card))
        tcol.addWidget(self.body(inf["line2"], card, True))
        tcol.addWidget(self.body(tr("copyright", year=d.when.year, owner=inf["owner"]), card, True))
        head.addLayout(tcol, 1)
        cl.addLayout(head)

        sep = QFrame(card)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{argb(text_color(0.08))}")
        cl.addSpacing(14)
        cl.addWidget(sep)
        cl.addSpacing(14)

        lic = QHBoxLayout()
        lic.setSpacing(12)
        lic.addWidget(self._icon(FIF.CERTIFICATE, 20, card), 0, Qt.AlignmentFlag.AlignTop)
        lcol = QVBoxLayout()
        lcol.setSpacing(6)
        link = QColor(themeColor())
        if isDarkTheme():
            link = link.lighter(150)
        lt = self.body("", card)
        lt.setTextFormat(Qt.TextFormat.RichText)
        lt.setOpenExternalLinks(True)
        anchor = (f"<a href=\"{LICENSE_URL}\" style=\"color:{link.name()}; text-decoration:none\">"
                  f"{html_escape(tr('license_link'))}</a>")
        lt.setText(html_escape(tr("license", link="\x00")).replace("\x00", anchor))
        lcol.addWidget(lt)
        who = QHBoxLayout()
        who.setSpacing(10)
        who.setContentsMargins(0, 4, 0, 0)
        who.addWidget(self._icon(FIF.PEOPLE, 16, card), 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        wcol = QVBoxLayout()
        wcol.setSpacing(0)
        wcol.addWidget(StrongBodyLabel(inf["owner"], card))
        wcol.addWidget(self.body(inf["host"], card, True, 13))
        who.addLayout(wcol, 1)
        lcol.addLayout(who)
        lic.addLayout(lcol, 1)
        cl.addLayout(lic)
        lay.addWidget(card)
        lay.addSpacing(8)

        # Expander « Spécifications de l'appareil »
        # “Device specifications” expander
        rows = self.rows = spec_rows(d, inf)
        self.card = ExpandGroupSettingCard(FIF.DEVELOPER_TOOLS, tr("specs_title"),
                                           tr("specs_sub", n=len(rows)), c)
        copy_btn = PushButton(tr("copy"), self.card)
        copy_btn.setIcon(FIF.COPY)
        copy_btn.clicked.connect(self.copy_all)
        self.card.addWidget(copy_btn)
        for key, orig, value, pct in rows:
            kind = "battery" if orig.startswith("Battery") else "usage"
            self.card.addGroupWidget(SpecRow(key, value, pct, kind, self.copy, self.card.view))
        self.card.installEventFilter(self)
        lay.addWidget(self.card)
        lay.addStretch(1)
        if self.expanded:
            self.card.setExpand(True)

        status = tr("status_demo") if d.demo else \
            (f"Fastfetch {d.version} · " if d.version else "") + tr("status_refreshed", time=f"{d.when:%H:%M}")
        self._footer(status, [(tr("refresh"), FIF.SYNC, self.refresh, False), (tr("ok"), None, self.close, True)],
                     tools=True)

    def toggle_specs(self):
        if self.card:
            self.card.setExpand(not self.card.isExpand)
            self.expanded = self.card.isExpand

    # ── Réglages ──────────────────────────────────────────────────────────
    # ── Settings ──────────────────────────────────────────────────────────
    def open_settings(self):
        self.page = "settings"
        self.render()

    def close_settings(self):
        self.page = "main"
        self.render()

    def _switch(self, parent, checked, on_change):
        sw = SwitchButton(parent, IndicatorPosition.RIGHT)
        sw.setOnText(tr("on"))
        sw.setOffText(tr("off"))
        sw.setChecked(bool(checked))
        sw.checkedChanged.connect(on_change)
        return sw

    def _fluid_card(self, icon, title, content, parent):
        """SettingCard dont la hauteur suit le texte (l'originale est figée à 70 px et le texte se chevauche).
        SettingCard whose height follows its text (the original is fixed at 70 px and the text overlaps)."""
        card = SettingCard(icon, title, content, parent)
        card.setMinimumHeight(70)
        card.setMaximumHeight(16777215)
        hb = card.hBoxLayout
        hb.setContentsMargins(16, 12, 0, 12)
        for i in reversed(range(hb.count())):  # le ressort d'origine empêchait le texte de s'élargir
                                               # the original spacer stopped the text from widening
            sp = hb.itemAt(i).spacerItem()
            if sp and sp.expandingDirections() & Qt.Orientation.Horizontal:
                hb.removeItem(sp)
        hb.setStretchFactor(card.vBoxLayout, 1)
        for lbl in (card.titleLabel, card.contentLabel):
            lbl.setWordWrap(True)
            card.vBoxLayout.setAlignment(lbl, Qt.AlignmentFlag(0))
        # Un alignement sur la mise en page la fige à la hauteur d'une seule ligne : on centre par des ressorts.
        # A layout-level alignment locks it to the height of a single line: center it with spacers instead.
        hb.setAlignment(Qt.AlignmentFlag(0))
        card.vBoxLayout.setAlignment(Qt.AlignmentFlag(0))
        card.vBoxLayout.insertStretch(0, 1)
        card.vBoxLayout.addStretch(1)
        card.vBoxLayout.setSpacing(2)
        return card

    @staticmethod
    def _card_controls(card, *widgets):
        """Place les commandes (boutons, interrupteur…) à droite d'une carte de réglage.
        Places the controls (buttons, switch…) on the right of a setting card."""
        hb = card.hBoxLayout
        hb.addSpacing(12)
        for i, w in enumerate(widgets):
            if i:
                hb.addSpacing(8)
            hb.addWidget(w, 0, Qt.AlignmentFlag.AlignRight)
        hb.addSpacing(16)

    def _section(self, title, lay, parent):
        lay.addWidget(StrongBodyLabel(title, parent))
        lay.addSpacing(8)

    def build_settings(self):
        self.setWindowTitle(tr("settings_window"))
        lay = self._scroll_page()
        c = self.content

        head = QHBoxLayout()
        head.setSpacing(8)
        head.addWidget(self._tool(FIF.RETURN, tr("back"), self.close_settings, c), 0, Qt.AlignmentFlag.AlignVCenter)
        head.addWidget(TitleLabel(tr("settings"), c), 0, Qt.AlignmentFlag.AlignVCenter)
        head.addStretch(1)
        lay.addLayout(head)
        lay.addSpacing(16)

        # Général : langue
        # General: language
        self._section(tr("general"), lay, c)
        lang = self._fluid_card(FIF.LANGUAGE, tr("language"), tr("language_desc"), c)
        combo = ComboBox(lang)
        codes = ["auto", "fr", "en"]
        for code, label in zip(codes, (tr("lang_auto"), "Français", "English")):
            combo.addItem(label, userData=code)
        combo.setCurrentIndex(codes.index(SETTINGS["language"]))
        combo.setMinimumWidth(180)
        combo.currentIndexChanged.connect(lambda i: self.set_lang(codes[i]))
        self._card_controls(lang, combo)
        lay.addWidget(lang)
        lay.addSpacing(24)

        for kind in ("fastfetch", "app"):
            self._section(tr(f"group_{kind}"), lay, c)
            card = self._fluid_card(FIF.UPDATE if kind == "fastfetch" else FIF.APPLICATION, " ", " ", c)
            check = PushButton(tr("check"), card)
            check.setIcon(FIF.SYNC)
            check.clicked.connect(lambda _=False, k=kind: self.check_updates(k))
            act = PrimaryPushButton(tr("update"), card)
            act.setIcon(FIF.DOWNLOAD)
            act.clicked.connect(lambda _=False, k=kind: self.run_update(k))
            self._card_controls(card, check, act)
            lay.addWidget(card)
            lay.addSpacing(3)

            auto = self._fluid_card(FIF.HISTORY, tr("auto_update"), tr(f"auto_{kind}_desc"), c)
            sw = self._switch(auto, SETTINGS[f"{kind}_auto_update"], lambda v, k=kind: self.set_auto(k, v))
            self._card_controls(auto, sw)
            lay.addWidget(auto)
            self.ui[kind] = dict(card=card, check=check, act=act, switch=sw)
            self._sync_update_ui(kind)
            lay.addSpacing(24)

        # Copies gardées après les mises à jour : supprimées seulement sur demande (bouton).
        # Copies kept after updates: deleted only when asked (button).
        backups = list_backups()
        if backups:
            self._section(tr("group_backups"), lay, c)
            size = sum(os.path.getsize(b) for b in backups if os.path.isfile(b))
            card = self._fluid_card(FIF.HISTORY, tr("backups_title"),
                                    tr("backups_desc_1" if len(backups) == 1 else "backups_desc",
                                       n=len(backups), size=fmt_bytes(size)), c)
            btn = PushButton(tr("backups_delete"), card)
            btn.setIcon(FIF.DELETE)
            btn.clicked.connect(lambda _=False, paths=backups: self.remove_backups(paths))
            self._card_controls(card, btn)
            lay.addWidget(card)
            lay.addSpacing(24)
        lay.addStretch(1)

        self._footer(f"{APP_NAME} {APP_VERSION} · build {BUILD} · github.com/{UPDATE_REPO}",
                     [(tr("done"), None, self.close_settings, True)])

    def set_lang(self, code):
        SETTINGS["language"] = code
        SETTINGS.save()
        set_language(code)
        QTimer.singleShot(0, self.render)  # reconstruit la page dans la nouvelle langue
                                           # rebuilds the page in the new language

    def remove_backups(self, paths):
        n = delete_backups(paths)
        self.render()
        self.toast("success", tr("backups_deleted_1" if n == 1 else "backups_deleted", n=n),
                   duration=2500, title=tr("backups_title"), closable=False)

    def set_auto(self, kind, value):
        SETTINGS[f"{kind}_auto_update"] = bool(value)
        SETTINGS.save()

    # ── Mises à jour ──────────────────────────────────────────────────────
    # ── Updates ───────────────────────────────────────────────────────────
    def run_bg(self, fn, done):
        """Exécute fn en arrière-plan puis done(résultat, erreur) dans le fil de l'interface.
        Runs fn in the background, then done(result, error) on the UI thread."""
        fut = self._bg.submit(fn)

        def poll():
            if not fut.done():
                QTimer.singleShot(100, poll)
                return
            try:
                res, err = fut.result(), None
            except Exception as e:
                res, err = None, e
                write_log(f"Tâche d'arrière-plan en échec : {e!r}")
            done(res, err)

        QTimer.singleShot(100, poll)

    def _update_texts(self, kind):
        u = self.upd[kind]
        st, latest = u.get("state", "idle"), u.get("latest") or ""
        if kind == "fastfetch":
            local = u.get("local") or (self.data.version if self.data and not self.data.demo else "")
            if not self.ff_exe:
                title = tr("ff_not_installed")
            else:
                title = f"Fastfetch {local}".strip()
                if u.get("method"):
                    title += " · " + tr(f"method_{u['method']}")
        else:
            title = f"{APP_NAME} {APP_VERSION}"
        key = {"updated": "st_updated_restart" if kind == "app" else "st_updated"}.get(st, f"st_{st}")
        if st == "available" and u.get("action") == "hint":
            key = "st_hint"
        elif st == "available" and u.get("action") == "page":
            key = "st_no_checksum" if kind == "app" and u.get("no_checksum") else \
                ("st_page" if kind == "fastfetch" else "st_page_app")
        if key not in STRINGS["fr"]:
            return title, ""
        return title, tr(key, latest=latest, repo=UPDATE_REPO, msg=u.get("msg", ""), cmd=u.get("hint"))

    def _sync_update_ui(self, kind):
        w = self.ui.get(kind)
        if not w or not all(isValid(x) for x in w.values()):
            return
        title, text = self._update_texts(kind)
        u = self.upd[kind]
        st, action = u.get("state"), u.get("action")
        w["card"].setTitle(title)
        w["card"].setContent(text)
        busy = st in ("checking", "updating")
        w["check"].setEnabled(not busy)
        if kind == "app" and st == "updated":
            w["act"].setText(tr("restart"))
            w["act"].setIcon(FIF.SYNC)
            w["act"].setVisible(True)
        elif st in ("available", "missing") and action in ("update", "page"):
            w["act"].setText(tr("update") if action == "update" else tr("open_page"))
            w["act"].setIcon(FIF.DOWNLOAD if action == "update" else FIF.LINK)
            w["act"].setVisible(True)
        else:
            w["act"].setVisible(False)
        w["act"].setEnabled(not busy)

    def check_updates(self, kind, auto=False):
        u = self.upd[kind]
        if u.get("state") in ("checking", "updating"):
            return
        u["state"] = "checking"
        self._sync_update_ui(kind)
        if kind == "fastfetch":
            self.ff_exe = exe = find_fastfetch(self.args.fastfetch)  # Fastfetch a pu être installé entre-temps
                                                                     # Fastfetch may have been installed since
            fn = lambda: ff_check(exe)
        else:
            fn = app_check
        self.run_bg(fn, lambda res, err: self._on_checked(kind, res, err, auto))

    def _set_error(self, kind, err):
        u = self.upd[kind]
        u.update(state="error", msg=str(err) or err.__class__.__name__)
        self._sync_update_ui(kind)
        return u["msg"]

    def _on_checked(self, kind, res, err, auto):
        u = self.upd[kind]
        if err:
            self._set_error(kind, err)
            return  # au démarrage, un échec (hors ligne…) reste discret : il est dans le journal
                    # at startup, a failure (offline…) stays quiet: it's in the log
        u.update(res)
        latest, local = res["latest"], (res["local"] if kind == "fastfetch" else APP_VERSION)
        if kind == "fastfetch" and not local:
            state = "missing"
        elif latest is None:
            state = "norelease"
        elif is_newer(latest, local):
            state = "available"
        elif is_newer(local, latest):
            state = "dev"
        else:
            state = "uptodate"
        u["state"] = state
        self._sync_update_ui(kind)
        if auto and state == "available":
            if u.get("action") == "update":
                self.run_update(kind, auto=True)
            else:
                key = "toast_ff_available" if kind == "fastfetch" else "toast_app_available"
                self.toast("info", tr(key, v=u["latest"]), duration=7000)

    def run_update(self, kind, auto=False):
        u = self.upd[kind]
        if kind == "app" and u.get("state") == "updated":
            restart_app()
            return
        if u.get("action") == "page":
            QDesktopServices.openUrl(QUrl(u.get("url") or FASTFETCH_URL))
            return
        if u.get("action") != "update" or u.get("state") in ("checking", "updating"):
            return
        u["state"] = "updating"
        self._sync_update_ui(kind)
        if kind == "fastfetch":
            exe, method, latest = self.ff_exe, u.get("method"), u.get("latest")
            fn = lambda: ff_update(exe, method, latest)
        else:
            url, sha = u.get("url"), u.get("sha256")
            fn = lambda: app_install(url, sha)
        self.run_bg(fn, lambda res, err: self._on_updated(kind, res, err, auto))

    def _on_updated(self, kind, res, err, auto):
        u = self.upd[kind]
        what = "Fastfetch" if kind == "fastfetch" else APP_NAME
        if err:
            msg = self._set_error(kind, err)
            if auto:
                self.toast("error", tr("toast_failed", what=what, msg=msg[:120]), duration=9000)
            return
        if kind == "fastfetch":
            u.update(state="updated", local=res or u.get("latest"), latest=res or u.get("latest"))
            self.toast("success", tr("toast_ff_updated", v=u["local"]))
            if self.page == "main" and not self.args.demo:
                self.refresh()  # relit Fastfetch pour afficher sa nouvelle version
                                # re-reads Fastfetch to show its new version
        else:
            res = res or u.get("latest")  # l'exe ne relit pas sa version : on garde celle de GitHub
                                          # the exe doesn't read its version back: keep GitHub's
            u.update(state="updated", latest=res, action="restart")
            if auto:
                btn = PushButton(tr("restart"))
                btn.setIcon(FIF.SYNC)
                btn.clicked.connect(restart_app)
                self.toast("success", tr("toast_app_updated", v=res), duration=-1, button=btn)
        self._sync_update_ui(kind)

    def toast(self, level, content, duration=5000, button=None, title=None, closable=True):
        """Bandeau en bas de la fenêtre ; vertical s'il est long ou porte un bouton (sinon il déborde).
        Banner at the bottom of the window; vertical if long or if it carries a button (otherwise it overflows)."""
        vertical = button is not None or len(content) > 48
        bar = getattr(InfoBar, level)(title or tr("toast_update"), content, duration=duration,
                                      position=InfoBarPosition.BOTTOM, isClosable=closable,
                                      orient=Qt.Orientation.Vertical if vertical else Qt.Orientation.Horizontal,
                                      parent=self)
        if button is not None:
            bar.addWidget(button)
        return bar

    def start_auto_updates(self):
        if self.args.selftest:
            return
        for kind in ("fastfetch", "app"):
            if SETTINGS[f"{kind}_auto_update"] and not (kind == "fastfetch" and self.args.demo):
                self.check_updates(kind, auto=True)

    # ── Presse-papiers ────────────────────────────────────────────────────
    # ── Clipboard ─────────────────────────────────────────────────────────
    def copy(self, text, msg=None):
        QGuiApplication.clipboard().setText(text)
        self.toast("success", msg or tr("copied_default"), duration=2200, title=tr("copied"), closable=False)

    def copy_all(self):
        if not self.data:
            return
        inf = os_info(self.data)
        sep = " : " if LANG == "fr" else ": "
        lines = [inf["pretty"], inf["line2"], ""] + [f"{k}{sep}{v}" for k, _, v, _ in spec_rows(self.data, inf)]
        self.copy("\n".join(lines), tr("copied_all"))


def html_escape(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ════════════════════════════════════════════════════════════════════════════

def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="fastver", description=tr("cli_desc"))
    p.add_argument("--demo", action="store_true", help=tr("cli_demo"))
    p.add_argument("--theme", choices=("auto", "light", "dark"), default="auto", help=tr("cli_theme"))
    p.add_argument("--accent", default="logo", help=tr("cli_accent"))
    p.add_argument("--version", action="version", version=f"FastVer {APP_VERSION} (build {BUILD})")
    p.add_argument("--expand", action="store_true", help=tr("cli_expand"))
    p.add_argument("--backdrop", choices=("acrylic", "solid"), default=None, help=tr("cli_backdrop"))
    p.add_argument("--mica", dest="backdrop", action="store_const", const="acrylic", help=argparse.SUPPRESS)
    p.add_argument("--wallpaper", metavar="IMAGE", help=tr("cli_wallpaper"))
    p.add_argument("--fastfetch", metavar="PATH", help=tr("cli_fastfetch"))
    p.add_argument("--lang", choices=("auto", "fr", "en"), default=None, help=tr("cli_lang"))
    p.add_argument("--selftest", action="store_true", help=argparse.SUPPRESS)  # contrôle automatique (CI)
                                                                              # automatic check (CI)
    args = p.parse_args(argv)
    if args.selftest:
        args.demo = True
    return args


def bring_to_front(pid):
    """Met au premier plan la fenêtre de l'instance déjà ouverte (Windows).
    Brings the already-open instance's window to the front (Windows)."""
    if os.name != "nt" or not pid:
        return False
    user32 = ctypes.windll.user32
    found = []
    proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def visit(hwnd, _):
        owner = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(ctypes.c_void_p(hwnd)):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(proc(visit), 0)
    for hwnd in found:
        user32.ShowWindow(ctypes.c_void_p(hwnd), 9)          # SW_RESTORE
        user32.SetForegroundWindow(ctypes.c_void_p(hwnd))
        return True
    return False


def acquire_instance_lock():
    """Une seule fenêtre FastVer à la fois : renvoie le verrou, ou None si FastVer est déjà ouvert
    (sa fenêtre est alors ramenée au premier plan). Un verrou laissé par un FastVer planté est
    reconnu (processus disparu) et repris automatiquement.
    A single FastVer window at a time: returns the lock, or None if FastVer is already open
    (its window is then brought to the front). A lock left by a crashed FastVer is recognized
    (process gone) and taken over automatically."""
    wait_pid = os.environ.pop(WAIT_ENV, "")
    if wait_pid.isdigit():
        _wait_for_exit(int(wait_pid), timeout=20)   # redémarrage : l'ancienne instance se ferme
                                                    # restart: the old instance is closing
    try:
        os.makedirs(config_dir(), exist_ok=True)
    except OSError:
        return True   # dossier inaccessible : pas de verrou, FastVer démarre quand même
                      # folder unreachable: no lock, FastVer starts anyway
    lock = QLockFile(os.path.join(config_dir(), "fastver.lock"))
    lock.setStaleLockTime(0)   # seul le PID décide si le verrou est périmé / only the PID decides staleness
    if lock.tryLock(3000 if wait_pid else 300):
        return lock
    if lock.error() != QLockFile.LockError.LockFailedError:
        write_log(f"Verrou d'instance indisponible ({lock.error()}) : démarrage sans verrou")
        return True
    info = lock.getLockInfo()   # selon la version de PySide6 : (pid, hôte, appli) ou (ok, pid, hôte, appli)
                                # depending on the PySide6 version: (pid, host, app) or (ok, pid, host, app)
    pid = next((v for v in (info if isinstance(info, tuple) else ())
                if isinstance(v, int) and not isinstance(v, bool)), 0)
    write_log(f"FastVer est déjà ouvert (PID {pid}) : cette instance se ferme")
    if not bring_to_front(pid) and os.name == "nt":
        try:
            ctypes.windll.user32.MessageBoxW(None, tr("already_running"), APP_NAME, 0x40 | 0x10000)
        except Exception:
            pass
    return None


def run_selftest(app, win):
    """--selftest : parcourt l'interface (données de démonstration) puis quitte avec le code 0,
    ou 1 en cas d'erreur. Utilisé par le workflow de compilation pour vérifier l'exe produit.
    --selftest: walks through the interface (sample data), then exits with code 0,
    or 1 on error. Used by the build workflow to check the produced exe."""
    def check_data():
        if not win.data or win.card is None:
            raise RuntimeError("données de démonstration absentes / sample data missing")

    steps = [
        check_data, win.toggle_specs, win.toggle_theme, win.open_settings, win.toggle_theme, win.close_settings,
        lambda: win.material and win.material.pixmap(win.screen(), isDarkTheme()),
    ]
    state = {"i": 0}

    def step():
        try:
            if state["i"] < len(steps):
                steps[state["i"]]()
                state["i"] += 1
                QTimer.singleShot(300, step)
                return
            write_log("Autotest réussi")
            app.exit(0)
        except Exception:
            write_log("Autotest en échec :\n" + traceback.format_exc())
            app.exit(1)

    QTimer.singleShot(2500, step)                      # laisse le temps au chargement / give loading time
    QTimer.singleShot(30000, lambda: (write_log("Autotest : délai dépassé"), app.exit(2)))


def main(argv=None):
    args = parse_args(argv)
    if args.lang:
        set_language(args.lang)  # pour cette session seulement (non enregistré)
                                 # for this session only (not saved)
    write_log(f"FastVer {APP_VERSION} build {BUILD} — {APP_PATH} — Python {platform.python_version()}")
    if sys.platform.startswith("linux") and not os.environ.get("QT_QPA_PLATFORM"):
        # X11 (ou XWayland) d'abord : la fenêtre sans bordure et l'acrylique ont besoin de connaître la position
        # de la fenêtre à l'écran, que Wayland ne donne pas. Wayland natif reste le repli.
        # X11 (or XWayland) first: the frameless window and the acrylic need the window's on-screen position,
        # which Wayland doesn't provide. Native Wayland remains the fallback.
        os.environ["QT_QPA_PLATFORM"] = "xcb;wayland"
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setFont(qfont(UI_FAMILIES, 14))
    lock = True if args.selftest else acquire_instance_lock()
    if lock is None:
        return 0
    win = FastVerWindow(args)
    win.show()
    if args.selftest:
        run_selftest(app, win)
    code = app.exec()
    if isinstance(lock, QLockFile):
        lock.unlock()
    return code


def _excepthook(etype, value, tb):
    write_log("".join(traceback.format_exception(etype, value, tb)))
    sys.__excepthook__(etype, value, tb)


if __name__ == "__main__":
    sys.excepthook = _excepthook  # erreurs survenant pendant l'exécution → journal
                                  # errors raised while running → log
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        fatal_error(traceback.format_exc())
        sys.exit(1)
