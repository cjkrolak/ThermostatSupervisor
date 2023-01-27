# set python image
# bunch 1.0.1 pkg is not compatible with py3.11 due to universal newline in build instructions.
FROM python:3.10  

# set working directory
WORKDIR /usr/src/app  

# install dependencies
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# copy source code
COPY . .

# execute the script, default to Honeywell zone 0 if runtime parameters are not provided
#CMD ["supervise.py", "honeywell", "0"]
#ENTRYPOINT ["python3"]
ENTRYPOINT ["python3", "-m"]
# defaults runtime parameters if not specified
# [module, thermostat, zone, poll time, connect time, tolerance, target mode, measurements]
CMD ["thermostatsupervisor.supervise", "emulator", "0", "30", "86400", "3", "OFF_MODE", "4"]
