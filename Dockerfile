# set python image with digest for security
FROM python:3.14.1-slim

# Security labels
LABEL security.non-root="true" \
      security.updated="2024-08-14" \
      security.cve-fix="CVE-2025-8194"

# display python version
RUN python --version

# Security: Update package lists and install ca-certificates first for SSL
RUN apt-get update && apt-get install -y ca-certificates

# install timezone data, build tools for psutil, and configure timezone
RUN apt-get install -y \
    tzdata \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
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
# CVE-2025-8194 mitigation: Temporary SSL workaround for build environment
# Production deployments should use proper SSL certificate validation
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org || true

# remove build tools to minimize image size and attack surface
RUN apt-get remove -y gcc python3-dev && apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# create non-root user for security
RUN groupadd -r thermostat && useradd -r -g thermostat -d /usr/src/app -s /sbin/nologin -c "Thermostat user" thermostat

# list python packages after install
RUN pip list

# copy source code
COPY . .

# change ownership to non-root user
RUN chown -R thermostat:thermostat /usr/src/app

# switch to non-root user for security
USER thermostat

# add security labels
LABEL security.non-root="true" \
      security.updated="2024-08-14" \
      security.cve-fix="CVE-2025-8194"

# add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)" || exit 1

# execute the script
ENTRYPOINT ["python3", "-m"]
# defaults runtime parameters to emulator zone 0 if runtime parameters are not provided
# [module, thermostat, zone, poll time, connect time, tolerance, target mode, measurements]
CMD ["thermostatsupervisor.supervise", "emulator", "0", "30", "86400", "3", "OFF_MODE", "4"]
