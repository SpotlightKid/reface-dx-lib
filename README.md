Yamaha Reface DX Patch Librarian
================================

A simple patch librarian for the Yamaha Reface DX synthesizer that allows to send and receive
SysEx patches from the computer to the synthesizer and vice versa.

**This is still alpha-stage software and not yet fully functional!**


## Command Line Tools


### `reface-request-patch`

Requests a SysEx patch dump(s) from the Reface DX and saves it as a file.

For example, if bank 3, slot (i.e. program 17, counting from 1) contains a
patch called "Cool Pad", the following command retrives it from a
connected reface DX and saves it:

```console
$ reface-request-patch 17
INFO - Opening MIDI input port #2 (reface DX:reface DX MIDI 1 24:0).
INFO - Opening MIDI output port #2 (reface DX:reface DX MIDI 1 24:0).
INFO - Sending program change #16 on channel 1...
INFO - Sending patch dump request ...
INFO - Writing patch 'Cool Pad' to file 'Cool_Pad.syx'...
```

Use the `-h/--help` option to view further usage information and descriptions
of the command line options.


### `reface-get-soundmondo-voice`

Downloads voice data from [Soundmondo] and saves it as a SysEx file.

Optionally sends it via MIDI to the Reface DX. It can also send any SysEx file
to a chosen MIDI ouput.

For example, to download the Voice "Numana" by *Manny Fernandez* to a file
and send it to the Reface DX:

```console
$ reface-get-soundmondo-voice https://soundmondo.yamahasynth.com/voices/5562 -m
INFO: Writing voice 'Numana' SysEx data to 'Numana.syx'.
INFO: Opening MIDI output port #2 (reface DX:reface DX MIDI 1 24:0).
INFO: Sending voice 'Numana' SysEx data to 'reface DX:reface DX MIDI 1 24:0'.
```

You can also just use the numerical voice ID (e.g. `5562`) instead of the URL,
but using the URL makes it easy to copy-and-paste it from your web browser.

Use the `-h/--help` option to view further usage information and descriptions
of the command line options.

This script can be also be used stand-alone without installing the
`reface-dx-lib` package. Copy the file [get_soundmondo_voice.py] to a
convenient location and install its dependencies, e.g.:

```console
$ pip install appdirs cachecontrol lockfile python-rtmidi requests
$ install -Dm755 refacedx/tools/get_soundmondo_voice.py ~/bin/get-soundmondo-voice
```

[Soundmondo]: https://soundmondo.yamahasynth.com
[get_soundmondo_voice.py]: ./refacedx/tools/get_soundmondo_voice.py