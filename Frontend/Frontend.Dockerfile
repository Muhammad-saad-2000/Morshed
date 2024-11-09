# Use an official Node.js runtime as a parent image
FROM node:20

# Set the working directory
WORKDIR /app

# Copy the content of the frontend directory to the working directory
COPY . .

RUN npm install --force

# Expose the frontend port
EXPOSE 3000

# Start the React application
CMD ["npm", "run", "dev"]