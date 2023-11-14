### Builder image
# using ubuntu LTS version
FROM lsiobase/ubuntu:jammy AS builder-image

# avoid stuck build due to user prompt
ARG DEBIAN_FRONTEND=noninteractive

# install python
RUN apt-get update && apt-get install --no-install-recommends -y python3.12 python3.12-dev python3.12-venv python3-pip python3-wheel build-essential && \
	apt-get clean && rm -rf /var/lib/apt/lists/*

# create and activate virtual environment
# using final folder name to avoid path issues with packages
RUN python3.12 -m venv /home/abc/venv
ENV PATH="/home/abc/venv/bin:$PATH"

# install requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir wheel
RUN pip3 install --no-cache-dir -r requirements.txt

### Runner image
FROM lsiobase/ubuntu:jammy AS runner-image

# install python
RUN apt-get update && apt-get install --no-install-recommends -y python3.12 python3-venv && \
	apt-get clean && rm -rf /var/lib/apt/lists/*

# use unprivileged user and virtual environment
RUN chsh -s /bin/bash abc
COPY --from=builder-image /home/abc/venv /home/abc/venv

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
ENV VIRTUAL_ENV=/home/abc/venv
ENV PATH="/home/abc/venv/bin:$PATH"

# run server when container starts
CMD [ "python3", "./mediator.py", "--log-level", "1" ]

