# Makefile for Nifty 100 Financial Intelligence Platform

.PHONY: load test clean

load:
	python src/etl/loader.py

test:
	pytest tests/

ratios:
	python src/analytics/ratios.py

clean:
	if exist src\etl\__pycache__ rmdir /s /q src\etl\__pycache__
	if exist tests\etl\__pycache__ rmdir /s /q tests\etl\__pycache__
	if exist .pytest_cache rmdir /s /q .pytest_cache
