# 📝 RESPUESTAS A LAS PREGUNTAS DEL EXAMEN

## Pregunta 1: ¿Cuáles son los factores que se han cubierto durante el desarrollo de la aplicación?

### Factores Cubiertos (10 de 12):

| # | Factor | Implementación en el Proyecto |
|---|--------|-------------------------------|
| **1** | **Codebase** | Un repositorio Git único con los 3 módulos. Cada push a `main` dispara el despliegue a producción. El mismo código fuente se usa para todos los ambientes. |
| **2** | **Dependencies** | Cada módulo tiene su propio `requirements.txt` que declara explícitamente todas las dependencias con versiones fijas (ej: `fastapi==0.109.0`). |
| **3** | **Config** | Toda la configuración está en variables de entorno: `ENVIRONMENT`, `TABLE_CLIENTES`, `S3_BUCKET`, `SNS_TOPIC_ARN`, etc. Definidas en CloudFormation y GitHub Secrets. |
| **4** | **Backing Services** | DynamoDB, S3, SNS y SES son tratados como recursos adjuntos, configurados via URL/ARN en variables de entorno. Pueden cambiarse sin modificar código. |
| **5** | **Build, Release, Run** | Separación clara: GitHub Actions hace **build** (Docker + ZIP), CloudFormation hace **release** (configura infraestructura), Lambda hace **run** (ejecuta). |
| **6** | **Processes** | Cada Lambda es stateless. No guarda nada en memoria entre invocaciones. Todo el estado está en DynamoDB y S3. |
| **7** | **Port Binding** | API Gateway expone el servicio vía HTTPS. Cada Lambda se auto-contiene con FastAPI+Mangum. |
| **8** | **Concurrency** | Lambda escala horizontalmente de forma automática. Cada request es una instancia independiente. |
| **9** | **Disposability** | Lambdas inician rápido (~500ms cold start) y terminan gracefully. Los procesos son efímeros. |
| **10** | **Dev/Prod Parity** | Mismo código, mismo Dockerfile, mismo template. Solo cambia `ENVIRONMENT=local` vs `ENVIRONMENT=production`. |
| **11** | **Logs** | Todos los logs van a CloudWatch Logs automáticamente. Se usa `print()` y los logs estructurados de FastAPI. |
| **12** | **Admin Processes** | ⚠️ Parcialmente cubierto - Se podrían agregar scripts de migración como tareas Lambda separadas. |

### Evidencia en el Código:

```python
# Factor 3 - Config via Environment Variables (app.py)
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
TABLE_CLIENTES = os.getenv("TABLE_CLIENTES", "clientes")
S3_BUCKET = os.getenv("S3_BUCKET", f"{EXPEDIENTE}-esi3898k-examen1")

# Factor 6 - Stateless (cada request es independiente)
@app.post("/clientes")
async def crear_cliente(cliente: ClienteCreate):
    # No hay estado en memoria, todo va a DynamoDB
    table.put_item(Item=item)
```

---

## Pregunta 2: ¿Cuáles han sido los retos al separar las aplicaciones? ¿Cuál ha sido la parte más complicada?

### Retos Encontrados:

#### 1. **Comunicación entre módulos** (Más Complicado)
- **Problema**: El módulo de Notas necesita datos de Clientes y Productos, pero son módulos separados.
- **Solución**: Compartir las mismas tablas DynamoDB. Notas tiene permisos de LECTURA en las tablas de Catálogos.
- **Alternativa ideal**: Crear un API Gateway interno o usar eventos, pero agregaría latencia.

```yaml
# template-academy.yaml - Notas puede leer tablas de Catálogos
- DynamoDBReadPolicy:
    TableName: !Ref ClientesTable
```

#### 2. **Comunicación asíncrona para notificaciones**
- **Problema**: Después de crear una nota, hay que enviar correo sin bloquear la respuesta.
- **Solución**: SNS como intermediario. Notas publica → SNS notifica → Lambda Notificaciones procesa.

```
[Crear Nota] → [Publicar SNS] → [Return Response]
                     ↓
              [Lambda Notificaciones] → [Enviar Email]
```

#### 3. **Manejo de metadatos del PDF en S3**
- **Problema**: Necesitamos trackear `hora-envio`, `nota-descargada`, `veces-enviado` por cada PDF.
- **Solución**: Usar metadata de objetos S3 y actualizarla con `copy_object` + `MetadataDirective='REPLACE'`.

#### 4. **Consistencia de dependencias**
- **Problema**: 3 módulos podrían tener versiones diferentes de boto3.
- **Solución**: Cada `requirements.txt` tiene versiones fijas idénticas.

#### 5. **AWS Academy - Restricciones de ECR**
- **Problema**: No se puede crear repositorios ECR en Learner Lab.
- **Solución**: Las imágenes Docker SE CONSTRUYEN (cumple requisito) pero se despliegan como ZIP.

### Lo Más Complicado: **La Orquestación de la Creación de Notas**

```
1. Validar cliente existe (leer de otra tabla)
2. Validar domicilios existen (leer de otra tabla)  
3. Validar productos existen (leer de otra tabla)
4. Calcular totales
5. Guardar nota en DynamoDB
6. Guardar contenido en otra tabla
7. Generar PDF con ReportLab
8. Subir PDF a S3 con metadatos
9. Publicar a SNS para notificación
10. Retornar respuesta
```

Todo esto debe ser **transaccional conceptualmente** pero DynamoDB no tiene transacciones multi-tabla nativas, así que si falla en el paso 8, hay datos huérfanos.

---

## Pregunta 3: ¿Qué tipo de tarea administrativa implementarías? ¿Por qué?

### Tareas Administrativas Propuestas:

#### 1. **Limpieza de PDFs antiguos** (Prioridad Alta)
```python
# Lambda programada con CloudWatch Events (cron)
def limpiar_pdfs_antiguos(event, context):
    """Elimina PDFs de notas con más de 1 año de antigüedad"""
    # Listar objetos en S3
    # Filtrar por LastModified > 365 días
    # Eliminar objetos
```
**¿Por qué?** El bucket S3 crecerá indefinidamente. Sin limpieza, los costos aumentarán. Además, por compliance, ciertos documentos no deben guardarse más de X tiempo.

#### 2. **Reenvío masivo de notificaciones fallidas** (Prioridad Alta)
```python
def reenviar_notificaciones_fallidas(event, context):
    """Busca notas donde nota-descargada=false y veces-enviado<3"""
    # Escanear S3 buscando metadatos
    # Para cada PDF no descargado con <3 envíos
    # Publicar a SNS para reenvío
```
**¿Por qué?** Si un correo no llegó o el cliente no descargó, hay que reintentar. Esto mejora la tasa de entrega.

#### 3. **Migración de datos** (Prioridad Media)
```python
def migrar_schema_clientes(event, context):
    """Agrega campo 'activo' a todos los clientes existentes"""
    # Escanear tabla clientes
    # Actualizar cada registro con nuevo campo
```
**¿Por qué?** Cuando el esquema evoluciona, necesitamos actualizar datos existentes sin downtime.

#### 4. **Generación de reportes** (Prioridad Media)
```python
def generar_reporte_mensual(event, context):
    """Genera CSV con todas las notas del mes anterior"""
    # Query a DynamoDB con filtro de fecha
    # Generar CSV
    # Subir a S3
    # Enviar por SNS
```
**¿Por qué?** El negocio necesita reportes periódicos para contabilidad y análisis.

#### 5. **Warmup de Lambdas** (Prioridad Baja)
```python
def warmup_lambdas(event, context):
    """Invoca cada Lambda para evitar cold starts"""
    # Invocar Lambda catálogos con evento de warmup
    # Invocar Lambda notas con evento de warmup
```
**¿Por qué?** Reducir latencia de cold start en horarios de alta demanda.

### Implementación Recomendada:

```yaml
# Agregar a template-academy.yaml
LimpiezaPDFsFunction:
  Type: AWS::Lambda::Function
  Properties:
    FunctionName: admin-limpieza-pdfs
    Handler: admin_tasks.limpiar_pdfs_antiguos
    # ...

LimpiezaPDFsSchedule:
  Type: AWS::Events::Rule
  Properties:
    ScheduleExpression: "cron(0 3 1 * ? *)"  # Día 1 de cada mes a las 3am
    Targets:
      - Arn: !GetAtt LimpiezaPDFsFunction.Arn
        Id: "LimpiezaMensual"
```

---

## Resumen de Métricas Implementadas

### Métricas de Comportamiento (HTTP):
| Métrica | Namespace | Descripción |
|---------|-----------|-------------|
| `HTTPRequests2xx` | NotasVenta/Catalogos | Requests exitosos |
| `HTTPRequests4xx` | NotasVenta/Catalogos | Errores de cliente |
| `HTTPRequests5xx` | NotasVenta/Catalogos | Errores de servidor |

### Métricas de Tiempo:
| Métrica | Namespace | Descripción |
|---------|-----------|-------------|
| `ExecutionTime` | NotasVenta/Catalogos | Tiempo por endpoint (ms) |
| `TiempoGeneracionNota` | NotasVenta/Notas | Tiempo total crear nota (ms) |

### Dimensiones:
- `Environment`: `local` o `production`
- `Service`: `catalogos`, `notas-venta`, `notificaciones`
- `Endpoint`: nombre de la función

### Alertas y Umbrales:

| Alerta | Umbral | Justificación |
|--------|--------|---------------|
| 5xx Errors | >5 en 5min | 5 errores seguidos indica fallo sistémico, no esporádico |
| Alta Latencia | >5000ms | Una nota no debe tardar más de 5s, afecta UX |
| Errores Notificación | >3 en 5min | Afecta comunicación con cliente, crítico para el negocio |

### Dashboard Widgets:
1. ⏱️ **Percentiles p50, p90, p99** - Tiempo de ejecución de Catálogos
2. ⏱️ **Percentiles p50, p90, p99** - Tiempo de generación de Notas
3. 📈 **Comportamiento HTTP** - Catálogos (2xx, 4xx, 5xx)
4. 📈 **Comportamiento HTTP** - Notas (2xx, 4xx, 5xx)
5. 📧 **Notificaciones** - Enviados vs Errores
6. 📊 **Contadores CRUD** - Operaciones del día
