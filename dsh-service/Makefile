SHELL := /usr/bin/env bash
COMPOSE := docker compose

.PHONY: help build up down restart logs ps token config auth-up auth-down

help:
	@printf '%s\n' \
	  'make up        Build the image and start the service' \
	  'make down      Stop and remove the container (volumes are kept)' \
	  'make restart   Restart the container' \
	  'make logs      Follow dsh logs (the launch URL appears here)' \
	  'make token     Print the current tokenized login URL' \
	  'make ps        Show container and health status' \
	  'make config    Render the effective Compose configuration' \
	  'make auth-up   Start with the optional HTTP Basic auth overlay' \
	  'make auth-down Stop the Basic auth overlay deployment'

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f --no-log-prefix dsh

ps:
	$(COMPOSE) ps

token:
	./scripts/token-url.sh

config:
	$(COMPOSE) config

auth-up:
	$(COMPOSE) -f docker-compose.yml -f compose.auth.yml up -d --build

auth-down:
	$(COMPOSE) -f docker-compose.yml -f compose.auth.yml down
