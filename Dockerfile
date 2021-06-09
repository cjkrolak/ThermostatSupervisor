FROM python:3
WORKDIR /usr/src/app
COPY . .
CMD ["supervise.py"]
ENTRYPOINT ["python3"]
