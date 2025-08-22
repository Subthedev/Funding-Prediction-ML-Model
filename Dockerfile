# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files into container
COPY . .

# Expose port Flask will run on
EXPOSE 8000

# Run the app
CMD ["python", "main.py"]
# Use gunicorn for production
# CMD ["gunicorn", "main:app", "--bind", "0.0.