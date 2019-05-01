#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# setup.py
#
"""Request and save SysEx patch dump(s) from a Yamaha Reface DX synthesizer."""

import argparse
import logging
import os.path
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
        help="MIDI channel to send program change(s) to (default: %(default)s)")
    ap.add_argument(
        '-d',
        '--device',
        type=int,
        default=1,
        help="MIDI SysEx device number to send patch request for (default: %(default)s).")
    ap.add_argument(
        '-i',
        '--input-port',
        metavar='PORT',
        nargs='?',
        default='reface DX',
        const=None,
        help="MIDI input port. May be a port number or port name sub-string or the option value "
             "may be omitted, then the input port can be selected interactively "
             "(default: '%(default)s').")
    ap.add_argument(
        '-n',
        '--add-program-number',
        action='store_true',
        help="Prefix output file name with patch number (requires specifying patch number).")
    ap.add_argument(
        '-o',
        '--output-port',
        metavar='PORT',
        nargs='?',
        default='reface DX',
        const=None,
        help="MIDI output port. May be a port number or port name sub-string or the option value "
             "may be omitted, then the input port can be selected interactively "
             "(default: '%(default)s').")
    ap.add_argument(
        '-f',
        '--filename',
        help="Filename for sysex patch dump output (default: '<patch name>.syx').")
    ap.add_argument(
        '-q',
        '--quiet',
        action='store_true',
        help="Do not print messages except errors.")
    ap.add_argument(
        '-r',
        '--replace',
        action='store_true',
        help="Replace existing output file(s) (default: no).")
    ap.add_argument(
        '-t',
        '--add-timestamp',
        action='store_true',
        help="Add timestamp to output file name.")
    ap.add_argument(
        'patches',
        nargs='*',
        help="Patches to request. Each argument can be a patch number (1 to 32) or a patch number "
             "range (e.g. '9-16'). If no positional arguments are given, the current patch is "
             "requested.")

    args = ap.parse_args(args if args is not None else sys.argv[1:])
    logging.basicConfig(level=logging.WARN if args.quiet else logging.INFO,
                        format="%(levelname)s - %(message)s")

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
                if '-' in patchspec:
                    lo, hi = [int(i) for i in patchspec.split('-', 1)]
                    patches.update(range(lo, hi+1))
                else:
                    patches.add(int(patchspec))
            except (TypeError, ValueError):
                log.error("Invalid argument: %s", patchspec)

        args.patches = sorted(list(patches))

    for patchno in args.patches or [None]:
        if patchno is not None:
            if 32 >= patchno >= 1:
                log.info("Sending program change #%i on channel %i...", patchno - 1, channel)
                reface.send_program_change(patchno - 1)
                time.sleep(0.1)
            else:
                log.error("Skipping patch number %i, which is out of range (1..32).", patchno)
                continue

        try:
            log.info("Sending patch dump request ...")
            patch = reface.patch_request(args.device)
        except TimeoutError:
            log.error("Did not receive patch dump within timeout.")
        else:
            patch_name = get_patch_name(patch)

            if args.filename:
                outdir = os.path.dirname(args.filename)
                outfn = os.path.basename(args.filename)
            else:
                outdir = ''
                outfn = patch_name.replace(' ', '_')
                outfn = outfn.replace('?', '_')
                outfn = outfn.replace('*', '_')
                outfn = outfn.replace(':', '_')

            if args.add_timestamp:
                outfn += '_%s' % datetime.now().strftime('%Y%m%d-%H%M%S')

            if not outfn.endswith('.syx'):
                outfn += '.syx'

            if patchno and args.add_program_number:
                outfn = '%02i-%s' % (patchno, outfn)

            outpath = os.path.join(outdir, outfn)

            if os.path.exists(outpath):
                if args.replace:
                    log.warn("Existing output file '%s' will be overwritten.", outpath)
                else:
                    log.warn("Existing output file '%s' will not be overwritten.", outpath)
                    continue

            with open(outpath, 'wb') as sysex:
                log.info("Writing patch '%s' to file '%s'...", patch_name, outpath)
                sysex.write(patch)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]) or 0)
