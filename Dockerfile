FROM python:3-alpine

EXPOSE 8080
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY chat_server.py .

CMD [ "python", "./chat_server.py" ]