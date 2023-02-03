FROM python:3.9

WORKDIR /code

# expose port number
EXPOSE 5400

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . /code

CMD ["uvicorn","paas_launch:app", "--host", "0.0.0.0", "--port", "5400", "--root-path", "/connectree_backend"]
