"""
Crowdcast control panel for OBS Studio
=======================================

Puts a settings panel for the Crowdcast overlay (index.html) right inside
OBS, instead of making you open the browser source's page to change
anything. It runs a tiny local web server for the Crowdcast folder and
drives the page entirely through URL query parameters — no browser
extensions, no CEF scripting tricks, just a URL OBS's browser source can
load like any other.

Install
-------
1. In OBS: Tools > Scripts > the "+" button > select this file
   (obs_crowdcast.py). OBS needs a Python install configured under the
   "Python Settings" tab first (Windows/Linux; macOS OBS ships its own).
2. In the script's properties (right side of the Scripts window):
     - "Crowdcast folder" -> point this at the folder containing
       index.html (the one this script shipped alongside).
     - Click "Create Crowdcast source" to add a ready-sized Browser
       Source to your current scene, or pick an existing browser source
       from the dropdown if you already added one by hand.
     - Set topic, streamer name, pace, text size, theme, starting
       viewer count, and overlay mode.
     - Click "Apply to browser source" (or just change a dropdown —
       most fields apply immediately).
3. Theme can be a fixed color or "Auto", which dayparts across four
   accents by the OBS machine's local clock (morning/day/evening/night)
   so a long stream doesn't sit under one static color all night.

This script only talks to OBS and to a web server it runs on your own
machine (127.0.0.1) — it makes no outside network connections itself.
The Crowdcast page's own font request is the only external call, made
by the browser source's Chromium, not by this script.
"""

import obspython as obs
import http.server
import threading
import socket
import os
import urllib.parse

# ---------------------------------------------------------------------
# State
# ---------------------------------------------------------------------

httpd = None
http_thread = None
served_dir = None
served_port = None

S = {
    "folder": "",
    "port": 8642,
    "source": "",
    "topic": "the stream",
    "streamer": "the streamer",
    "pace": "normal",
    "size": "14",
    "theme": "auto",
    "viewers": 1284,
    "overlay": False,
}

PACE_ITEMS = [("Chill", "chill"), ("Normal", "normal"), ("Hype", "hype")]
SIZE_ITEMS = [("Small", "13"), ("Medium", "14"), ("Large", "17")]
THEME_ITEMS = [
    ("Auto (follows time of day)", "auto"),
    ("Amber", "#ffb454"),
    ("Sky", "#7dd3fc"),
    ("Orchid", "#e2a6ff"),
    ("Mint", "#7ee2a8"),
]

SOURCE_ID = "browser_source"


# ---------------------------------------------------------------------
# Local web server — serves the Crowdcast folder on 127.0.0.1 so the
# browser source can load it with a query string attached. Plain
# file:// URLs work in most OBS versions too, but a real HTTP origin
# sidesteps the handful of Chromium quirks around local files and
# fonts, and is the pattern most OBS overlay tools use.
# ---------------------------------------------------------------------

class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep the OBS script log clean


def _start_server(folder, port):
    global httpd, http_thread, served_dir, served_port
    _stop_server()
    if not folder or not os.path.isdir(folder):
        print("[Crowdcast] no valid folder set yet, not starting server")
        return
    try:
        handler = lambda *args, **kwargs: _QuietHandler(*args, directory=folder, **kwargs)
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError as e:
        print("[Crowdcast] could not bind 127.0.0.1:%d (%s) — pick a different port" % (port, e))
        httpd = None
        return
    http_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    http_thread.start()
    served_dir = folder
    served_port = port
    print("[Crowdcast] serving %s at http://127.0.0.1:%d/" % (folder, port))


def _stop_server():
    global httpd, http_thread, served_dir, served_port
    if httpd is not None:
        try:
            httpd.shutdown()
            httpd.server_close()
        except Exception:
            pass
    httpd = None
    http_thread = None
    served_dir = None
    served_port = None


def _server_ready_for(folder, port):
    return httpd is not None and served_dir == folder and served_port == port


# ---------------------------------------------------------------------
# Building the URL and pushing it into the browser source
# ---------------------------------------------------------------------

def _build_url():
    params = {
        "topic": S["topic"],
        "streamer": S["streamer"],
        "pace": S["pace"],
        "size": S["size"],
        "accent": S["theme"],
        "viewers": str(S["viewers"]),
        "overlay": "1" if S["overlay"] else "0",
    }
    return "http://127.0.0.1:%d/index.html?%s" % (S["port"], urllib.parse.urlencode(params))


def _find_source(name):
    if not name:
        return None
    return obs.obs_get_source_by_name(name)


def _refresh_browser(source):
    # Forces a reload even when the URL string is unchanged, using the
    # "refresh" procedure the browser source plugin registers on itself.
    ph = obs.obs_source_get_proc_handler(source)
    if ph is None:
        return
    cd = obs.calldata_create()
    obs.proc_handler_call(ph, "refresh", cd)
    obs.calldata_destroy(cd)


def apply_to_source():
    if not _server_ready_for(S["folder"], S["port"]):
        _start_server(S["folder"], S["port"])
    if not _server_ready_for(S["folder"], S["port"]):
        return  # folder still not valid — nothing to point the source at

    source = _find_source(S["source"])
    if source is None:
        print("[Crowdcast] no browser source selected yet")
        return

    url = _build_url()
    settings = obs.obs_source_get_settings(source)
    obs.obs_data_set_bool(settings, "is_local_file", False)
    obs.obs_data_set_string(settings, "url", url)
    obs.obs_source_update(source, settings)
    obs.obs_data_release(settings)
    _refresh_browser(source)
    obs.obs_source_release(source)


def _enum_browser_sources():
    names = []
    sources = obs.obs_enum_sources()
    if sources is not None:
        for s in sources:
            if obs.obs_source_get_unversioned_id(s) == SOURCE_ID:
                names.append(obs.obs_source_get_name(s))
        obs.source_list_release(sources)
    return names


# ---------------------------------------------------------------------
# Button callbacks
# ---------------------------------------------------------------------

def _create_source_clicked(props, prop):
    folder = S["folder"]
    if not folder or not os.path.isdir(folder):
        print("[Crowdcast] set the Crowdcast folder before creating a source")
        return False
    if not os.path.isfile(os.path.join(folder, "index.html")):
        print("[Crowdcast] no index.html found in that folder")
        return False

    _start_server(folder, S["port"])
    if not _server_ready_for(folder, S["port"]):
        return False

    scene_source = obs.obs_frontend_get_current_scene()
    if scene_source is None:
        print("[Crowdcast] no active scene to add the source to")
        return False
    scene = obs.obs_scene_from_source(scene_source)

    settings = obs.obs_data_create()
    obs.obs_data_set_string(settings, "url", _build_url())
    obs.obs_data_set_bool(settings, "is_local_file", False)
    obs.obs_data_set_int(settings, "width", 460)
    obs.obs_data_set_int(settings, "height", 640)
    obs.obs_data_set_bool(settings, "reroute_audio", False)

    name = "Crowdcast"
    existing = obs.obs_get_source_by_name(name)
    n = 2
    while existing is not None:
        obs.obs_source_release(existing)
        name = "Crowdcast %d" % n
        existing = obs.obs_get_source_by_name(name)
        n += 1

    source = obs.obs_source_create(SOURCE_ID, name, settings, None)
    obs.obs_scene_add(scene, source)
    obs.obs_data_release(settings)
    obs.obs_source_release(source)
    obs.obs_source_release(scene_source)

    S["source"] = name
    print("[Crowdcast] created browser source \"%s\"" % name)
    return True  # ask OBS to rebuild the properties list so the dropdown includes it


def _apply_clicked(props, prop):
    apply_to_source()
    return False


def _refresh_sources_clicked(props, prop):
    return True  # just triggers script_properties() to re-run


# ---------------------------------------------------------------------
# OBS script hooks
# ---------------------------------------------------------------------

def script_description():
    return (
        "<b>Crowdcast</b><br>"
        "Settings panel for the Crowdcast live-chat overlay. Point this at the "
        "folder holding index.html, create or pick a browser source, and "
        "everything below pushes straight to it.<br><br>"
        "Theme \"Auto\" changes the accent color across the day (morning/day/"
        "evening/night) using this computer's clock."
    )


def script_properties():
    props = obs.obs_properties_create()

    obs.obs_properties_add_path(
        props, "folder", "Crowdcast folder (containing index.html)",
        obs.OBS_PATH_DIRECTORY, "*.*", None
    )
    obs.obs_properties_add_int(props, "port", "Local server port", 1024, 65535, 1)

    src_list = obs.obs_properties_add_list(
        props, "source", "Browser source",
        obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING
    )
    obs.obs_property_list_add_string(src_list, "(none selected)", "")
    for name in _enum_browser_sources():
        obs.obs_property_list_add_string(src_list, name, name)

    obs.obs_properties_add_button(props, "create_btn", "Create Crowdcast source", _create_source_clicked)
    obs.obs_properties_add_button(props, "refresh_btn", "Refresh source list", _refresh_sources_clicked)

    obs.obs_properties_add_text(props, "topic", "Stream topic", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "streamer", "Streamer's name", obs.OBS_TEXT_DEFAULT)

    pace_list = obs.obs_properties_add_list(props, "pace", "Chat pace", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    for label, val in PACE_ITEMS:
        obs.obs_property_list_add_string(pace_list, label, val)

    size_list = obs.obs_properties_add_list(props, "size", "Text size", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    for label, val in SIZE_ITEMS:
        obs.obs_property_list_add_string(size_list, label, val)

    theme_list = obs.obs_properties_add_list(props, "theme", "Theme", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
    for label, val in THEME_ITEMS:
        obs.obs_property_list_add_string(theme_list, label, val)

    obs.obs_properties_add_int(props, "viewers", "Starting viewer count", 3, 999999, 1)
    obs.obs_properties_add_bool(props, "overlay", "Overlay mode (hide panel chrome)")

    obs.obs_properties_add_button(props, "apply_btn", "Apply to browser source", _apply_clicked)

    return props


def script_defaults(settings):
    obs.obs_data_set_default_int(settings, "port", 8642)
    obs.obs_data_set_default_string(settings, "topic", S["topic"])
    obs.obs_data_set_default_string(settings, "streamer", S["streamer"])
    obs.obs_data_set_default_string(settings, "pace", S["pace"])
    obs.obs_data_set_default_string(settings, "size", S["size"])
    obs.obs_data_set_default_string(settings, "theme", S["theme"])
    obs.obs_data_set_default_int(settings, "viewers", S["viewers"])
    obs.obs_data_set_default_bool(settings, "overlay", S["overlay"])


def script_update(settings):
    S["folder"] = obs.obs_data_get_string(settings, "folder")
    S["port"] = obs.obs_data_get_int(settings, "port") or 8642
    S["source"] = obs.obs_data_get_string(settings, "source")
    S["topic"] = obs.obs_data_get_string(settings, "topic") or "the stream"
    S["streamer"] = obs.obs_data_get_string(settings, "streamer") or "the streamer"
    S["pace"] = obs.obs_data_get_string(settings, "pace") or "normal"
    S["size"] = obs.obs_data_get_string(settings, "size") or "14"
    S["theme"] = obs.obs_data_get_string(settings, "theme") or "auto"
    S["viewers"] = obs.obs_data_get_int(settings, "viewers") or 1284
    S["overlay"] = obs.obs_data_get_bool(settings, "overlay")

    if S["folder"]:
        _start_server(S["folder"], S["port"])
    apply_to_source()


def script_load(settings):
    if S["folder"]:
        _start_server(S["folder"], S["port"])


def script_unload():
    _stop_server()
