FROM python:3.9.1

WORKDIR /run

# expose server listening ports
EXPOSE 20000/tcp
EXPOSE 20001/tcp

# copy server requirements and scripts
COPY mediator.py .

# run server when container starts
CMD [ "python", "./mediator.py" ]

