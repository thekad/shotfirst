#!/usr/bin/env python
# -*- mode:python; sh-basic-offset:4; indent-tabs-mode:nil; coding:utf-8 -*-
# vim:set tabstop=4 softtabstop=4 expandtab shiftwidth=4 fileencoding=utf-8:
#

import shotfirst

import hashlib
import importlib
import json
import logging
import mimetypes
import multiprocessing
import os
import pyinotify
from Queue import Queue
import shutil
import sys
from threading import Thread
from traceback import format_exc


# Default number of importers
DEFAULT_THREADS = multiprocessing.cpu_count()


class ImportHandler(pyinotify.ProcessEvent):

    config = {}

    def _make_conf(self, vals):
        values = vals.copy()
        if 'mask' not in values:
            values['mask'] = ''
        if 'operation' not in values:
            values['operation'] = 'copy2'
        if 'handler' in values:
            m = values['handler']
        else:
            m = 'shotfirst.handlers.simple_file_handler'
        try:
            mod = importlib.import_module('.'.join(m.split('.')[:-1]))
            method = getattr(mod, m.split('.')[-1])
        except:
            raise NotImplementedError(
                'Handler %s is not implemented' % (m,)
            )
        values['handler'] = method

        return values

    def my_init(self, config, threads=DEFAULT_THREADS):

        cfg = {}
        for keys, values in config.items():
            assert 'target' in values, 'Each item in the config must '\
                'have a target declared'
            for key in keys.split(','):
                logging.debug('Loading %s' % key.strip())
                k = key.strip()
                cfg[k] = self._make_conf(values)
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
        return f_type, self.config[f_type]

    def import_file(self, orig_file):
        fname = os.path.basename(orig_file)
        mime_type, config = self._get_config(orig_file)
        dtime = config['handler'](orig_file, config=config)
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
                msg = 'File %s was already processed. ' % (
                    orig_file,
                )
                if config['operation'] == 'copy':
                    msg += 'Leaving alone because operation is "copy" '
                elif config['operation'] == 'move':
                    msg += 'Removing source file to '\
                        'avoid this because operation is "move" '
                    os.unlink(orig_file)
                else:
                    pass
                msg += 'for mime type %s' % (mime_type,)
                logging.warn(msg)
            else:
                logging.warn('A file with the same name (%s) exists, but '
                             'it seems different.' % (dest_file,))
            return

        if not os.path.isdir(fsubdir):
            try:
                os.makedirs(fsubdir)
            except Exception as e:
                logging.debug(e)
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
    jsonf = {}
    with open(config, 'rb') as fh:
        jsonf = json.loads(fh.read())
    return jsonf


def main():
    if os.environ.get('SDEBUG', False):
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level, datefmt='%Y-%m-%d %H:%M:%S',
        format='%(asctime)s - %(threadName)s '
        '- %(levelname)s - %(message)s'
    )

    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=shotfirst.__doc__)
    parser.add_argument(
        '-v', '--version', action='version', version=shotfirst.__version__
    )
    parser.add_argument(
        '-t', '--threads', default=DEFAULT_THREADS,
        help='Default number of worker threads to create'
    )
    parser.add_argument(
        '--no-auto-add', action='store_true', default=False,
        help='Do not automatically watch sub-directories'
    )
    parser.add_argument(
        '--no-recurse', action='store_true', default=False,
        help='Do not recurse'
    )
    parser.add_argument(
        'config', nargs=1,
        help='JSON configuration file'
    )
    parser.add_argument(
        'paths', metavar='path', nargs='+',
        help='Director(y|ies) to watch'
    )
    args = parser.parse_args()

    logging.info('Starting up')

    handler = ImportHandler(
        threads=args.threads, config=load_config(args.config.pop())
    )

    wm = pyinotify.WatchManager()
    notifier = pyinotify.Notifier(wm, handler)

    mask = get_mask()
    for path in args.paths:
        ret = wm.add_watch(path, mask, rec=not args.no_recurse,
                           auto_add=not args.no_auto_add)
        if ret[path] == -1:
            logging.critical(
                'add_watch failed for %s, bailing out!' % (path,)
            )
            return 1

    import_files(handler, args.paths, not args.no_recurse)

    notifier.loop()

if __name__ == '__main__':
    sys.exit(main())
