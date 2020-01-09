#!/usr/bin/env python
"""Generate qrc and rcc file from icon theme."""

import argparse
import configparser
import os
import subprocess
import xml.etree.ElementTree as etree

from os.path import abspath, basename, dirname, exists, join, splitext


def create_qrc(themefilepath, exts=['.svg']):
    """Generate .qrc file from all images in directory of theme path.
    """
    themepath = dirname(themefilepath)

    # Parse index.theme
    parser = configparser.ConfigParser()
    parser.read(themefilepath)

    try:
        name = parser.get('Icon Theme', 'Name')
        directories = parser.get('Icon Theme', 'Directories').split(',')
    except configparser.NoSectionError:
        raise ValueError("Invalid .theme file. Missing 'Icon Theme' section.")

    # Create root
    root = etree.Element('RCC', version='1.0')
    element_qresource = etree.SubElement(root, 'qresource',
                                         prefix='icons/%s' % name)

    element = etree.SubElement(element_qresource, 'file', alias='index.theme')
    element.text = themefilepath

    # Find all image files
    cwd = os.getcwd()
    os.chdir(themepath)

    for dirpath, _, filenames in os.walk('scalable'):
        for filename in filenames:
            if splitext(filename)[1] not in exts:
                continue

            iconpath = join(themepath, dirpath, filename)

            for size in (16, 24, 32, 48):
                alias = join('%dx%d' % (size, size), filename)
                element = etree.SubElement(element_qresource, 'file', alias=alias)
                element.text = iconpath

    os.chdir(cwd)

    # Write qrc file
    outfilepath = name + '.qrc'
    with open(outfilepath, 'w') as fp:
        fp.write('<!DOCTYPE RCC>')
        etree.ElementTree(root).write(fp, encoding='unicode', xml_declaration=False)

    return outfilepath


def run_rcc(qrcfilepath, outfilepath=None, rcc='rcc'):
    if basename(rcc).startswith('pyrcc'):
        outfilepath = outfilepath or splitext(qrcfilepath)[0] + '_rcc.py'
        subprocess.check_call([rcc, '-o', outfilepath,
                               '-compress', '9', qrcfilepath])
    else:
        outfilepath = outfilepath or splitext(qrcfilepath)[0] + '.rcc'
        subprocess.check_call([rcc, '--binary', '-o', outfilepath,
                               '--compress', '9', qrcfilepath])


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-o',
        '--output-file',
        metavar='PATH',
        help="Path of RCC output file (default: theme name + '.rcc')")
    parser.add_argument(
        '--rcc',
        metavar='NAME',
        default='rcc',
        help="Name or path of 'rcc' binary (default: %(default)s)")
    parser.add_argument(
        'theme',
        metavar='FILE',
        help="Path to .theme file")

    args = parser.parse_args(args)

    if not exists(args.theme):
        return "File not found: %s" % args.theme

    try:
        qrcfilepath = create_qrc(args.theme)
        run_rcc(qrcfilepath, outfilepath=args.output_file, rcc=args.rcc)
    except Exception as exc:
        return str(exc)


if __name__ == '__main__':
    import sys
    sys.exit(main() or 0)
