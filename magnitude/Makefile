# =============================================================================
# Magnitude docker test harness - convenience targets
# =============================================================================
COMPOSE ?= docker compose
SERVICE := magnitude

.DEFAULT_GOAL := help

.PHONY: help build up down restart logs status test shell model-list clean prune

help: ## Show this help
	@echo "Magnitude docker harness"
	@echo ""
	@echo "  make build      Build the image (debian:12 + Magnitude .deb)"
	@echo "  make up         Start the Magnitude server in the background"
	@echo "  make down       Stop and remove the containers"
	@echo "  make restart    Restart the Magnitude server"
	@echo "  make logs       Follow the server logs"
	@echo "  make status     Show container status"
	@echo "  make test       Run the one-shot model download + inference test"
	@echo "  make model-list List downloaded models"
	@echo "  make shell      Open a shell inside a fresh container"
	@echo "  make clean      Stop everything and delete the models volume"
	@echo "  make prune      Remove the built images"

build: ## Build the image
	$(COMPOSE) build

up: ## Start the server
	$(COMPOSE) up -d $(SERVICE)

down: ## Stop the containers
	$(COMPOSE) down

restart: ## Restart the server
	$(COMPOSE) restart $(SERVICE)

logs: ## Follow server logs
	$(COMPOSE) logs -f $(SERVICE)

status: ## Container status
	$(COMPOSE) ps

test: ## Run the model smoke test
	$(COMPOSE) run --rm magnitude-test

model-list: ## List downloaded models
	$(COMPOSE) run --rm --entrypoint /bin/bash magnitude -c \
		'magnitude serve & srv=$$!; sleep 15; magnitude hardware; magnitude models status; kill $$srv'

shell: ## Interactive shell
	$(COMPOSE) run --rm magnitude bash

clean: ## Remove containers + models
	$(COMPOSE) down -v

prune: ## Remove built images
	docker image rm -f magnitude:local || true
