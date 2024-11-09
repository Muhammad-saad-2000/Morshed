# Use an official Python runtime as a parent image
FROM python:3.11.5-slim

# Set the working directory
WORKDIR /app

# Copy the content of the backend directory to the working directory
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt


# Run the application
CMD ["python", "main.py", "dev"]