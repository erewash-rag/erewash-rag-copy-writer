FROM public.ecr.aws/lambda/python:3.8

# Copy function code and articles
COPY lambda_function.py ./

# Install dependencies if requirements.txt exists
COPY requirements.txt ./
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt -t .; fi

# Set the CMD to your handler (function name in lambda_function.py)
CMD ["lambda_function.lambda_handler"] 