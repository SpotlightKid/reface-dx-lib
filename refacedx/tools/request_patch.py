#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# setup.py
#
"""Request and save SysEx patch dump(s) from a Yamaha Reface DX synthesizer."""

import argparse
import logging
import string
import sys
import time

from datetime import datetime
from os.path import exists, splitext

from rtmidi.midiutil import open_midiinput, open_midioutput

from ..midiio import RefaceDX, TimeoutError
from ..util import get_patch_name


log = logging.getLogger(__name__)


ILLEGAL_CHARS = r'\/:*"<>|'
ALLOWED_CHARS = set(string.printable).difference("\t\n\r\x0b\x0c" + ILLEGAL_CHARS)
PATH_SUBST_KEYS = (
    "day",
    "hour",
    "minute",
    "month",
    "name",
    "program",
    "second",
    "slot",
    "year",
)
DATE_KEYS = ("year", "month", "day", "hour", "minute", "second")


def sanitize_fn(fn, subst="_"):
    return "".join((c if c in ALLOWED_CHARS else "_") for c in fn)


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


def main(args=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "-c",
        "--channel",
        type=int,
        default=1,
        help="MIDI channel to send program change(s) to (default: %(default)s)",
    )
    ap.add_argument(
        "-d",
        "--device",
        type=int,
        default=1,
        help="MIDI SysEx device number to send patch request for (default: %(default)s).",
    )
    ap.add_argument(
        "-i",
        "--input-port",
        metavar="PORT",
        nargs="?",
        default="reface DX",
        const=None,
        help="MIDI input port. May be a port number or port name sub-string or the option value "
        "may be omitted, then the input port can be selected interactively "
        "(default: '%(default)s').",
    )
    ap.add_argument(
        "-o",
        "--output-port",
        metavar="PORT",
        nargs="?",
        default="reface DX",
        const=None,
        help="MIDI output port. May be a port number or port name sub-string or the option value "
        "may be omitted, then the output port can be selected interactively "
        "(default: '%(default)s').",
    )
    ap.add_argument(
        "-f",
        "--output-path",
        metavar="PATH",
        default="{name}.syx",
        help="Path of output file to write SysEx data to (default: '%(default)s')",
    )
    ap.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Do not print messages except errors.",
    )
    ap.add_argument(
        "-r",
        "--replace",
        action="store_true",
        help="Replace existing output file(s) (default: no).",
    )
    ap.add_argument(
        "patches",
        nargs="*",
        help="Patches to request. Each argument can be a program number (1 to 32) or a program "
        "number range (e.g. '9-16'). If no positional arguments are given, the patch in the "
        "current edit buffer is requested.",
    )

    args = ap.parse_args(args if args is not None else sys.argv[1:])
    logging.basicConfig(
        level=logging.WARN if args.quiet else logging.INFO,
        format="%(levelname)s - %(message)s",
    )

    try:
        midiin, midiin_name = open_midiinput(args.input_port)
        midiout, midiout_name = open_midioutput(args.output_port)
    except (EOFError, KeyboardInterrupt):
        return 1

    channel = max(1, min(16, args.channel))
    reface = RefaceDX(midiin, midiout, channel=channel - 1)

    if args.patches:
        patches = set()
        for patchspec in args.patches:
            try:
                if "-" in patchspec:
                    lo, hi = [int(i) for i in patchspec.split("-", 1)]
                    patches.update(range(lo, hi + 1))
                else:
                    patches.add(int(patchspec))
            except (TypeError, ValueError):
                log.error("Invalid argument: %s", patchspec)

        args.patches = sorted(list(patches))

    for patchno in args.patches or [None]:
        if patchno is not None:
            if 32 >= patchno >= 1:
                log.info(
                    "Sending program change #%i on channel %i...", patchno - 1, channel
                )
                reface.send_program_change(patchno - 1)
                time.sleep(0.1)
            else:
                log.error(
                    "Skipping patch number %i, which is out of range (1..32).", patchno
                )
                continue

        try:
            log.info("Sending patch dump request ...")
            patch = reface.patch_request(args.device)
        except TimeoutError:
            log.error("Did not receive patch dump within timeout.")
        else:
            now = datetime.now()
            data = {name: getattr(now, name) for name in DATE_KEYS}
            data["name"] = get_patch_name(patch)

            if patchno is not None:
                data["program"] = patchno
                data["slot"] = "{}-{}".format((patchno - 1) // 8 + 1, (patchno - 1) % 8 + 1)

            output_path = build_path(args.output_path, **data)
            log.info("Output path (after substitution): %s", output_path)

            if not splitext(output_path)[1]:
                output_path += ".syx"

            if exists(output_path):
                if args.replace:
                    log.warn(
                        "Existing output file '%s' will be overwritten.", output_path
                    )
                else:
                    log.warn(
                        "Existing output file '%s' will not be overwritten.",
                        output_path,
                    )
                    continue

            with open(output_path, "wb") as sysex:
                log.info("Writing patch '%s' to file '%s'...", data["name"], output_path)
                sysex.write(patch)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) or 0)
