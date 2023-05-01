cd ..
docker build . --tag twitchairacingleague/retro-build:win64-v2 --file docker/Dockerfile
# Next once it's done (and we're happy) it will run this docker container, and copy the contents of the dist folder
# Into an equivalent one here, so we have the files locally.