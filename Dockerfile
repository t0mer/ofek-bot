FROM selenium/standalone-chrome:143.0-chromedriver-143.0-grid-4.39.0-20251212
LABEL maintainer="tomer.klein@gmail.com"

# Switch to root user to install packages
USER root

ENV PYTHONIOENCODING utf-8
ENV LANG C.UTF-8
ENV NOTIFIERS ""
ENV SCHEDULES ""
RUN apt update -yqq

RUN apt -yqq install python3-pip && \
    apt -yqq install libffi-dev && \
    apt -yqq install libssl-dev

COPY requirenebts.txt /tmp

RUN pip3 install -r /tmp/requirenebts.txt
     
RUN mkdir -p /app/config

COPY app /app

WORKDIR /app
 
ENTRYPOINT python /app/app.py