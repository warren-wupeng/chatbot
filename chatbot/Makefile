up-local:
	export $(shell cat envs/.env | grep -v '^#' | xargs ) && poetry run chatbot

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down --remove-orphans