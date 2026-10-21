from __future__ import annotations

import logging
import os
import sys
import zipfile
from typing import Callable, Dict, Optional

from PySide6.QtGui import QPixmap
from PySide6.QtCore import QSize, Qt

log = logging.getLogger(__name__)

ICON_SIZE = 32

def _get_local_icons_dir():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
        # Source checkout: the icon pack lives at the repo root.
        repo_icons = os.path.join(base, "..", "icons_local")
        if os.path.isdir(repo_icons) and not os.path.isdir(os.path.join(base, "icons_local")):
            return os.path.normpath(repo_icons)
    return os.path.join(base, "icons_local")


class IconCache:

    def __init__(self, icon_urls_path: Optional[str] = None):
        self._pixmaps: Dict[int, QPixmap] = {}
        self._local_dir = _get_local_icons_dir()
        os.makedirs(self._local_dir, exist_ok=True)
        # The release ships icons_local.zip; it can sit next to the exe unextracted.
        self._zip = None
        self._zip_names: Dict[str, str] = {}
        zip_path = self._local_dir + ".zip"
        if os.path.isfile(zip_path):
            try:
                self._zip = zipfile.ZipFile(zip_path)
                self._zip_names = {n.rsplit("/", 1)[-1]: n for n in self._zip.namelist()
                                   if n.endswith(".webp")}
            except (OSError, zipfile.BadZipFile) as exc:
                log.warning("Could not open %s: %s", zip_path, exc)
                self._zip = None

    def has_icon(self, item_key: int) -> bool:
        return (os.path.isfile(os.path.join(self._local_dir, f"{item_key}.webp"))
                or f"{item_key}.webp" in self._zip_names)

    def _load(self, item_key: int) -> Optional[QPixmap]:
        name = f"{item_key}.webp"
        px = QPixmap()
        local_path = os.path.join(self._local_dir, name)
        if os.path.isfile(local_path):
            px.load(local_path)
        elif name in self._zip_names:
            px.loadFromData(self._zip.read(self._zip_names[name]))
        if px.isNull():
            return None
        self._pixmaps[item_key] = px
        return px

    def get_pixmap(self, item_key: int) -> Optional[QPixmap]:
        if item_key in self._pixmaps:
            return self._pixmaps[item_key]
        return self._load(item_key)

    def request_icon(self, item_key: int, callback: Callable[[int, QPixmap], None]) -> None:
        # Icons are deliberately local-only in this build.
        px = self.get_pixmap(item_key)
        if px is not None:
            callback(item_key, px)

    def preload_keys(self, keys: list, callback: Callable[[int, QPixmap], None]) -> None:
        for key in keys:
            if key not in self._pixmaps:
                self.request_icon(key, callback)

    def get_merc_pixmap(self, char_key: int) -> Optional[QPixmap]:
        cache_key = f"merc_{char_key}"
        if cache_key in self._pixmaps:
            return self._pixmaps[cache_key]

        merc_dir = os.path.join(os.path.dirname(self._local_dir), "icons_mercenary")
        local_path = os.path.join(merc_dir, f"{char_key}.webp")
        if os.path.isfile(local_path):
            px = QPixmap(local_path)
            if not px.isNull():
                self._pixmaps[cache_key] = px
                return px
        return None

    @property
    def coverage(self) -> int:
        try:
            names = {f for f in os.listdir(self._local_dir) if f.endswith('.webp')}
        except Exception:
            names = set()
        return len(names | set(self._zip_names))
