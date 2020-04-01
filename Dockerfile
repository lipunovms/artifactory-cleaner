FROM python:3

env PYTHONWARNINGS="ignore:Unverified HTTPS request"
WORKDIR /app

COPY cleaner.py requirements.txt ./
RUN pip install -r requirements.txt

CMD ["python","cleaner.py"]