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
    from pyPdf import PdfFileReader
    r = PdfFileReader(open(fullpath, 'rb'))
    try:
        dtime = r.documentInfo['/CreationDate'][:14]
        dtime = datetime.strptime(dtime, 'D:%Y%m%d%H%M')
    except:
        logging.error(
            'Could not fetch PDF metadata for %s, falling back '
            'to simple file handler' % (
                fullpath
            )
        )
        return simple_file_handler(fullpath, **kwargs)
    return dtime


def exif_image_handler(fullpath, **kwargs):
    logging.debug('Handling %s as an EXIF image' % (fullpath, ))

    from PIL import Image
    image = Image.open(fullpath)
    exif = image._getexif()
    dtime = exif.get(0x9003)

    if dtime is None:
        logging.error(
            'Could not fetch timestamp for %s, skipping' % (
                fullpath
            )
        )
        return False
    logging.info(dtime)
    dtime = datetime.strptime(dtime, '%Y:%m:%d %H:%M:%S')
    return dtime
