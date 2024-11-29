FROM python:3.12

FROM ubuntu:24.04
LABEL maintainer='kamal.swamidoss@protonmail.com'

ENV USER=fancycrets
RUN groupadd "${USER}" && \
    useradd -m -l -g "${USER}" -c "${USER} account" "${USER}"

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
RUN apt-get update && \
    apt-get --no-install-recommends -y install \
        ca-certificates gcc libssl-dev \
        python3 python3-dev python3-pip python3-venv \
        curl iputils-ping net-tools tcpdump telnet traceroute vim wget && \
    rm -rf /var/lib/apt/lists/*

ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

USER ${USER}
ENV APP_HOME=/home/${USER}
WORKDIR $APP_HOME

COPY requirements.txt ${APP_HOME}/
COPY src/ ${APP_HOME}/src/

RUN python3 -m venv ${APP_HOME}/venv && \
    ${APP_HOME}/venv/bin/pip install -U pip && \
    ${APP_HOME}/venv/bin/pip install -r requirements.txt

ENTRYPOINT ["venv/bin/kopf run src/handlers.py"]
