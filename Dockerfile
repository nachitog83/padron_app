FROM python:3.8.2-slim-buster

# Adds metadata to the image as a key value pair example LABEL version="1.0"
LABEL maintainer="Ignacio Grosso"

# Set environment variables
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

# Set up WorkDirs
RUN mkdir /app
WORKDIR /app

# Copy requirements.txt
COPY ./app/requirements.txt /app

# Install Debian packages
RUN apt-get -qq update && apt-get -qq -y install apt-utils \
    autoconf \
    automake \
    make \
    libtool \
    python-dev \
    curl \
    cron \
    git \
    ca-certificates \
    pkg-config \
    python3-pip \
    locales

RUN sed -i -e 's/# es_AR.UTF-8 UTF-8/es_AR.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=es_AR.UTF-8

RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

CMD ["python", "./main.py"]
