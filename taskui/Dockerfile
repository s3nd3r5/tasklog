FROM python:3

VOLUME /secrets

EXPOSE 5000/tcp

WORKDIR /opt/taskui
ENV FLASK_APP=/opt/taskui/taskui.py

COPY requirements.txt ./
RUN python3 -m pip install -U -r requirements.txt

COPY static ./static
COPY templates ./templates
COPY taskui.py  ./

CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0"]

