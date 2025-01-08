FROM python:3.12
LABEL authors="tenag"
WORKDIR /app

COPY ./r.txt /app/r.txt
RUN pip3 install -r r.txt

COPY . /app


CMD ["python","bot.py"]