FROM python:3

VOLUME /secrets

WORKDIR /opt/taskbot

# get requirements (sometimes changes)
COPY requirements.txt ./ 
RUN python3 -m pip install -U --no-cache-dir -r ./requirements.txt

# often changes
COPY taskbot.py ./

CMD ["python3", "./taskbot.py"]
