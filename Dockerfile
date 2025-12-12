FROM python:3.10

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Command to run the app
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
