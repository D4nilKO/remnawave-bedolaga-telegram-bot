.PHONY: up
up: ## Поднять контейнеры (detached)
	@echo "🚀 Поднимаем контейнеры (detached)..."
	docker compose up -d --build

.PHONY: up-follow
up-follow: ## Поднять контейнеры с логами
	@echo "📡 Поднимаем контейнеры (в консоли)..."
	docker compose up --build

.PHONY: down
down: ## Остановить и удалить контейнеры
	@echo "🛑 Останавливаем и удаляем контейнеры..."
	docker compose down

.PHONY: reload
reload: ## Перезапустить контейнеры (detached)
	@$(MAKE) down
	@$(MAKE) up

.PHONY: reload-follow
reload-follow: ## Перезапустить контейнеры с логами
	@$(MAKE) down
	@$(MAKE) up-follow

.PHONY: test
test: ## Запустить тесты
	@echo "🧪 Запускаем тесты..."
	pytest -v

.PHONY: migrate
migrate: ## Применить миграции (alembic upgrade head)
	uv run alembic upgrade head

.PHONY: migration
migration: ## Создать миграцию (usage: make migration m="description")
	uv run alembic revision --autogenerate -m "$(m)"

.PHONY: migrate-stamp
migrate-stamp: ## Пометить БД как актуальную (для существующих БД)
	uv run alembic stamp head

.PHONY: migrate-history
migrate-history: ## Показать историю миграций
	uv run alembic history --verbose

.PHONY: help
help: ## Показать список доступных команд
	@echo ""
	@echo "📘 Команды Makefile:"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?##' $(MAKEFILE_LIST) | \
		sed -E 's/:.*?## /| /' | \
		awk -F'|' '{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo ""
