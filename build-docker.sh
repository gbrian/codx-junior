echo "Build codx-junior:latest"
CWD=$PWD
cd codx-junior-installer/codx-junior

docker-compose build codx-junior-debian-image 
docker-compose build codx-junior-api-image codx-junior-image

cd $CWD