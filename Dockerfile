FROM python:buster

WORKDIR /run

# expose server listening ports
EXPOSE 20000/tcp
EXPOSE 20001/tcp

# copy server requirements and scripts
COPY mediator.py .

# run server when container starts
CMD [ "python3", "./mediator.py" ]

