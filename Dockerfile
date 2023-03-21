FROM python:3.12.0a5-slim

WORKDIR /run

# expose server listening ports
EXPOSE 80/tcp
EXPOSE 443/tcp

# copy server requirements and scripts
COPY mediator.py .

# run server when container starts
CMD [ "python3", "./mediator.py", "--log-level", "1" ]

