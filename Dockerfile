FROM techblog/selenium:latest
LABEL maintainer="tomer.klein@gmail.com"

ENV PYTHONIOENCODING utf-8
ENV LANG C.UTF-8
ENV NOTIFIERS ""
ENV SCHEDULES ""
RUN apt update -yqq

RUN apt -yqq install python3-pip && \
    apt -yqq install libffi-dev && \
    apt -yqq install libssl-dev

RUN  pip3 install --upgrade pip --no-cache-dir && \
     pip3 install --upgrade setuptools --no-cache-dir && \
     pip3 install schedule --no-cache-dir && \
     pip3 install loguru --no-cache-dir && \
     pip3 install apprise --no-cache-dir
     
RUN mkdir -p /app/config

COPY app /app

WORKDIR /app
 
ENTRYPOINT ["/usr/bin/python3", "/app/app.py"]