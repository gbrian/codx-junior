import json
import os

import pytest

from codx.junior.browser.scripts import (
    STEPS,
    BrowserScriptStore,
    coerce_code,
    normalize_site,
    parse_steps,
)


def _steps():
    return [
        {"action": "goto", "url": "https://github.com/login"},
        {"action": "type", "selector": "#login_field", "text": "user"},
        {"action": "click", "selector": "input[type=submit]"},
    ]


@pytest.fixture
def store(tmp_path):
    return BrowserScriptStore(str(tmp_path))


def test_normalize_site():
    assert normalize_site("https://www.GitHub.com/login?x=1") == "github.com"
    assert normalize_site("github.com") == "github.com"
    assert normalize_site("http://localhost:3000/app") == "localhost"
    assert normalize_site(None) == "generic"
    assert normalize_site("   ") == "generic"


def test_coerce_code_validates_steps():
    code = coerce_code(_steps())
    assert json.loads(code)[0]["action"] == "goto"
    assert parse_steps(code)[1]["text"] == "user"

    with pytest.raises(ValueError):
        coerce_code([{"url": "https://x"}])
    with pytest.raises(ValueError):
        coerce_code("not json")
    with pytest.raises(ValueError):
        coerce_code("[]")
    with pytest.raises(ValueError):
        coerce_code("x", language="cobol")


def test_coerce_code_keeps_javascript_verbatim():
    assert coerce_code("return document.title;", language="javascript") == "return document.title;"


def test_save_get_and_list(store):
    script = store.save_script(
        title="GitHub login",
        code=_steps(),
        site="https://github.com",
        description="password login flow",
        tags=["login"],
    )
    assert script.id
    assert script.site == "github.com"
    assert script.version == 1

    loaded = store.get_script(script.id)
    assert loaded.title == "GitHub login"
    assert len(loaded.steps) == 3
    assert os.path.isfile(store.code_path(script.id, STEPS))

    entries = store.list_scripts(site="github.com")
    assert [entry["id"] for entry in entries] == [script.id]
    assert store.list_scripts(site="gitlab.com") == []


def test_update_bumps_version_and_archives(store):
    script = store.save_script(title="Flow", code=_steps(), site="github.com")
    updated = store.save_script(
        script_id=script.id,
        title="Flow",
        code=[{"action": "reload"}],
        site="github.com",
    )
    assert updated.id == script.id
    assert updated.version == 2
    assert store.list_versions(script.id) == ["v1.json"]
    assert store.get_script(script.id).steps == [{"action": "reload"}]


def test_same_title_and_site_updates_in_place(store):
    first = store.save_script(title="Login", code=_steps(), site="github.com")
    second = store.save_script(title="login", code=_steps(), site="https://www.github.com/")
    assert second.id == first.id
    assert second.version == 2
    assert len(store.list_scripts()) == 1


def test_search_by_tags_and_site(store):
    store.save_script(title="Search products", code=_steps(), site="amazon.com", tags=["shop", "search"])
    login = store.save_script(title="Login", code=_steps(), site="github.com", tags=["auth"])

    assert [entry["id"] for entry in store.search_scripts(tags=["auth"])] == [login.id]
    assert store.search_scripts(query="login", site="github.com")[0]["id"] == login.id
    # sub domains belong to the same site
    assert store.search_scripts(site="gist.github.com")[0]["id"] == login.id


def test_find_by_title(store):
    script = store.save_script(title="Checkout", code=_steps(), site="shop.example.com")
    assert store.find_script(title="checkout", site="shop.example.com").id == script.id
    assert store.find_script(title="checkout", site="other.com") is None


def test_mark_used(store):
    script = store.save_script(title="Flow", code=_steps(), site="github.com")
    used = store.mark_used(script.id)
    assert used.uses == 1
    assert used.last_used_at
    assert store.list_scripts()[0]["uses"] == 1


def test_delete_is_soft(store):
    script = store.save_script(title="Flow", code=_steps(), site="github.com")
    assert store.delete_script(script.id)
    assert store.get_script(script.id) is None
    assert store.list_scripts() == []
    assert len(os.listdir(store.trash_path)) == 1


def test_index_is_rebuilt_when_missing(store):
    script = store.save_script(title="Flow", code=_steps(), site="github.com")
    os.remove(store.index_path)
    assert [entry["id"] for entry in store.list_scripts()] == [script.id]


def test_stats(store):
    store.save_script(title="A", code=_steps(), site="github.com")
    store.save_script(title="B", code=_steps(), site="amazon.com")
    stats = store.stats()
    assert stats["scripts"] == 2
    assert set(stats["sites"]) == {"github.com", "amazon.com"}