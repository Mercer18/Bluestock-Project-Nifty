# Makefile for Nifty 100 Financial Intelligence Platform

.PHONY: load test clean

load:
	python src/etl/loader.py

test:
	pytest tests/

ratios:
	python src/analytics/ratios.py

screener:
	python src/screener/engine.py

peer:
	python src/analytics/peer.py

radar:
	python src/analytics/radar.py

run-app:
	streamlit run src/app.py

clean:
	if exist src\etl\__pycache__ rmdir /s /q src\etl\__pycache__
	if exist src\analytics\__pycache__ rmdir /s /q src\analytics\__pycache__
	if exist src\screener\__pycache__ rmdir /s /q src\screener\__pycache__
	if exist tests\etl\__pycache__ rmdir /s /q tests\etl\__pycache__
	if exist tests\kpi\__pycache__ rmdir /s /q tests\kpi\__pycache__
	if exist .pytest_cache rmdir /s /q .pytest_cache
