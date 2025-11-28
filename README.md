# Sistema de Notas de Venta - API REST en AWS Lambda

Sistema de gestión de notas de venta implementado como aplicación serverless siguiendo la metodología de los 12 factores.

> 📘 **¿Usas AWS Academy?** Lee la guía completa: [GUIA-AWS-ACADEMY.md](GUIA-AWS-ACADEMY.md)

## 📋 Descripción

Este proyecto implementa un API REST para la gestión de notas de venta con las siguientes características:

- **CRUD de Clientes** (ID, Razón Social, Nombre Comercial, RFC, Correo electrónico, Teléfono)
- **CRUD de Domicilios** (ID, Domicilio, Colonia, Municipio, Estado, Tipo de Dirección)
- **CRUD de Productos** (ID, Nombre, Unidad de Medida, Precio Base)
- **Notas de Venta** con generación automática de PDF
- **Notificaciones por correo electrónico** vía Amazon SNS/SES

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         API Gateway                                  │
└─────────────────────────────────────────────────────────────────────┘
                    │              │              │
                    ▼              ▼              ▼
         ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
         │   Lambda     │ │   Lambda     │ │   Lambda     │
         │  Catálogos   │ │    Notas     │ │Notificaciones│
         └──────────────┘ └──────────────┘ └──────────────┘
                │              │    │              │
                ▼              ▼    │              ▼
         ┌──────────────┐          │        ┌──────────────┐
         │   DynamoDB   │◄─────────┘        │   Amazon     │
         │   (Tablas)   │                   │     SES      │
         └──────────────┘                   └──────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   Amazon S3  │
                        │    (PDFs)    │
                        └──────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │  Amazon SNS  │
                        │ (Notific.)   │
                        └──────────────┘
```

## 📁 Estructura del Proyecto

```
proyecto-notas-venta/
├── modulo-catalogos/          # Módulo 1: CRUD de Catálogos
│   ├── src/
│   │   └── app.py
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── docker-compose.yml
├── modulo-notas/              # Módulo 2: Notas de Venta
│   ├── src/
│   │   └── app.py
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── docker-compose.yml
├── modulo-notificaciones/     # Módulo 3: Notificaciones
│   ├── src/
│   │   └── app.py
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── docker-compose.yml
├── infrastructure/            # Infraestructura SAM
│   ├── template.yaml
│   └── samconfig.toml
├── .github/
│   └── workflows/             # CI/CD Pipelines
│       ├── catalogos.yml
│       ├── notas.yml
│       ├── notificaciones.yml
│       └── infrastructure.yml
└── README.md
```

## 🔧 Tecnologías Utilizadas

- **Runtime**: Python 3.11
- **Framework**: FastAPI + Mangum
- **Base de Datos**: Amazon DynamoDB
- **Almacenamiento**: Amazon S3
- **Notificaciones**: Amazon SNS + SES
- **Contenedores**: Docker
- **Infraestructura**: AWS SAM
- **CI/CD**: GitHub Actions
- **Monitoreo**: Amazon CloudWatch

## 📊 Métricas Implementadas

### Métricas de Comportamiento (HTTP)
- `HTTPRequests2xx` - Requests exitosos
- `HTTPRequests4xx` - Errores de cliente
- `HTTPRequests5xx` - Errores de servidor

### Métricas de Tiempo de Ejecución
- `ExecutionTime` - Tiempo de ejecución por endpoint
- `TiempoGeneracionNota` - Tiempo de generación de nota completa

### Dimensiones
Todas las métricas incluyen:
- `Environment` - local, staging, production
- `Service` - catalogos, notas-venta, notificaciones
- `Endpoint` - nombre del endpoint específico

## 🚨 Alertas Configuradas

1. **Errores 5xx en Catálogos**: Alerta cuando hay más de 5 errores en 5 minutos
2. **Latencia Alta en Notas**: Alerta cuando la generación de notas supera 5 segundos
3. **Errores en Notificaciones**: Alerta cuando hay más de 3 errores de envío

### ¿Por qué estos umbrales?

- **5 errores 5xx**: Indica un problema sistémico, no errores esporádicos
- **5 segundos de latencia**: Una nota no debería tardar tanto; indica problemas de rendimiento
- **3 errores de envío**: Afecta directamente la experiencia del cliente

## 📈 Dashboard

El dashboard de CloudWatch incluye:

1. **Percentiles de Tiempo de Ejecución (p50, p90, p99)**
   - Widget para módulo de catálogos
   - Widget para generación de notas

2. **Comportamiento HTTP**
   - Gráfico de requests por código de respuesta
   - Separado por módulo

3. **Operaciones CRUD**
   - Conteo de operaciones por tipo

4. **Notas y PDFs**
   - Notas creadas
   - PDFs generados
   - PDFs descargados

## 🚀 Despliegue

### Prerrequisitos

1. AWS CLI configurado
2. SAM CLI instalado
3. Docker instalado
4. Cuenta de GitHub con acceso a Actions

### Variables de Entorno Requeridas

```bash
# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx

# Aplicación
ENVIRONMENT=local|staging|production
EXPEDIENTE=A01234567
SES_SOURCE_EMAIL=noreply@tudominio.com
```

### Despliegue Local

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/proyecto-notas-venta.git
cd proyecto-notas-venta

# Levantar módulo de catálogos
cd modulo-catalogos
docker-compose up -d

# Levantar módulo de notas
cd ../modulo-notas
docker-compose up -d

# Levantar módulo de notificaciones
cd ../modulo-notificaciones
docker-compose up -d
```

### Despliegue en AWS

```bash
# Desde la carpeta infrastructure
cd infrastructure

# Build y deploy
sam build
sam deploy --guided
```

### CI/CD Automático

El despliegue se realiza automáticamente mediante GitHub Actions:

1. **Push a `develop`**: Despliega a staging
2. **Push a `main`**: Despliega a producción
3. **Pull Request**: Ejecuta tests y lint

## 📝 API Endpoints

### Catálogos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /catalogos/clientes | Listar clientes |
| POST | /catalogos/clientes | Crear cliente |
| GET | /catalogos/clientes/{id} | Obtener cliente |
| PUT | /catalogos/clientes/{id} | Actualizar cliente |
| DELETE | /catalogos/clientes/{id} | Eliminar cliente |
| GET | /catalogos/domicilios/cliente/{id} | Listar domicilios |
| POST | /catalogos/domicilios | Crear domicilio |
| GET | /catalogos/productos | Listar productos |
| POST | /catalogos/productos | Crear producto |

### Notas de Venta

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /notas | Listar notas |
| POST | /notas | Crear nota (genera PDF y notifica) |
| GET | /notas/{id} | Obtener nota |
| GET | /notas/{id}/pdf | Descargar PDF |
| POST | /notas/{id}/reenviar | Reenviar notificación |

## 🔒 Seguridad

- Todas las Lambdas tienen políticas IAM de mínimo privilegio
- El bucket S3 tiene bloqueo de acceso público
- Las credenciales se manejan via AWS Secrets Manager / GitHub Secrets
- CORS configurado apropiadamente

## 📚 12-Factor App Compliance

| Factor | Implementación |
|--------|----------------|
| 1. Codebase | Un repositorio, múltiples deploys |
| 2. Dependencies | requirements.txt explícito |
| 3. Config | Variables de entorno |
| 4. Backing services | DynamoDB, S3, SNS, SES como recursos |
| 5. Build, release, run | GitHub Actions pipeline |
| 6. Processes | Lambdas stateless |
| 7. Port binding | API Gateway |
| 8. Concurrency | Lambda auto-scaling |
| 9. Disposability | Lambdas efímeras |
| 10. Dev/prod parity | Mismo template, diferentes params |
| 11. Logs | CloudWatch Logs |
| 12. Admin processes | SAM CLI para admin |

## 👤 Autor

**Tu Nombre**
- Expediente: A01234567
- Materia: ESI3898K

## 📄 Licencia

Este proyecto es parte de un examen académico.
