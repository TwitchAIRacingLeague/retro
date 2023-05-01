FROM ubuntu:22.04

 

ARG DEBIAN_FRONTEND=noninteractive 

RUN apt-get update -y && apt-get install -y \
    git \
    cmake \
    capnproto \
    zlib1g-dev \
    g++ \
    build-essential \
    python3-dev \
    python3-pip \
    pkg-config \
    libzip-dev \
    software-properties-common

#RUN git clone https://github.com/zbeucler2018/stable-retro stable-retro
RUN git clone https://github.com/TwitchAIRacingLeague/retro stable-retro


WORKDIR /stable-retro

COPY cmake cmake

RUN python3 -m pip install --upgrade pip wheel setuptools

#RUN python3 -m pip install -e .

RUN cmake . -DBUILD_TESTS=ON -DBUILD_MANYLINUX=ON -DPYTHON_INCLUDE_DIR=/usr/include/python3.10 -DBUILD_UI=ON -DCMAKE_TOOLCHAIN_FILE=cmake/win64.cmake

RUN python3 setup.py -q build_ext -i -j3

RUN make -j3

RUN python3 setup.py bdist_wheel --plat-name win_amd64