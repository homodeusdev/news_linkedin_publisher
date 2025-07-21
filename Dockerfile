FROM public.ecr.aws/lambda/python:3.11

RUN pip install poetry
RUN poetry self add poetry-plugin-export
RUN yum update -y && yum install -y zip

WORKDIR /var/task

COPY pyproject.toml poetry.lock* ./
RUN poetry export -f requirements.txt --without-hashes -o requirements.txt
RUN pip install -r requirements.txt -t .

COPY lambda_function.py ./
RUN zip -r deployment_package.zip lambda_function.py *

CMD ["lambda_function.lambda_handler"]