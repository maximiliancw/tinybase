.PHONY: build build-admin export-openapi test dev clean repo

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
	uv run pytest

# Start development server (backend)
dev:
	uv run tinybase serve --reload

# Full build pipeline
build: build-admin
	uv build -p packages/tinybase

# Clean build artifacts
clean:
	rm -rf packages/tinybase/tinybase/static/app
	rm -rf apps/admin/dist
	rm -rf dist build *.egg-info

# Repo management CLI passthrough
# Usage: make repo version bump patch
repo:
	uv run python scripts/repo.py $(filter-out $@,$(MAKECMDGOALS))

%:
	@:
