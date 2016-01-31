#!/usr/bin/env python
# -*- mode:python; sh-basic-offset:4; indent-tabs-mode:nil; coding:utf-8 -*-
# vim:set tabstop=4 softtabstop=4 expandtab shiftwidth=4 fileencoding=utf-8:
#

from datetime import datetime
import logging
import os


def simple_file_handler(fullpath, **kwargs):
    logging.debug('Handling %s as a simple file' % (fullpath, ))
    try:
        mtime = os.path.getmtime(fullpath)
        dtime = datetime.fromtimestamp(mtime)
    except:
        logging.error('Could not fetch timestamp for %s, skipping' % (
                      fullpath))
        return False
    return dtime


def pdf_file_handler(fullpath, **kwargs):
    logging.debug('Handling %s as a PDF file' % (fullpath, ))

    from pdfrw import PdfReader
    r = PdfReader(fullpath)
    try:
        # Why do PDFs have such a weird timestamp format?
        # example from a random PDF: (D:20131222010843-06'00')
        # grabbing only what we need up to seconds, no TZ
        dtime = r.Info.CreationDate[3:17]
        dtime = datetime.strptime(dtime, '%Y%m%d%H%M%S')
    except Exception as e:
        logging.debug(e)
        logging.error(
            'Could not read PDF metadata from %s, falling back '
            'to simple_file_handler' % (
                fullpath
            )
        )
        return simple_file_handler(fullpath, **kwargs)
    return dtime


def exif_image_handler(fullpath, **kwargs):
    logging.debug('Handling %s as an EXIF image' % (fullpath, ))

    from PIL import Image

    dtime = None
    try:
        image = Image.open(fullpath)
        exif = image._getexif()
        dtime = exif.get(0x9003)
    except Exception as e:
        logging.debug(e)

    if dtime is None:
        logging.error(
            'Could not read EXIF metadata from %s, falling back '
            'to simple_file_handler' % (
                fullpath
            )
        )
        return simple_file_handler(fullpath, **kwargs)
    dtime = datetime.strptime(dtime, '%Y:%m:%d %H:%M:%S')
    return dtime


def video_handler(fullpath, **kwargs):
    logging.debug('Handling %s as a video file' % (fullpath, ))

    from enzyme import MKV

    try:
        with open(fullpath, 'rb') as fh:
            mkv = MKV(fh)
    except Exception as e:
        logging.debug(e)
        logging.error(
            'Could not read Video metadata from %s, falling back '
            'to simple_file_handler' % (
                fullpath
            )
        )
        return simple_file_handler(fullpath, **kwargs)

    return mkv.info.date_utc
