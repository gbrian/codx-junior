"""Image library catalog, resolution and per-provider Docker commands."""

from codx.junior.browser.model import BrowserSession
from codx.junior.computer.images import (
    DEFAULT_KASM_TAG,
    list_images,
    list_image_tags,
    resolve_image,
)


def test_library_offers_kasmweb_and_linuxserver():
    kasm = list_images(provider="kasmweb")
    linuxserver = list_images(provider="linuxserver")

    assert kasm and all(image.provider == "kasmweb" for image in kasm)
    assert linuxserver and all(image.provider == "linuxserver" for image in linuxserver)
    assert any(image.name == "Kasm Desktop" for image in kasm)
    assert any(image.tag == "debian-kde" for image in linuxserver)
    assert {image.live_view for image in kasm} == {"kasmvnc"}
    assert {image.live_view for image in linuxserver} == {"selkies"}


def test_legacy_kasm_images_pin_their_last_published_tag():
    """Kasm stopped shipping current tags for some legacy images.

    The catalog must surface the last tag that actually exists, otherwise the
    card looks selectable but the pull fails with "tag not found".
    """
    images = list_images(provider="kasmweb")
    teams = next(image for image in images if image.repository == "kasmweb/teams")

    assert teams.default_tag == "1.12.0"
    assert teams.image == "kasmweb/teams:1.12.0"
    assert "1.12.0" in teams.tags

    spec = resolve_image("kasmweb/teams")
    assert spec.tag == "1.12.0"
    assert spec.image == "kasmweb/teams:1.12.0"


def test_library_search_and_category_filters():
    desktop = list_images(provider="kasmweb", category="Desktop")
    vscode = list_images(provider="kasmweb", query="vs code")

    assert desktop and all(image.category == "Desktop" for image in desktop)
    assert vscode and vscode[0].repository == "kasmweb/vs-code"


def test_resolve_kasmweb_and_linuxserver_profiles():
    kasm = resolve_image("kasmweb/desktop:1.19.0")
    assert kasm.provider == "kasmweb"
    assert kasm.live_view == "kasmvnc"
    assert kasm.live_port == 6901
    assert kasm.live_scheme == "https"
    assert kasm.strip_prefix is True
    assert kasm.viewer_user == "kasm_user"
    assert kasm.image == "kasmweb/desktop:1.19.0"

    ls = resolve_image("lscr.io/linuxserver/webtop:ubuntu-xfce")
    assert ls.provider == "linuxserver"
    assert ls.live_view == "selkies"
    assert ls.live_port == 3000
    assert ls.live_scheme == "http"
    assert ls.strip_prefix is False
    assert ls.image == "lscr.io/linuxserver/webtop:ubuntu-xfce"

    default_kasm = resolve_image("kasmweb/desktop")
    assert default_kasm.tag == DEFAULT_KASM_TAG


def test_resolve_custom_image_is_screenshot_only():
    spec = resolve_image("ghcr.io/example/desktop:1.2")
    assert spec.provider == "custom"
    assert spec.live_view == "screenshot"
    assert spec.live_port is None
    assert spec.image == "ghcr.io/example/desktop:1.2"


def test_tags_fallback_without_network(monkeypatch):
    import codx.junior.computer.images as images

    def boom(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(images, "_cached_json", boom)
    tags = list_image_tags("kasmweb", "kasmweb/desktop")
    assert tags and tags[0].name == DEFAULT_KASM_TAG
    ls_tags = list_image_tags("linuxserver", "linuxserver/webtop")
    assert ls_tags and ls_tags[0].name == "debian-kde"


def test_kasm_container_command_uses_kasmvnc_profile(tmp_path, monkeypatch):
    from codx.junior.browser.docker_browser_manager import DockerBrowserManager

    manager = DockerBrowserManager(
        str(tmp_path),
        traefik_domain="example.test",
        project_id="project-1",
        project_root_path=str(tmp_path / "project"),
        project_name="proj",
    )
    (tmp_path / "project").mkdir(exist_ok=True)
    monkeypatch.setattr(manager, "_ensure_image", lambda image=None: None)
    monkeypatch.setattr(manager, "_prepare_computer_agent", lambda sid: "/tmp/agent.py")

    session = BrowserSession(name="Kasm", kind="linux", image="kasmweb/desktop:1.19.0")
    session.id = "52345678-aaaa-bbbb-cccc-ddddeeeeffff"
    manager.configure_share(session, share_project=False)
    manager._apply_image_profile(session)
    assert session.image_provider == "kasmweb"
    assert session.viewer_password
    cmd = manager._build_kasm_run_command(
        session,
        "computer_52345678",
        str(tmp_path / "profile"),
        f"/computer/{session.id}/",
        "codx-computer-52345678",
    )
    joined = " ".join(cmd)

    assert "kasmweb/desktop:1.19.0" in cmd
    assert f"VNC_PW={session.viewer_password}" in cmd
    assert "--user" in cmd
    assert "/tmp/agent.py:/codx/computer_agent.py:ro" in cmd
    assert "loadbalancer.server.port=6901" in joined
    assert "loadbalancer.server.scheme=https" in joined
    assert "codx-insecure@http" in joined
    assert "stripprefix.prefixes=/computer/" + session.id in joined
    assert "customrequestheaders.Authorization=Basic " in joined


def test_traefik_labels_for_selkies_are_not_stripped(tmp_path):
    from codx.junior.browser.docker_browser_manager import DockerBrowserManager

    manager = DockerBrowserManager(str(tmp_path), traefik_domain="example.test")
    labels = manager._build_traefik_labels(
        router_name="codx-browser-x",
        session_id="x",
        path_prefix="/browser/x/",
    )
    joined = "\n".join(labels)
    assert "server.port=3000" in joined
    assert "server.scheme=http" in joined
    assert "stripprefix" not in joined
