#Use an official python image as the base image
FROM python:3.8-slim-buster

#Set the working directory in the container to /app
WORKDIR /app

#copy the content of the current directory into the containter /app directory
COPY . /app

#Upgrade pip
RUN pip install --upgrade pip

#Install any neede packages
RUN pip install --no-cache-dir -r requirements.txt

#set the default commands to run when starting the container
CMD {"python", "main.py"}