# set python image
FROM python:3.13

# display python version
RUN python --version

# install timezone data and configure timezone
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*
COPY timezone /tmp/timezone
RUN TZ=$(cat /tmp/timezone) && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    echo "export TZ=$TZ" >> /etc/environment
ENV TZ=America/Chicago

# set working directory
WORKDIR /usr/src/app  

# update pip to latest
RUN pip install --upgrade pip

# list python packages before install
RUN pip list

# install dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# list python packages after install
RUN pip list

# copy source code
COPY . .

# execute the script
ENTRYPOINT ["python3", "-m"]
# defaults runtime parameters to emulator zone 0 if runtime parameters are not provided
# [module, thermostat, zone, poll time, connect time, tolerance, target mode, measurements]
CMD ["thermostatsupervisor.supervise", "emulator", "0", "30", "86400", "3", "OFF_MODE", "4"]
