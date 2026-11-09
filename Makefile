# Makefile for Helios Web Platform Verification Pipeline

.PHONY: verify-env test-unit test-integration e2e security performance audit all

verify-env:
	python scripts/verify_env.py environment_check.log

test-unit:
	pytest tests/test_razorpay_webhook.py --cov=skelion_agent.billing_routes --cov-report=xml:coverage/python/coverage.xml --cov-fail-under=100
	npm --prefix skelion_website run test:coverage

test-integration:
	pytest -m integration tests/test_razorpay_webhook.py tests/test_razorpay_wiremock.py --junitxml=integration/report.xml

e2e:
	npx playwright test

security:
	semgrep --config=local_rules.yaml --metrics=off
	detect-secrets scan > security/detect-secrets.json

performance:
	k6 run load/k6_load_test.js

audit:
	python scripts/generate_verification_report.py

all: verify-env test-unit test-integration audit
