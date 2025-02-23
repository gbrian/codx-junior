
(cd ../../ && docker build -t codx-junior:dind -f Dockerfile.dind .)
docker rm -f codx-junior-dind || true
docker run -d --privileged --name codx-junior-dind codx-junior:dind
docker exec -it codx-junior-dind bash