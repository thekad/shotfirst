FROM alpine:3

ENV SDEBUG=

WORKDIR /app

ADD README.rst /app/
ADD requirements.txt /app/
ADD setup.py /app/
ADD shotfirst /app/shotfirst
ADD shotfirst.json /app/config/

VOLUME /app/config
VOLUME /app/inbox

RUN apk --no-cache --no-progress add dumb-init \
        python3 \
        build-base \
        python3-dev \
        py3-setuptools \
        py3-pip \
        jpeg \
        jpeg-dev \
        zlib \
        zlib-dev \
        freetype \
        freetype-dev \
        openjpeg \
        openjpeg-dev \
        tiff \
        tiff-dev && \
    pip install -r requirements.txt && \
    apk del build-base \
        python3-dev \
        py3-pip \
        jpeg-dev \
        zlib-dev \
        freetype-dev \
        openjpeg-dev \
        tiff-dev

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["shotfirst", "/app/config/shotfirst.json", "/app/inbox"]
