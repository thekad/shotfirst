#!/usr/bin/env python
# -*- mode:python; sh-basic-offset:4; indent-tabs-mode:nil; coding:utf-8 -*-
# vim:set tabstop=4 softtabstop=4 expandtab shiftwidth=4 fileencoding=utf-8:
#
"""
Monitors a "drop box" location for new files to copy or move them
"""

import argparse
from datetime import datetime
import hashlib
import json
import logging
import mimetypes
import multiprocessing
import os
from PIL import Image
import pyinotify
from Queue import Queue
import shutil
import sys
from threading import Thread
from traceback import format_exc

__version__ = '0.1'

# Default number of importers
DEFAULT_THREADS = multiprocessing.cpu_count()

if os.environ.get('SDEBUG', False):
    level = logging.DEBUG
else:
    level = logging.INFO

logging.basicConfig(level=level, datefmt='%Y-%m-%d %H:%M:%S',
                    format='%(asctime)s - %(levelname)s - %(message)s')


class ImportHandler(pyinotify.ProcessEvent):

    config = {}

    def _make_conf(self, vals):
        values = vals.copy()
        if 'mask' not in values:
            values['mask'] = ''
        if 'operation' not in values:
            values['operation'] = 'move'
        if 'handler' in values:
            if values['handler'] in dir(self):
                values['handler'] = getattr(self, values['handler'])
            else:
                raise NotImplementedError('Handler %(handler)s '
                                          'is not implemented' % values)
        else:
            values['handler'] = self.handle_simple_file

        return values

    def my_init(self, config, threads=DEFAULT_THREADS):

        cfg = config.copy()
        for keys, values in cfg.items():
            assert 'target' in values, 'Each item in the config must '\
                'have a target declared'
            if len(keys.split(',')) > 1:
                for key in keys.split(','):
                    logging.debug('Loading %s' % key.strip())
                    k = key.strip()
                    cfg[k] = self._make_conf(values)
                cfg.pop(keys)
            else:
                logging.debug('Loading %s' % keys.strip())
                cfg[keys] = self._make_conf(values)
        self.config = cfg
        logging.debug(self.config)
        self.fileq = Queue()

        for i in range(int(threads)):
            t = Thread(target=self.worker)
            t.daemon = True
            t.start()

    def worker(self):
        while True:
            f = self.fileq.get()
            try:
                self.import_file(f)
            except:
                logging.error('Failed importing %s.\n%s' %
                              (f, format_exc()))

            self.fileq.task_done()

    def process_IN_CLOSE_WRITE(self, event):
        self.add_file(event.pathname)

    def process_IN_MOVED_TO(self, event):
        self.add_file(event.pathname)

    def handle_simple_file(self, fullpath, config):
        try:
            ctime = os.path.getmtime(fullpath)
            dtime = datetime.fromtimestamp(ctime)
        except:
            logging.error('Could not fetch timestamp for %s, skipping' % (
                          fullpath))
            return False
        return dtime

    def handle_pdf(self, fullpath, config):
        from pyPdf import PdfFileReader
        r = PdfFileReader(open(fullpath, 'rb'))
        try:
            dtime = r.documentInfo['/CreationDate'][:14]
            dtime = datetime.strptime(dtime, 'D:%Y%m%d%H%M')
        except:
            logging.error('Could not fetch timestamp for %s, skipping' % (
                          fullpath))
            return False
        return dtime

    def handle_exif_image(self, fullpath, config):
        image = Image.open(fullpath)
        exif = image._getexif()
        dtime = None
        try:
            dtime = exif[0x9003]
            dtime = datetime.strptime(dtime, '%Y:%m:%d %H:%M:%S')
        except:
            logging.error('Could not fetch timestamp for %s, skipping' % (
                          fullpath))
            return False
        return dtime

    def add_file(self, fullpath):
        logging.debug('Analyzing %s for inclusion...' % (fullpath,))
        try:
            (f_type, f_encoding) = mimetypes.guess_type(fullpath)
            logging.debug('%s is %s' % (fullpath, f_type,))
            if f_type in self.config:
                self.fileq.put(fullpath)
            else:
                raise ValueError(
                    'Invalid or not-configured mime-type %s' % (
                        f_type,
                    )
                )
        except Exception as e:
            logging.warn('Error adding %s! %s' % (fullpath, e))
            return

    def _get_config(self, orig_file):
        (f_type, f_encoding) = mimetypes.guess_type(orig_file)
        cfg = self.config[f_type]
        logging.debug(cfg)
        return self.config[f_type]

    def import_file(self, orig_file):
        fname = os.path.basename(orig_file).lower()
        config = self._get_config(orig_file)
        dtime = config['handler'](orig_file, config)
        if not dtime:
            return False
        logging.debug('Timestamp for %s is %s' % (
                      os.path.basename(orig_file), dtime,))
        fsubdir = os.path.join(config['target'],
                               dtime.strftime(config['mask']))
        dest_file = os.path.join(fsubdir, fname)
        if os.path.exists(dest_file):
            logging.debug('Destination file %s already exists, comparing' % (
                          dest_file,))
            dest_md5 = hashlib.md5(open(dest_file).read()).hexdigest()
            orig_md5 = hashlib.md5(open(orig_file).read()).hexdigest()
            logging.debug('%s == %s ? %s' % (dest_md5, orig_md5,
                          dest_md5 == orig_md5))
            if dest_md5 == orig_md5:
                logging.warn(
                    'File %s already exists, unlinking to avoid this' % (
                        os.path.basename(dest_file)
                    )
                )
                os.unlink(orig_file)
            else:
                logging.warn('A file with the same name (%s) exists, but '
                             'it seems different.' % (dest_file,))
            return

        if not os.path.isdir(fsubdir):
            os.makedirs(fsubdir)
        operation = getattr(shutil, config['operation'])
        operation(orig_file, dest_file)
        logging.info('Imported %s -> %s (via %s)' %
                     (orig_file, dest_file, operation.__name__))


def import_file(handler, filename, filedir, log):
    if not filedir.endswith('/'):
        filedir += '/'

    fullpath = os.path.realpath('%s%s' % (filedir, filename))

    if os.path.isdir(fullpath):
        return

    handler.add_file(fullpath)


def get_mask(listen_events=['IN_MOVED_TO', 'IN_CLOSE_WRITE']):
    mask = 0
    while listen_events:
        mask = mask | getattr(pyinotify, listen_events.pop())

    return mask


def import_files(handler, paths, recurse, log=logging):
    for path in paths:
        logging.info('Import from %s' % path)
        if recurse:
            for root, dirs, files in os.walk(path):
                for filename in files:
                    import_file(handler, filename, root, log)
        else:
            for filename in os.listdir(path):
                import_file(handler, filename, path, log)
    return 0


def load_config(config):
    jsonf = json.loads(open(config, 'rb').read())
    return jsonf


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Monitor a given number of dropboxes for files')
    parser.add_argument('-t', '--threads', default=DEFAULT_THREADS,
                        help='Default number of worker threads to create')
    parser.add_argument('--no-auto-add', action='store_true', default=False,
                        help='Do not automatically watch sub-directories')
    parser.add_argument('--no-recurse', action='store_true', default=False,
                        help='Do not recurse')
    parser.add_argument('-c', '--config', required=True,
                        help='JSON configuration file')
    parser.add_argument('paths', metavar='path', nargs='+',
                        help='Director(y|ies) to watch')
    args = parser.parse_args()

    logging.info('Starting up')

    handler = ImportHandler(threads=args.threads,
                            config=load_config(args.config))

    wm = pyinotify.WatchManager()
    notifier = pyinotify.Notifier(wm, handler)

    mask = get_mask()
    for path in args.paths:
        ret = wm.add_watch(path, mask, rec=not args.no_recurse,
                           auto_add=not args.no_auto_add)
        if ret[path] == -1:
            logging.critical('add_watch failed for %s, bailing out!' %
                             (path))
            return 1

    import_files(handler, args.paths, not args.no_recurse)

    notifier.loop()

if __name__ == '__main__':
    sys.exit(main())
