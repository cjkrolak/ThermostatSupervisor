# set python image
FROM python:3  

# set working directory
WORKDIR /usr/src/app  

# install dependencies
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# copy source code
COPY . .

# execute the script for Honeywell zone 0
CMD ["supervise.py", "honeywell", "0"]
ENTRYPOINT ["python3"]
