#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# setup.py
#
"""Request the current patch fromm a Yamaha Reface DX synthesizer and save it to a file."""

import argparse
import logging
import sys
import time
from datetime import datetime

from rtmidi.midiutil import open_midiinput, open_midioutput

from ..midiio import RefaceDX, TimeoutError
from ..util import get_patch_name


log = logging.getLogger(__name__)


def main(args=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        '-c',
        '--channel',
        type=int,
        default=1,
        help="MIDI channel to send program change to (default: %(default)s)")
    ap.add_argument(
        '-d',
        '--device',
        type=int,
        default=1,
        help="MIDI SysEx device number to send patch request for (default: %(default)s)")
    ap.add_argument(
        '-i',
        '--input-port',
        help="MIDI input port (default: ask)")
    ap.add_argument(
        '-o',
        '--output-port',
        help="MIDI output port (default: ask)")
    ap.add_argument(
        '-O',
        '--output-file',
        help="Filename for sysex patch dump output (default: patch name)")
    ap.add_argument(
        '-t',
        '--add-timestamp',
        action='store_true',
        help="Add timestamp to output file name.")
    ap.add_argument(
        '-n',
        '--add-program-number',
        action='store_true',
        help="Add program number to output file name as a prefix "
             "(requires specifying patch number).")
    ap.add_argument(
        'patch',
        nargs='?',
        type=int,
        help="Patch number (1..32) to request (default: current).")

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s - %(message)s")
    args = ap.parse_args(args if args is not None else sys.argv[1:])

    try:
        midiin, midiin_name = open_midiinput(args.input_port)
        midiout, midiout_name = open_midioutput(args.output_port)
    except (EOFError, KeyboardInterrupt):
        return 1

    channel = max(0, min(15, args.channel - 1))
    reface = RefaceDX(midiin, midiout, channel=channel)

    if args.patch:
        patchno = max(0, min(31, args.patch - 1))
        log.info("Sending program change %i ...", patchno)
        reface.send_program_change(patchno)
        time.sleep(0.1)

    try:
        patch = reface.patch_request(args.device)
    except TimeoutError:
        return "Did not receive patch dump."
    else:
        patch_name = get_patch_name(patch)

        if args.output_file:
            outfn = args.output_file
        else:
            outfn = patch_name.replace(' ', '_')
            outfn = outfn.replace('?', '_')
            outfn = outfn.replace('*', '_')
            outfn = outfn.replace(':', '_')

            if args.add_timestamp:
                outfn += '_%s.syx' % datetime.now().strftime('%Y%m%d-%H%M%S')
            else:
                outfn += '.syx'

            if args.patch and args.add_program_number:
                outfn = '%02i-%s' % (patchno + 1, outfn)

        with open(outfn, 'wb') as sysex:
            log.info("Writing patch '%s' to file '%s'...", patch_name, outfn)
            sysex.write(patch)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]) or 0)
