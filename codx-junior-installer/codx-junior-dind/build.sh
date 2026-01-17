# Build codx-junior:dind
echo "Build codx-junior-dind"

# if [ ! -d "images" ];then
#     mkdir images
#     docker save -o images/codx-junior-debian.tar codx-junior:debian
#     docker save -o images/codx-junior-api.tar codx-junior:api
#     docker save -o images/codx-junior-latest.tar codx-junior:latest
# fi
cd ../.. && docker build -t codx-junior:dind -f codx-junior-installer/codx-junior-dind/Dockerfile .
