FROM python:3.6.2

# Metadata
LABEL container.base.image="python:3.6.2"
LABEL software.name="audio_books_crawler"
LABEL software.version="1.0.0"
LABEL software.description="A lazy way to crunch the latest Chinese news"
LABEL software.website="https://github.com/haoeric/free-audio-books"
LABEL software.documentation="https://github.com/haoeric/free-audio-books"
LABEL software.license="GPLv3 or later"
LABEL maintainer="Hao Chen <haoeric@hotmail.com>"
LABEL tags="audio_books_crawler"

# Set the destination directory for softwares installation
ENV DST=/tmp

# Do a few updates of the base system and install R (via the r-base package)
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y zlib1g-dev gnuplot && \
    apt-get install -y unzip gcc libncurses5-dev && \
    apt-get install -y git && \
    apt-get install -y software-properties-common && \
    apt-get clean

RUN apt-get -y update && apt-get install -y wget nano git build-essential yasm pkg-config

# # install ffmpeg
#  RUN add-apt-repository ppa:mc3man/trusty-media && \
#      apt-get update && \
#      apt-get install -y ffmpeg

# Compile and install ffmpeg from source
RUN git clone https://github.com/FFmpeg/FFmpeg /root/ffmpeg && \
    cd /root/ffmpeg && \
    ./configure --enable-nonfree --disable-shared --extra-cflags=-I/usr/local/include && \
    make -j8 && make install -j8
    
# install python modulars
RUN pip install boto3 awscli requests beautifulsoup4 youtube_dl

# copy scripts from host to image
COPY src /audio_books_crawler

## install lame
RUN cd /audio_books_crawler/lame-3.100/ && \
    make -f Makefile.unix

# export env path
ENV PATH /usr/local/bin:$PATH
ENV PATH /audio_books_crawler/lame-3.100/frontend:$PATH

RUN chmod 555 /audio_books_crawler/*

# create ENTRYPOINT
ENTRYPOINT ["python", "/audio_books_crawler/youtube_audio_crawler.py"]





