#!/usr/bin/env python
"""Download voice data from Soundmondo and save it as a SysEx file.

Optionally send it via MIDI to the Reface DX.

"""

import argparse
import logging
import os
import re
import string
import sys
import time

from datetime import datetime
from os.path import basename, dirname, exists, splitext, split as pathsplit
from posixpath import join as pjoin

import requests
import rtmidi
from rtmidi.midiutil import list_output_ports, open_midioutput

try:
    import cachecontrol
    from cachecontrol.caches.file_cache import FileCache
except ImportError:
    cachecontrol = None
else:
    from appdirs import user_cache_dir
    from cachecontrol.heuristics import ExpiresAfter


__appname__ = "reface-dx-lib"
__appauthor__ = "chrisarndt.de"

SOUNDMONDO_URL = "https://soundmondo.yamahasynth.com/"
API_BASE_URL = pjoin(SOUNDMONDO_URL, "api/v1")
VOICE_PAGE_URL_RX = re.compile(pjoin(SOUNDMONDO_URL, r"voices/(?P<voice_id>\d+)/?$"))
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
END_OF_EXCLUSIVE = b"\xF7"
SYSTEM_EXCLUSIVE = b"\xF0"
ILLEGAL_CHARS = r'\/:*"<>|'
ALLOWED_CHARS = set(string.printable).difference("\t\n\r\x0b\x0c" + ILLEGAL_CHARS)
OPTION_DEFAULT = object()
PATH_SUBST_KEYS = (
    "day",
    "hour",
    "id",
    "minute",
    "month",
    "name",
    "reface",
    "second",
    "user",
    "user_id",
    "year",
)
DATE_KEYS = ("year", "month", "day", "hour", "minute", "second")

_http_session = None
log = logging.getLogger("get-soundmondo-voice")


def build_path(path, **data):
    subst = {}
    for key in PATH_SUBST_KEYS:
        value = data.get(key)
        if isinstance(value, str):
            subst[key] = sanitize_fn(value)
        elif isinstance(value, int):
            subst[key] = value
        else:
            subst[key] = ""

    return path.format(**subst)


def download_voice(voice_id):
    voice_url = pjoin(API_BASE_URL, "voices", voice_id) + "/"
    resp = get_http_session().get(voice_url, headers={"Accept": "application/json"})

    if resp.status_code != 200:
        raise IOError(
            "Failed to retrieve voice data from '%s': %s" % (voice_url, resp.reason)
        )

    log.debug(
        "Response headers:\n%s",
        "\n".join("%s: %s" % (name, value) for name, value in resp.headers.items()),
    )

    try:
        data = resp.json()
        log.debug("Response data:\n%s", format_reponse_log(data))
        messages = parse_sysex_messages(data["data"]["sysex"])
        del data["data"]
    except (KeyError, TypeError, ValueError) as exc:
        raise IOError("Unexpected response data format: %s" % exc)
    else:
        data["messages"] = messages

    return data


def get_http_session():
    global _http_session

    if _http_session is None:
        _http_session = requests.session()

        if cachecontrol:
            _http_session = cachecontrol.CacheControl(
                _http_session,
                cache=FileCache(
                    user_cache_dir(__appname__, __appauthor__), forever=True
                ),
                heuristic=ExpiresAfter(days=14),
            )

    return _http_session


def get_user_info(user_url):
    resp = get_http_session().get(user_url, headers={"Accept": "application/json"})

    if resp.status_code != 200:
        raise IOError(
            "Failed to retrieve user information from '%s': %s"
            % (user_url, resp.reason)
        )

    log.debug(
        "Response headers:\n%s",
        "\n".join("%s: %s" % (name, value) for name, value in resp.headers.items()),
    )

    try:
        return resp.json()
    except (KeyError, TypeError, ValueError) as exc:
        raise IOError("Unexpected response data format: %s" % exc)


def format_reponse_log(data):
    import copy
    import json
    data = copy.deepcopy(data)
    data["data"]["sysex"] = ["..."]
    return json.dumps(data, indent=2)


def parse_sysex_messages(data):
    messages = []

    for i, part in enumerate(data):
        msg = bytearray(v for _, v in sorted(part.items(), key=lambda i: int(i[0])))
        log.debug("SysEx msg #%02i: %s", i, " ".join("%02X" % b for b in msg))
        messages.append(msg)

    return messages

def parse_timestamp(datetimestr):
    try:
        dt = datetime.strptime(datetimestr, DATE_FORMAT)
    except (TypeError, ValueError):
        return {}
    else:
        return {name: getattr(dt, name) for name in DATE_KEYS}


def parse_voice_id(voice_id):
    if not isinstance(voice_id, str):
        return

    if voice_id.isdecimal():
        return voice_id

    match = VOICE_PAGE_URL_RX.match(voice_id)

    if match:
        return match.group("voice_id")


def sanitize_fn(fn, subst="_"):
    return "".join((c if c in ALLOWED_CHARS else "_") for c in fn)


def send_sysex_file(filename, midiout, portname, delay=50):
    """Send contents of SysEx file to given MIDI output.

    Reads file given by filename and sends all consecutive SysEx messages found
    in it to given midiout.

    """
    bn = basename(filename)

    with open(filename, "rb") as sysex_file:
        data = sysex_file.read()

        if data.startswith(SYSTEM_EXCLUSIVE):
            sox = 0
            i = 0

            log.info("Sending SysEx file '%s' data to '%s'.", filename, portname)
            while sox >= 0:
                sox = data.find(SYSTEM_EXCLUSIVE, sox)

                if sox >= 0:
                    eox = data.find(END_OF_EXCLUSIVE, sox)

                    if eox >= 0:
                        sysex_msg = data[sox:eox + 1]
                        # Python 2: convert data into list of integers
                        if isinstance(sysex_msg, str):
                            sysex_msg = [ord(c) for c in sysex_msg]

                        log.debug("Sending '%s' message #%03i...", bn, i)
                        midiout.send_message(sysex_msg)
                        time.sleep(0.001 * delay)

                        i += 1
                    else:
                        break

                    sox = eox + 1
        else:
            log.warning("File '%s' does not start with a SysEx message.", bn)



def write_sysex_to_file(fobj, messages):
    for msg in messages:
        fobj.write(msg)


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    padd = parser.add_argument
    padd(
        "-d",
        "--delay",
        default="10",
        metavar="MS",
        type=int,
        help="Delay between sending each SysEx message in milliseconds "
        "(default: %(default)s)",
    )
    padd(
        "-l",
        "--list-ports",
        action="store_true",
        help="List available MIDI output ports",
    )
    padd(
        "-m",
        "--send-midi",
        metavar="FILE",
        nargs="?",
        const=OPTION_DEFAULT,
        help="Send downloaded voice SysEx data or SysEx file to MIDI output",
    )
    padd(
        "-f",
        "--output-path",
        metavar="PATH",
        default="{name}.syx",
        help="Path of output file to write SysEx data to (default: '%(default)s')",
    )
    padd(
        "-O",
        "--no-file-output",
        action="store_true",
        help="Don't write SysEx data to file (requires option '-m/--midi')",
    )
    padd(
        "-p",
        "--port",
        metavar="PORT",
        nargs="?",
        default="reface DX",
        const=None,
        help="MIDI output port. May be a port number or port name sub-string "
        "or the option value may be omitted, then the output port can be "
        "selected interactively (default: '%(default)s').",
    )
    padd(
        "-r",
        "--replace",
        action="store_true",
        help="Replace existing output file (default: no)",
    )
    padd("-v", "--debug", action="store_true", help="Enable debug logging")
    padd("voice_id", metavar="ID", nargs="?", help="URL or ID of voice to download")
    args = parser.parse_args(args)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.list_ports:
        try:
            list_output_ports()
        except rtmidi.RtMidiError as exc:
            log.error(exc)
            return 1

        return 0

    if not args.voice_id and args.send_midi is OPTION_DEFAULT:
        log.error(
            "Option '-m/--midi' requires input file argument if no positional "
            "argument is given."
        )
        print()
        parser.print_help()
        return 2

    if args.voice_id:
        vid = parse_voice_id(args.voice_id)
        if not vid:
            log.error("Invalid voice ID or URL: %s", args.voice_id)
            return 1

        try:
            data = download_voice(vid)
        except Exception as exc:
            log.error("Error downloading voice %s: %s", vid, exc)
            return 1
        else:
            data.update(parse_timestamp(data.get("updated")))

        if not args.no_file_output:
            if "{user" in args.output_path:
                try:
                    user_info = get_user_info(data["user"])
                except Exception as exc:
                    log.error("Error downloading user information: %s", exc)
                    return 1
                else:
                    data["user"] = user_info.get(
                        "display_name", "user-{}".format(user_info["id"])
                    )
                    data["user_id"] = user_info["id"]

            output_path = build_path(args.output_path, **data)
            log.debug("Output path (after substitution): %s", output_path)

            if output_path == "-":
                write_sysex_to_file(sys.stdout, data["messages"])
            else:
                if not splitext(output_path)[1]:
                    output_path += ".syx"

                if not args.replace and exists(output_path):
                    log.error(
                        "Output path '%s' exist. Use option '-f/--force' to overwrite.",
                        args.output_path,
                    )
                    return 1
                else:
                    head, tail = pathsplit(output_path)
                    if head and not exists(head):
                        os.makedirs(dirname(head))

                    with open(output_path, "wb") as fp:
                        log.info(
                            "Writing voice '%s' SysEx data to '%s'.",
                            data["name"],
                            output_path,
                        )
                        write_sysex_to_file(fp, data["messages"])

    if args.send_midi:
        try:
            midiout, portname = open_midioutput(args.port)
        except rtmidi.InvalidPortError:
            log.error("Invalid MIDI port number or name.")
            log.error("Use '-l' option to list MIDI ports.")
            return 2
        except rtmidi.RtMidiError as exc:
            log.error(exc)
            return 1

        if args.voice_id:
            with midiout:
                log.info(
                    "Sending voice '%s' SysEx data to '%s'.", data["name"], portname
                )
                for i, msg in enumerate(data["messages"]):
                    time.sleep(0.001 * args.delay)
                    log.debug("Sending message #%03i...", i)
                    midiout.send_message(msg)
        elif args.send_midi is not OPTION_DEFAULT:
            try:
                with midiout:
                    send_sysex_file(args.send_midi, midiout, portname, args.delay)
            except Exception as exc:
                log.error("Error sending SysEx data: %s", args.send_midi, exc)

        del midiout


if __name__ == "__main__":
    sys.exit(main() or 0)
