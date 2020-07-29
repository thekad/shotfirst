Overview
========

This is just a very simple inotify monitor for "dropbox" style folders. What it
does is you give it a JSON config file and some directories and it will go and
find all the files in the directories and execute ``shutil`` operations on them
(by default ``copy2`` which means the file is copied along with the metadata)
to the configured location.


Installing
==========

Option 1: Clone this repo and ``pip install -r requirements.txt`` (bleeding edge)
Option 2: Run ``pip install shotfirst`` (released)


Configuration
=============

With the following configuration file ``shotfirst.json``::

    {
      "image/jpeg, image/gif, image/png": {
        "mask": "%Y/%m/%d",
        "target": "/tmp/foo/pics",
        "handler": "shotfirst.handlers.exif_image_handler"
      },
      "video/webm": {
        "target": "/tmp/foo/videos",
        "operation": "move",
        "mask": "%Y/%m/%d",
        "handler": "shotfirst.handlers.video_handler"
      },
      "application/pdf": {
        "target": "/tmp/foo/docs",
        "handler": "shotfirst.handlers.pdf_handler",
        "mask": "%Y/%m"
      }
    }

``shotfirst shotfirst.json /tmp/inbox`` will:

#.  Monitor the ``/tmp/inbox`` folder for files
#.  Copy all GIF, JPEG, and PNG images found to a directory ``/tmp/foo/pics``
    and use the EXIF metadata from the image to figure out the sub-folder
    structure (which is year/month/day)
#.  Move all the WebM videos to a directory named ``/tmp/foo/videos`` based on
    the video metadata, if available. Otherwise will fall back to the file
    system meta data.
#.  Copy all PDF files to a directory ``/tmp/foo/docs`` based on the PDF
    metadata if available. Fall back to the file system meta data if not.

Running in docker
=================

There's a published docker image, to run you will have to mount your
configuration file and your input and output folders, for example::

    docker run --rm -it -v `pwd`/myconfig:/etc/shotfirst.json -v `pwd`/input:/app/inbox:rw -v `pwd`/output:/app/outbox:rw thekad/shotfirst:latest

And adjust your configuration appropriately to output the files to
subdirectories inside ``/app/outbox``.

.. NOTE::
   The input folder is statically set to ``/app/inbox``, but the output
   folder(s) can be configured at will

