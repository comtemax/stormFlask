# syntax=docker/dockerfile:1

FROM python:3.8

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

ADD src/ ./src
ADD templates/ ./templates

COPY app.py .
RUN mkdir /uploads
VOLUME /uploads

CMD ["python3", "-m", "flask", "run", "--port=8085"]