.PHONY: build build-admin export-openapi test dev dev-backend dev-frontend clean repo lint format

# Build admin UI and copy to backend static folder
build-admin:
	cd apps/admin && yarn install && yarn build
	rm -rf packages/tinybase/tinybase/static/app
	cp -r apps/admin/dist packages/tinybase/tinybase/static/app

# Export OpenAPI spec
export-openapi:
	uv run python scripts/export_openapi.py

# Run all tests
test:
	uv run pytest -n auto

# Start both backend and frontend development servers
dev:
	@echo "Starting backend (port 8000) and frontend (port 5173) dev servers..."
	@trap 'kill 0' INT TERM; \
		uv run tinybase serve --reload & \
		cd apps/admin && yarn dev & \
		wait

# Start backend development server only
dev-backend:
	uv run tinybase serve --reload

# Start frontend development server only
dev-frontend:
	cd apps/admin && yarn dev

# Full build pipeline
build: build-admin
	uv build -p packages/tinybase

# Clean build artifacts
clean:
	rm -rf packages/tinybase/tinybase/static/app
	rm -rf apps/admin/dist
	rm -rf dist build *.egg-info

# Lint all files (Python + Markdown)
# Uses pre-commit to ensure consistent tool versions
lint:
	uv run pre-commit run ruff --all-files
	uv run pre-commit run markdownlint --all-files

# Format all files (Python + Markdown)
# Uses pre-commit to ensure consistent tool versions
format:
	uv run pre-commit run ruff-format --all-files
	uv run pre-commit run ruff --all-files
	uv run pre-commit run mdformat --all-files

# Install pre-commit hooks
install-hooks:
	uv run pre-commit install

# Run all pre-commit hooks
pre-commit:
	uv run pre-commit run --all-files

# Repo management CLI passthrough
# Usage: make repo version bump patch
repo:
	uv run python scripts/repo.py $(filter-out $@,$(MAKECMDGOALS))

%:
	@:
