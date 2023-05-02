FROM ubuntu:22.04
FROM ubuntu:bionic



#ARG DEBIAN_FRONTEND=noninteractive 


#RUN apt-get update -y && apt-get install -y \
#    git \
#    cmake \
#    capnproto \
#    zlib1g-dev \
#    g++ \
#    build-essential \
#    python3-dev \
#    python3-pip \
#    pkg-config \
#    libzip-dev \
#    g++-mingw-w64-x86-64 \
#    libz-mingw-w64-dev \
#    software-properties-common

#RUN git clone https://github.com/zbeucler2018/stable-retro stable-retro




SHELL ["/bin/bash", "-c"]
ARG ARCH=x86_64
ARG BITS=64
ENV PYVER=3.10
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential ccache cmake curl g++-mingw-w64-`echo $ARCH | tr _ -` \
        git libffi-dev libpng-dev libz-mingw-w64-dev p7zip-full pkg-config nano \
        software-properties-common unzip zip dos2unix capnproto python3-dev python3-pip && \
    apt-get clean


RUN apt-add-repository -y ppa:deadsnakes/ppa && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libpython${PYVER}-dev python${PYVER}-venv && \
    apt-get clean

#python3.10 -m venv ~/venv3.10 && . ~/venv3.10/bin/activate && pip install wheel

RUN python${PYVER} -m venv ~/venv${PYVER} && \
    . ~/venv${PYVER}/bin/activate && \
    pip install wheel && \
    pip install pytest requests && \
    rm -rf ~/.cache && \
    ln -s ~/venv${PYVER} ~/venv && \
    echo "source /root/venv\$PYVER/bin/activate" > ~/.bash_profile

WORKDIR /root

#RUN curl https://repo.anaconda.com/archive/Anaconda3-2023.03-1-Linux-x86_64.sh --output Anaconda3-2023.03-1-Linux-x86_64.sh

#RUN chmod +x Anaconda3-2023.03-1-Linux-x86_64.sh
#RUN ./Anaconda3-2023.03-1-Linux-x86_64.sh -b -u
#RUN source ~/anaconda3/bin/activate && conda init bash

COPY docker/scripts scripts
COPY docker/cmake cmake

RUN dos2unix scripts/install_python.sh
RUN dos2unix scripts/build_libzip.sh
RUN dos2unix scripts/build_qt5.sh
RUN dos2unix scripts/build_ccache.sh
RUN dos2unix scripts/build_capnproto.sh

RUN CROSS=win${BITS} ROOT=/usr/${ARCH}-w64-mingw32 ./scripts/install_python.sh

COPY third-party/libzip libzip

RUN CROSS=win${BITS} ROOT=/usr/${ARCH}-w64-mingw32 ./scripts/build_libzip.sh && \
    rm -rf libzip

COPY third-party/capnproto capnproto
RUN ROOT=/usr ./scripts/build_capnproto.sh && \
    CROSS=win${BITS} ROOT=/usr/${ARCH}-w64-mingw32 ./scripts/build_capnproto.sh && \
    rm -rf capnproto

RUN CROSS=win${BITS} ROOT=/usr/${ARCH}-w64-mingw32 ./scripts/build_qt5.sh && \
    rm -rf qt5

RUN ./scripts/build_ccache.sh && (cd /usr/local/libexec/ccache && \
    ln -s /usr/local/bin/ccache ${ARCH}-w64-mingw32-gcc && \
    ln -s /usr/local/bin/ccache ${ARCH}-w64-mingw32-g++)
ENV PATH /usr/local/libexec/ccache:$PATH

#RUN git clone https://github.com/TwitchAIRacingLeague/retro stable-retro
RUN git clone https://github.com/zbeucler2018/stable-retro stable-retro

#RUN python3 -m pip install --upgrade pip wheel setuptools

####RUN python3 -m pip install -e .

#RUN cmake . -DBUILD_TESTS=ON -DBUILD_MANYLINUX=ON -DPYTHON_INCLUDE_DIR=/usr/include/python${PYVER} -DBUILD_UI=ON -DCMAKE_TOOLCHAIN_FILE=../cmake/win64.cmake
#RUN cmake . -DBUILD_TESTS=ON -DBUILD_MANYLINUX=ON -DPYTHON_INCLUDE_DIR=/usr/include/python3.10 -DBUILD_UI=ON -DCMAKE_TOOLCHAIN_FILE=../cmake/win64.cmake

#RUN python3 setup.py -q build_ext -i -j3

#RUN make -j3

#RUN python3 setup.py -q bdist_wheel --plat-name win_amd64

