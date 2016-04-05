Overview
========

This is just a very simple inotify monitor for "dropbox" style folders. What it
does is you give it a JSON config file and some directories and it will go and
find all the files in the directories and execute ``shutil`` operations on them
(by default ``copy2`` which means the file is copied along with the metadata)
to the configured location.

An example of the configuration file:

```json
    {
      "image/jpeg, image/gif, image/png": {
        "mask": "%Y/%m/%d",
        "target": "/tmp/foo/pics",
        "handler": "shotfirst.handlers.exif_image_handler"
      },
      "video/webm": {
        "target": "/tmp/foo/videos",
        "mask": "%Y/%m/%d",
        "handler": "shotfirst.handlers.video_handler"
      },
      "application/pdf": {
        "target": "/tmp/foo/docs",
        "handler": "shotfirst.handlers.pdf_handler",
        "mask": "%Y/%m"
      }
    }
```

