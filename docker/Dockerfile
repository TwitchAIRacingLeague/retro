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
    g++-mingw-w64-x86-64 \
    libz-mingw-w64-dev \
    software-properties-common

#RUN git clone https://github.com/zbeucler2018/stable-retro stable-retro
RUN git clone https://github.com/TwitchAIRacingLeague/retro stable-retro


WORKDIR /stable-retro

COPY docker/scripts scripts

ARG ARCH=x86_64
ARG BITS=64
ENV PYVER=3.10

COPY docker/cmake cmake

RUN apt-get install -y ccache
#RUN CROSS=win${BITS} ROOT=/usr/${ARCH}-w64-mingw32 ./scripts/install_python.sh

#COPY third-party/libzip libzip
#RUN CROSS=win${BITS} ROOT=/usr/${ARCH}-w64-mingw32 ./scripts/build_libzip.sh && \
#    rm -rf libzip

#COPY third-party/capnproto capnproto
#RUN ROOT=/usr ./scripts/build_capnproto.sh && \
#    CROSS=win${BITS} ROOT=/usr/${ARCH}-w64-mingw32 ./scripts/build_capnproto.sh && \
#    rm -rf capnproto

#RUN CROSS=win${BITS} ROOT=/usr/${ARCH}-w64-mingw32 ./scripts/build_qt5.sh && \
#    rm -rf qt5

#RUN ./scripts/build_ccache.sh && (cd /usr/local/libexec/ccache && \
#    ln -s /usr/local/bin/ccache ${ARCH}-w64-mingw32-gcc && \
#    ln -s /usr/local/bin/ccache ${ARCH}-w64-mingw32-g++)
#ENV PATH /usr/local/libexec/ccache:$PATH

RUN python3 -m pip install --upgrade pip wheel setuptools

#RUN python3 -m pip install -e .

RUN cmake . -DBUILD_TESTS=ON -DBUILD_MANYLINUX=ON -DPYTHON_INCLUDE_DIR=/usr/include/python3.10 -DBUILD_UI=ON -DCMAKE_TOOLCHAIN_FILE=cmake/win64.cmake

RUN python3 setup.py -q build_ext -i -j3

RUN make -j3

RUN python3 setup.py -q bdist_wheel --plat-name win_amd64

