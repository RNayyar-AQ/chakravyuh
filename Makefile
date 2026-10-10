# CHAKRAVYUH — one command per thing you might want to do.
#
# Everything runs from the repository root. `app/` holds the system; `data/`, `docs/` and
# `tests/` sit beside it because they are inputs, outputs for people, and proof respectively.

# Prefer the repo's venv when it exists and is not already active, so `make test` does not
# silently run against a different interpreter than `make install` populated.
PY ?= $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)

.DEFAULT_GOAL := help
.PHONY: help install dev narrate build artefacts artefacts-fast test lint api web clean

help:            ## Show this list
	@grep -hE '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | sort | awk -F':.*?## ' '{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:         ## Install Python and Node dependencies
	$(PY) -m pip install -e ".[test,ui,kb,api]"
	cd app/web && npm install

dev:             ## Run backend and frontend together (http://localhost:3000)
	$(PY) app/dev.py

narrate:         ## Run one simulation and narrate it: retrieval, agents, engine, Game Master
	$(PY) app/scripts/narrate_run.py $(ARGS)

artefacts:       ## Run the whole pipeline and export the UI bundle — commit what this writes
	$(PY) app/scripts/showcase.py

artefacts-fast:  ## Same without the slow stages: a local preview, never a commit
	$(PY) app/scripts/showcase.py --fast

build:           ## Produce the static site in app/web/out
	$(MAKE) artefacts
	cd app/web && npm run build

deploy-check:    ## Build exactly as Vercel does: no Python, straight from committed files
	npm --prefix app/web ci
	npm --prefix app/web run build
	@echo "built app/web/out -- this is what Vercel serves"

test:            ## Run the Python suite
	$(PY) -m pytest -q

lint:            ## Ruff over Python, ESLint and tsc over the frontend
	$(PY) -m ruff check app tests
	cd app/web && npm run lint && npx tsc --noEmit

api:             ## Run only the backend
	$(PY) -m uvicorn app.backend.main:app --reload --port 8000

web:             ## Run only the frontend (static artefacts, no backend)
	$(PY) app/dev.py --no-backend

clean:           ## Remove every generated artefact
	rm -rf outputs runs data/clauses data/chroma app/web/out app/web/.next app/web/public/data
