FROM public.ecr.aws/lambda/python:3.11

# Copiar requirements primero para aprovechar cache
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ ${LAMBDA_TASK_ROOT}/

# Comando para Lambda
CMD ["app.handler"]
