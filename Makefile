.PHONY: test run docker lint

test:
	pytest tests/ -v --tb=short

run:
	uvicorn web.app:app --reload --host 0.0.0.0 --port 8000

docker:
	docker build -t coding-agent-harness .

docker-run:
	docker run -p 8000:8000 -v agent_data:/app/.agent coding-agent-harness
