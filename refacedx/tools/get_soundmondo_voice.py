#!/usr/bin/env python
"""Download voice data from Soundmondo and save it as a SysEx file.

Optionally send it via MIDI to the Reface DX.

"""

import argparse
import logging
import re
import string
import sys
import time

from os.path import basename, exists
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


__appname__ = "refacedx-tools"
__appauthor__ = "chrisarndt.de"
log = logging.getLogger("get-soundmondo-voice")
SOUNDMONDO_URL = "https://soundmondo.yamahasynth.com/"
API_BASE_URL = pjoin(SOUNDMONDO_URL, "api/v1")
VOICE_PAGE_URL_RX = re.compile(pjoin(SOUNDMONDO_URL, r"voices/(?P<voice_id>\d+)/?$"))
END_OF_EXCLUSIVE = b"\xF7"
SYSTEM_EXCLUSIVE = b"\xF0"
ILLEGAL_CHARS = r' \/:*"<>|'
ALLOWED_CHARS = set(string.printable).difference("\t\n\r\x0b\x0c" + ILLEGAL_CHARS)
MIDI_DEFAULT = object()


def sanitize_fn(fn, subst="_"):
    return "".join((c if c in ALLOWED_CHARS else "_") for c in fn)


def parse_voice_id(voice_id):
    if not isinstance(voice_id, str):
        return

    if voice_id.isdecimal():
        return voice_id

    match = VOICE_PAGE_URL_RX.match(voice_id)

    if match:
        return match.group("voice_id")


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
                        sysex_msg = data[sox : eox + 1]
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


def download_voice(voice_id):
    voice_url = pjoin(API_BASE_URL, "voices", voice_id) + "/"
    session = requests.session()

    if cachecontrol:
        session = cachecontrol.CacheControl(
            session,
            cache=FileCache(user_cache_dir(__appname__, __appauthor__), forever=True),
            heuristic=ExpiresAfter(days=14),
        )

    resp = session.get(voice_url, headers={"Accept": "application/json"})

    if resp.status_code != 200:
        raise IOError(
            "Failed to retrieve voice data from '%s': %s" % (voice_url, resp.reason)
        )

    log.debug(
        "Response headers:\n%s",
        "\n".join("%s: %s" % (name, value) for name, value in resp.headers.items()),
    )

    messages = []
    try:
        data = resp.json()
        for i, part in enumerate(data["data"]["sysex"]):
            msg = bytearray(v for _, v in sorted(part.items(), key=lambda i: int(i[0])))
            log.debug("Mgs #%02i: %s", i, " ".join("%0X" % b for b in msg))
            messages.append(msg)
    except (KeyError, TypeError, ValueError) as exc:
        raise IOError("Unexpected response data format: %s" % exc)
    else:
        del data["data"]
        data["messages"] = messages

    return data


def write_sysex_to_file(fobj, messages):
    for msg in messages:
        fobj.write(msg)


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    padd = parser.add_argument
    padd(
        "-d",
        "--delay",
        default="50",
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
        const=MIDI_DEFAULT,
        help="Send downloaded voice SysEx data or SysEx file to MIDI output",
    )
    padd(
        "-o",
        "--output-file",
        metavar="PATH",
        help="Path of output file to write SysEx data to (default: patch name + '.syx')",
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
        default="reface DX",
        help="MIDI output port name or number (default: %(default)r)",
    )
    padd(
        "-r",
        "--replace",
        action="store_true",
        help="Replace existing output file(s) (default: no)",
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

    if not args.voice_id and args.send_midi is MIDI_DEFAULT:
        log.error(
            "Option '-m/--midi' requires input file argument if no positional argument is given."
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

        if not args.output_file:
            args.output_file = sanitize_fn(data["name"]) + ".syx"

        if not args.no_file_output:
            if args.output_file == "-":
                write_sysex_to_file(fp, sys.stdout)
            elif not args.replace and exists(args.output_file):
                log.error(
                    "Output file '%s' exist. Use option '-f/--force' to overwrite.",
                    args.output_file,
                )
                return 1
            else:
                with open(args.output_file, "wb") as fp:
                    log.info("Writing voice '%s' SysEx data to '%s'.", data['name'], args.output_file)
                    write_sysex_to_file(fp, data["messages"])

    if args.send_midi:
        try:
            midiout, portname = open_midioutput(
                args.port, interactive=False, use_virtual=False
            )
        except rtmidi.InvalidPortError:
            log.error("Invalid MIDI port number or name.")
            log.error("Use '-l' option to list MIDI ports.")
            return 2
        except rtmidi.RtMidiError as exc:
            log.error(exc)
            return 1

        if args.voice_id:
            with midiout:
                log.info("Sending voice '%s' SysEx data to '%s'.", data['name'], portname)
                for i, msg in enumerate(data["messages"]):
                    log.debug("Sending message #%03i...", i)
                    midiout.send_message(msg)
                    time.sleep(0.001 * args.delay)
        elif args.send_midi is not MIDI_DEFAULT:
            try:
                with midiout:
                    send_sysex_file(args.send_midi, midiout, portname, args.delay)
            except Exception as exc:
                log.error("Error sending SysEx data: %s", args.send_midi, exc)

        del midiout


if __name__ == "__main__":
    sys.exit(main() or 0)
