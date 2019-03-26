FROM ubuntu:latest
MAINTAINER Egor Sergeev
RUN apt-get update
RUN apt-get install -y python3-pip
RUN pip3 install aiohttp
COPY server.py /
CMD python3 server.py
EXPOSE 8080
