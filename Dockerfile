### Builder image
# using ubuntu LTS version
FROM ubuntu:latest AS builder-image

# avoid stuck build due to user prompt
ARG DEBIAN_FRONTEND=noninteractive

# install python
RUN apt-get update && apt-get install --no-install-recommends -y python3.11 python3.11-dev python3.11-venv python3-pip python3-wheel build-essential && \
	apt-get clean && rm -rf /var/lib/apt/lists/*

# create and activate virtual environment
# using final folder name to avoid path issues with packages
RUN python3.11 -m venv /root/venv
ENV PATH="/root/venv/bin:$PATH"

# install requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir wheel
RUN pip3 install --no-cache-dir -r requirements.txt

### Runner image
FROM ubuntu:latest AS runner-image

# install python
RUN apt-get update && apt-get install --no-install-recommends -y python3.11 python3-venv && \
	apt-get clean && rm -rf /var/lib/apt/lists/*

# use virtual environment
COPY --from=builder-image /root/venv /root/venv

# create directory for runtime and switch to user
RUN mkdir -p /run
WORKDIR /run
COPY mediator.py .

# expose server listening ports
EXPOSE 80/tcp
EXPOSE 443/tcp

# make sure all messages always reach console
ENV PYTHONUNBUFFERED=1

# activate virtual environment
ENV VIRTUAL_ENV=/root/venv
ENV PATH="/root/venv/bin:$PATH"

# run server when container starts
CMD [ "python3", "./mediator.py", "--log-level", "1" ]

