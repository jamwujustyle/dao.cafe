FROM python:3.11-alpine
LABEL maintainer='codebuddha'

ENV PYTHONUNBUFFERED=1

RUN mkdir -p /vol/web/media && \
    mkdir -p /vol/web/static && \
    mkdir -p /vol/web/media/images
# Copy requirements first for better caching
COPY ./requirements.txt /tmp/requirements.txt
COPY . /server
WORKDIR /server

EXPOSE 8000

RUN apk add --no-cache \
    postgresql-client \
    jpeg-dev \
    zlib-dev \
    musl-dev \
    postgresql-dev \
    gcc \
    libc-dev \
    linux-headers \
    build-base && \
    python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    /py/bin/pip install -r /tmp/requirements.txt && \
    # create user
        adduser \
        --disabled-password \
        --no-create-home \
        django-user && \
    # then create dirs and set permissions
    cp ./static/default-placeholder.jpg /vol/web/media/images/default-placeholder.jpg && \
    cp -r ./static/* /vol/web/static/ && \
    chown -R django-user:django-user /vol /py /server && \
    chmod -R 755 /vol && \
    # cleanup
    apk del gcc musl-dev libc-dev linux-headers build-base && \
    rm -rf /tmp

ENV PATH="/py/bin:$PATH"
ENV PYTHONPATH="/server"
ENV DJANGO_SETTINGS_MODULE=app.settings

USER django-user
COPY --chown=django-user:django-user ./static/ /server/static/

CMD ["sh", "run.sh"]
