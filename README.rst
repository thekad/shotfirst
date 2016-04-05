Overview
========

This is just a very simple inotify monitor for "dropbox" style folders. What it
does is you give it a JSON config file and some directories and it will go and
find all the files in the directories and execute ``shutil`` operations on them
(by default ``copy2`` which means the file is copied along with the metadata)
to the configured location.

For example, with the following configuration file::

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

``shotfirst`` will:

#.  Copy all GIF, JPEG, and PNG images found in the given folders to a
    directory ``/tmp/foo/pics`` and will use the EXIF metadata from the image
    to figure out the sub-folder structure (which is year/month/day)
#.  Move all the WebM videos in the given folders to a directory named
    ``/tmp/foo/videos`` based on the video metadata, if available. Otherwise
    will fall back to the file system meta data.
#.  Copy all PDF files in the given folders to a directory ``/tmp/foo/docs``
    based on the PDF metadata if available. Fall back to the file system meta
    data if not.

