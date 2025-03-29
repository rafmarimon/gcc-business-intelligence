# For development (includes Airbyte CDK and testing tools)
FROM gcc-connector-base:development as dev

WORKDIR /connector

# Copy connector-specific requirements and source code
COPY requirements.txt .
COPY . .

# Install additional dependencies specific to this connector
RUN pip install --no-cache-dir -r requirements.txt

# Set the entrypoint
ENTRYPOINT ["python", "/connector/main.py"]

# For production (minimal dependencies, no dev tools)
FROM gcc-connector-base:production as prod

WORKDIR /connector

# Copy connector-specific requirements and source code
COPY requirements.txt .
COPY . .

# Install additional dependencies specific to this connector
RUN pip install --no-cache-dir -r requirements.txt

# Set the entrypoint
ENTRYPOINT ["python", "/connector/main.py"] 