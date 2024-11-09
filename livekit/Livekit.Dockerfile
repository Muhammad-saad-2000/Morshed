FROM ubuntu:latest

# Install dependencies
RUN apt-get update && \
    apt-get install -y curl wget ca-certificates gnupg lsb-release apt-transport-https

# Install LiveKit server
RUN curl -sSL https://get.livekit.io | bash

# Expose ports
EXPOSE 7880 
EXPOSE 7443

# Define the entrypoint
CMD ["livekit-server", "--dev", "--bind", "0.0.0.0"]