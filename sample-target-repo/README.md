# Refund Bot

A simple AI-powered refund processing agent for an e-commerce platform.

## What this agent does

This agent handles customer refund requests. It validates the order,
checks eligibility, and processes the refund automatically.

## Business rules

- Refunds are only allowed within 30 days of the order date
- Refund amount must never be negative
- An order can only be refunded once
- Maximum combined coupon discount on any order is 50%
- Refund amount can never exceed the original order amount

## Tech stack

- Python 3.11
- FastAPI
- No external LLM — pure business logic agent

## Running locally

```
pip install -r requirements.txt
python main.py
```

The agent exposes a `/invoke` endpoint that accepts refund requests.
