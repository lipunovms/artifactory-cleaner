FROM python:3

env PYTHONWARNINGS="ignore:Unverified HTTPS request"
WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY cleaner.py ./

CMD ["python","cleaner.py"]