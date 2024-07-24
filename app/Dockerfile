FROM python:3.10-slim

WORKDIR /app

RUN apt update && apt -y upgrade

COPY requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt
