FROM python:3.14-slim-bookworm

USER root

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    DJANGO_SETTINGS_MODULE=config.settings

COPY --chown=root:root --chmod=777 . /undine/
WORKDIR /undine/tests/test_federation/compatibility

RUN pip install "django>=6" "/undine/[federation-tracing]"

EXPOSE 4001

CMD ["python", "manage.py", "runserver", "0.0.0.0:4001"]
