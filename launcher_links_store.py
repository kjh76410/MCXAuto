import json
import os

STORE_PATH = "launcher_links.json"


def _load_all():
    if not os.path.exists(STORE_PATH):
        return []
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_all(links):
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)


def list_links():
    """[{"name": str, "url": str}, ...] 형태로, 추가된 순서 그대로 돌려줍니다."""
    return _load_all()


def add_link(name, url):
    links = _load_all()
    links.append({"name": name, "url": url})
    _save_all(links)


def delete_link(name):
    links = _load_all()
    links = [link for link in links if link.get("name") != name]
    _save_all(links)
