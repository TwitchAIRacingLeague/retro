cd ..
REM docker/linux/build_scripts/prefetch.sh OPENSSL CURL
docker build . --tag twitchairacingleague/retro-build:win64-v2 --file docker/Dockerfile --progress plain
REM Next once it's done (and we're happy) it will run this docker container, and copy the contents of the dist folder
REM Into an equivalent one here, so we have the files locally.
docker run -i -t twitchairacingleague/retro-build:win64-v2 /bin/bash

REM docker cp 915ff70ebc56:/root/stable-retro/dist/gym_retro-0.9.0-cp310-cp310-win_amd64.whl .
REM pip install retro/dist/gym_retro-0.9.0-cp310-cp310-win_amd64.whl