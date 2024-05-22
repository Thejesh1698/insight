# Use a base image that includes Python and other necessary tools
FROM python:3.9-slim

# Install build dependencies for C extensions - to resolve the gcc error
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

# Set a working directory
WORKDIR /app

# Copy your project files into the container
COPY . /app

# Install any required Python packages
ENV PIP_DEFAULT_TIMEOUT=100
# https://stackoverflow.com/questions/68474458/error-run-pip-install-r-requirements-txt-when-using-docker-compose-up
RUN pip install -r requirements.txt

# Expose the port that the web server will listen on
EXPOSE 8000

# Set the entry point to your script that will start the server
ENTRYPOINT ["python", "application.py"]
