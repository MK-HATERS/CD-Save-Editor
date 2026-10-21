"""Refresh the bundled knowledge/quest/mission/stage JSON and item icons from the installed client.

Run after a game update (and after "Refresh from local game" updated item_names.json):

    python refresh_static_data.py "F:/SteamLibrary/steamapps/common/Crimson Desert" [icons_dir]

icons_dir defaults to ../icons_local.

Existing entries keep their names (the old files sometimes chose a subtitle
over the title); new records are appended. Quest mission/stage lists and
quest_stage_map.json are rebuilt from the live quest records, because the
Quest Editor's Complete/Reset Stages writes to whatever stages are listed.

Needs ../CrimsonGameMods (crimson_rs) on the path.
"""
from __future__ import annotations

import bisect
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, "..", "CrimsonGameMods"))
import crimson_rs  # noqa: E402

TABLE_DIR = "gamedata/binary__/client/bin"
ENG_DIR = "gamedata/stringtable/binary__/eng"
CATEGORY_NAMES = {0: "Side", 12: "Regional", 13: "Main Story"}


def _table(game: str, stem: str) -> dict[int, bytes]:
    """{key: raw record} using the .pabgh offset index."""
    head = bytes(crimson_rs.extract_file(game, "0008", TABLE_DIR, stem + ".pabgh"))
    body = bytes(crimson_rs.extract_file(game, "0008", TABLE_DIR, stem + ".pabgb"))
    wide = 2 + struct.unpack_from("<H", head, 0)[0] * 8 != len(head)
    count = struct.unpack_from("<I" if wide else "<H", head, 0)[0]
    base = 4 if wide else 2
    entries = [struct.unpack_from("<II", head, base + i * 8) for i in range(count)]
    ends = sorted(off for _, off in entries) + [len(body)]
    return {k: body[off:ends[bisect.bisect_right(ends, off)]] for k, off in entries}


def _paloc(game: str, name: str) -> dict[int, str]:
    data = bytes(crimson_rs.extract_file(game, "0020", ENG_DIR, name))
    return {int(e["string_key"]): e["string_value"]
            for e in crimson_rs.parse_paloc_bytes(data) if str(e["string_key"]).isdigit()}


def _name(rec: bytes) -> str:
    size = struct.unpack_from("<I", rec, 4)[0]
    return rec[8:8 + size].decode("ascii", "replace").rstrip("\0")


def _after_name(rec: bytes) -> int:
    return 8 + struct.unpack_from("<I", rec, 4)[0] + 1


def _loc_indices(rec: bytes):
    """LocalizableString indices: u8 category, u64 index, u32 len, index as decimal text."""
    for m in re.finditer(rb"\d{1,20}", rec):
        start, text = m.start(), m.group()
        if start >= 13 and struct.unpack_from("<I", rec, start - 4)[0] == len(text):
            idx = struct.unpack_from("<Q", rec, start - 12)[0]
            if str(idx).encode() == text:
                yield idx


def _display(rec: bytes, strings: dict[int, str]) -> str:
    return next((strings[i] for i in _loc_indices(rec) if i in strings), "")


def _read_loc(rec: bytes, pos: int) -> tuple[int, int]:
    return struct.unpack_from("<Q", rec, pos + 1)[0], pos + 13 + struct.unpack_from("<I", rec, pos + 9)[0]


def _quest_header(rec: bytes) -> dict:
    pos = _after_name(rec)
    quest_type, category = rec[pos], rec[pos + 1]
    title, pos = _read_loc(rec, pos + 2)
    subtitle, pos = _read_loc(rec, pos)
    group = struct.unpack_from("<I", rec, pos)[0]
    return {"quest_type": quest_type, "category": category, "title": title,
            "subtitle": subtitle, "quest_group": group if group < 0x10000 else 0, "end": pos + 4}


def _key_list(rec: bytes, start: int, valid: set[int]) -> list[int]:
    """First count-prefixed u32 array whose members are all in `valid`."""
    if not valid:
        return []
    for pos in range(start, len(rec) - 4):
        count = struct.unpack_from("<I", rec, pos)[0]
        if 1 <= count <= 4000 and pos + 4 + 4 * count <= len(rec):
            keys = struct.unpack_from("<%dI" % count, rec, pos + 4)
            if all(k in valid for k in keys):
                return list(keys)
    return []


def _load(name: str):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def _save(name: str, data, indent) -> None:
    text = json.dumps(data, indent=indent)
    with open(os.path.join(HERE, name), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(text + "\n")


def refresh(game: str) -> None:
    quest_strings = _paloc(game, "quest.paloc")
    quests = _table(game, "questinfo")
    missions = _table(game, "missioninfo")
    stage_tbl = _table(game, "stageinfo")

    mission_parent = {k: struct.unpack_from("<I", r, _after_name(r))[0] for k, r in missions.items()}
    stage_parent = {r["key"]: r.get("parent_quest") for r in crimson_rs.parse_table(
        "stage_info",
        bytes(crimson_rs.extract_file(game, "0008", TABLE_DIR, "stageinfo.pabgb")),
        bytes(crimson_rs.extract_file(game, "0008", TABLE_DIR, "stageinfo.pabgh")))}
    own_missions: dict[int, set[int]] = {}
    for k, q in mission_parent.items():
        own_missions.setdefault(q, set()).add(k)
    own_stages: dict[int, set[int]] = {}
    for k, q in stage_parent.items():
        own_stages.setdefault(q, set()).add(k)

    quest_info = {}
    for key, rec in quests.items():
        head = _quest_header(rec)
        display = quest_strings.get(head["title"]) or quest_strings.get(head["subtitle"]) or _name(rec)
        quest_info[key] = {
            "name": _name(rec), "display": display, **head,
            "missions": _key_list(rec, head["end"], own_missions.get(key, set())),
            "stages": _key_list(rec, head["end"], own_stages.get(key, set())),
        }

    # quest_names.json / quest_database.json
    names = _load("quest_names.json")
    known = {e["key"] for e in names}
    names += [{"key": k, "name": q["name"], "display": q["display"]}
              for k, q in quest_info.items() if k not in known]
    _save("quest_names.json", names, 2)

    database = _load("quest_database.json")
    for entry in database:
        q = quest_info.get(entry["key"])
        if q:
            entry["missions"] = q["missions"] or entry["missions"]
            entry["stages"] = q["stages"] or entry["stages"]
    known = {e["key"] for e in database}
    for k, q in quest_info.items():
        if k not in known:
            database.append({
                "key": k, "name": q["name"], "display": q["display"],
                "category": q["category"], "category_name": CATEGORY_NAMES.get(q["category"], "Side"),
                "quest_type": q["quest_type"], "quest_group": q["quest_group"],
                "missions": q["missions"], "stages": q["stages"],
            })
    _save("quest_database.json", database, 1)

    _save("quest_stage_map.json", {
        "quest_stages": {str(k): q["stages"] for k, q in quest_info.items() if q["stages"]},
        "quest_missions": {str(k): q["missions"] for k, q in quest_info.items() if q["missions"]},
    }, 2)

    # mission_names.json
    names = _load("mission_names.json")
    known = {e["key"] for e in names}
    names += [{"key": k, "name": _name(r), "display": _display(r, quest_strings) or _name(r)}
              for k, r in missions.items() if k not in known]
    _save("mission_names.json", names, 2)

    # stage_names.json (internal names only)
    stage_names = _load("stage_names.json")
    stage_names.update({str(k): _name(r) for k, r in stage_tbl.items()})
    _save("stage_names.json", stage_names, None)

    # knowledge_keys_all.json drives "inject all knowledge": live, unblocked records only.
    know_strings = _paloc(game, "knowledge.paloc")
    know_raw = _table(game, "knowledgeinfo")
    usable = {r["key"] for r in crimson_rs.parse_table(
        "knowledge_info",
        bytes(crimson_rs.extract_file(game, "0008", TABLE_DIR, "knowledgeinfo.pabgb")),
        bytes(crimson_rs.extract_file(game, "0008", TABLE_DIR, "knowledgeinfo.pabgh")))
        if not r.get("_blob_fallback") and r.get("is_blocked") == 0}
    knowledge = [e for e in _load("knowledge_keys_all.json") if e["key"] in know_raw]
    known = {e["key"] for e in knowledge}
    for k in know_raw:
        if k not in usable or k in known:
            continue
        entry = {"key": k, "name": _name(know_raw[k])}
        display = _display(know_raw[k], know_strings)
        if display:
            entry["display_name"] = display
        knowledge.append(entry)
    _save("knowledge_keys_all.json", knowledge, 2)

    print(f"quests {len(quest_info)}, missions {len(missions)}, stages {len(stage_tbl)}, "
          f"knowledge {len(knowledge)}")


def _jenkins(data: bytes, seed: int = 0xC5EDE) -> int:
    """Bob Jenkins lookup3 hashlittle; the client hashes texture names with seed 0xC5EDE."""
    mask = 0xFFFFFFFF

    def rot(x, k):
        return ((x << k) | (x >> (32 - k))) & mask

    a = b = c = (0xDEADBEEF + len(data) + seed) & mask
    rest = data
    while len(rest) > 12:
        a = (a + int.from_bytes(rest[0:4], "little")) & mask
        b = (b + int.from_bytes(rest[4:8], "little")) & mask
        c = (c + int.from_bytes(rest[8:12], "little")) & mask
        a = (a - c) & mask; a ^= rot(c, 4); c = (c + b) & mask
        b = (b - a) & mask; b ^= rot(a, 6); a = (a + c) & mask
        c = (c - b) & mask; c ^= rot(b, 8); b = (b + a) & mask
        a = (a - c) & mask; a ^= rot(c, 16); c = (c + b) & mask
        b = (b - a) & mask; b ^= rot(a, 19); a = (a + c) & mask
        c = (c - b) & mask; c ^= rot(b, 4); b = (b + a) & mask
        rest = rest[12:]
    if not rest:
        return c
    tail = rest + b"\0" * 12
    a = (a + int.from_bytes(tail[0:4], "little")) & mask
    b = (b + int.from_bytes(tail[4:8], "little")) & mask
    c = (c + int.from_bytes(tail[8:12], "little")) & mask
    c ^= b; c = (c - rot(b, 14)) & mask
    a ^= c; a = (a - rot(c, 11)) & mask
    b ^= a; b = (b - rot(a, 25)) & mask
    c ^= b; c = (c - rot(b, 16)) & mask
    a ^= c; a = (a - rot(c, 4)) & mask
    b ^= a; b = (b - rot(a, 14)) & mask
    c ^= b; c = (c - rot(b, 24)) & mask
    return c


def refresh_icons(game: str, icons_dir: str) -> None:
    """Add <item key>.webp for items in item_names.json that have no icon yet.

    iteminfo stores each icon as a hash of its texture name. The original-case
    names are only in the UI atlas XML (archive filenames are lower-cased), so
    hash those and map them to the DDS files in ui/texture/icon.
    """
    import io
    from PIL import Image

    icon_dir, xml_dir = "ui/texture/icon", "ui/xml/texture"
    listing = {d["path"]: [f["name"] for f in d["files"]]
               for d in crimson_rs.parse_pamt_file(os.path.join(game, "0012", "0.pamt"))["directories"]}
    icon_files = set(listing.get(icon_dir, []))
    by_hash: dict[int, str] = {}
    for xml in listing.get(xml_dir, []):
        text = bytes(crimson_rs.extract_file(game, "0012", xml_dir, xml)).decode("utf-8", "replace")
        for name, path in re.findall(r'<Texture Name="([^"]+)"\s+Filename="([^"]+)"', text):
            dds = path.rsplit("/", 1)[-1]
            if dds.lower() in icon_files:
                for candidate in (name, path, dds.rsplit(".", 1)[0]):
                    by_hash.setdefault(_jenkins(candidate.encode()), dds.lower())

    records = crimson_rs.parse_iteminfo_from_bytes(
        bytes(crimson_rs.extract_file(game, "0008", TABLE_DIR, "iteminfo.pabgb")))
    icon_of = {r["key"]: r["item_icon_list"][0]["icon_path"] for r in records if r.get("item_icon_list")}
    have = {int(f[:-5]) for f in os.listdir(icons_dir) if f.endswith(".webp") and f[:-5].isdigit()}
    donor = {icon_of[k]: k for k in have if k in icon_of}

    added = copied = failed = 0
    for entry in _load("item_names.json")["items"]:
        key = entry["itemKey"]
        icon = icon_of.get(key)
        if key in have or icon is None:
            continue
        out = os.path.join(icons_dir, f"{key}.webp")
        if icon in by_hash:
            try:
                data = bytes(crimson_rs.extract_file(game, "0012", icon_dir, by_hash[icon]))
                Image.open(io.BytesIO(data)).convert("RGBA").resize((256, 256)).save(out, "WEBP", quality=80, method=6)
                added += 1
            except Exception:
                failed += 1
                continue
        elif icon in donor:
            with open(os.path.join(icons_dir, f"{donor[icon]}.webp"), "rb") as src, open(out, "wb") as dst:
                dst.write(src.read())
            copied += 1
        else:
            continue
        donor.setdefault(icon, key)
    print(f"icons: {added} extracted, {copied} shared, {failed} failed")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    refresh(sys.argv[1])
    refresh_icons(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else os.path.join(HERE, "..", "icons_local"))
