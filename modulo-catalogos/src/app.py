"""
Módulo de Catálogos - CRUD de Clientes, Domicilios y Productos
Implementa métricas de CloudWatch para monitoreo
"""
import os
import json
import time
import uuid
import boto3
from decimal import Decimal
from datetime import datetime
from functools import wraps
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from mangum import Mangum
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from enum import Enum

# Configuración de ambiente
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
TABLE_CLIENTES = os.getenv("TABLE_CLIENTES", "clientes")
TABLE_DOMICILIOS = os.getenv("TABLE_DOMICILIOS", "domicilios")
TABLE_PRODUCTOS = os.getenv("TABLE_PRODUCTOS", "productos")

# Inicializar clientes AWS
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
cloudwatch = boto3.client('cloudwatch', region_name=AWS_REGION)

app = FastAPI(
    title="API Catálogos",
    description="CRUD de Clientes, Domicilios y Productos",
    version="1.0.0"
)

# ==================== MÉTRICAS ====================

def put_metric(metric_name: str, value: float, unit: str = "Count", dimensions: dict = None):
    """Envía una métrica a CloudWatch"""
    try:
        metric_dimensions = [
            {"Name": "Environment", "Value": ENVIRONMENT},
            {"Name": "Service", "Value": "catalogos"}
        ]
        if dimensions:
            for key, val in dimensions.items():
                metric_dimensions.append({"Name": key, "Value": str(val)})
        
        cloudwatch.put_metric_data(
            Namespace="NotasVenta/Catalogos",
            MetricData=[{
                "MetricName": metric_name,
                "Value": value,
                "Unit": unit,
                "Dimensions": metric_dimensions,
                "Timestamp": datetime.utcnow()
            }]
        )
    except Exception as e:
        print(f"Error enviando métrica: {e}")

def track_request_metrics(func):
    """Decorador para trackear métricas de requests HTTP"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            response = await func(*args, **kwargs)
            status_code = getattr(response, 'status_code', 200)
            
            # Métricas por rango de código HTTP
            if 200 <= status_code < 300:
                put_metric("HTTPRequests2xx", 1, dimensions={"Endpoint": func.__name__})
            elif 400 <= status_code < 500:
                put_metric("HTTPRequests4xx", 1, dimensions={"Endpoint": func.__name__})
            elif 500 <= status_code < 600:
                put_metric("HTTPRequests5xx", 1, dimensions={"Endpoint": func.__name__})
            
            return response
        except HTTPException as e:
            # Métricas para errores HTTP
            if 400 <= e.status_code < 500:
                put_metric("HTTPRequests4xx", 1, dimensions={"Endpoint": func.__name__})
            elif 500 <= e.status_code < 600:
                put_metric("HTTPRequests5xx", 1, dimensions={"Endpoint": func.__name__})
            raise
        except Exception as e:
            put_metric("HTTPRequests5xx", 1, dimensions={"Endpoint": func.__name__})
            raise
        finally:
            # Métrica de tiempo de ejecución
            execution_time = (time.time() - start_time) * 1000  # en milisegundos
            put_metric("ExecutionTime", execution_time, "Milliseconds", {"Endpoint": func.__name__})
    
    return wrapper

# ==================== MODELOS ====================

class ClienteCreate(BaseModel):
    razon_social: str = Field(..., min_length=1, max_length=200)
    nombre_comercial: str = Field(..., min_length=1, max_length=200)
    rfc: str = Field(..., min_length=12, max_length=13)
    correo_electronico: EmailStr
    telefono: str = Field(..., min_length=10, max_length=15)

class ClienteUpdate(BaseModel):
    razon_social: Optional[str] = None
    nombre_comercial: Optional[str] = None
    rfc: Optional[str] = None
    correo_electronico: Optional[EmailStr] = None
    telefono: Optional[str] = None

class Cliente(ClienteCreate):
    id: str
    created_at: str
    updated_at: str

class TipoDireccion(str, Enum):
    FACTURACION = "FACTURACION"
    ENVIO = "ENVIO"

class DomicilioCreate(BaseModel):
    cliente_id: str
    domicilio: str = Field(..., min_length=1, max_length=300)
    colonia: str = Field(..., min_length=1, max_length=100)
    municipio: str = Field(..., min_length=1, max_length=100)
    estado: str = Field(..., min_length=1, max_length=100)
    tipo_direccion: TipoDireccion

class DomicilioUpdate(BaseModel):
    domicilio: Optional[str] = None
    colonia: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None
    tipo_direccion: Optional[TipoDireccion] = None

class Domicilio(DomicilioCreate):
    id: str
    created_at: str
    updated_at: str

class ProductoCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    unidad_medida: str = Field(..., min_length=1, max_length=50)
    precio_base: float = Field(..., gt=0)

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    unidad_medida: Optional[str] = None
    precio_base: Optional[float] = None

class Producto(ProductoCreate):
    id: str
    created_at: str
    updated_at: str

# ==================== HELPERS ====================

def get_table(table_name: str):
    """Obtiene una referencia a la tabla de DynamoDB"""
    return dynamodb.Table(table_name)

def decimal_default(obj):
    """Helper para serializar Decimal a float"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def convert_decimals(item: dict) -> dict:
    """Convierte Decimals en un dict a float"""
    if item is None:
        return None
    return json.loads(json.dumps(item, default=decimal_default))

# ==================== ENDPOINTS DE CLIENTES ====================

@app.post("/clientes", response_model=Cliente, status_code=201)
@track_request_metrics
async def crear_cliente(cliente: ClienteCreate):
    """Crear un nuevo cliente"""
    table = get_table(TABLE_CLIENTES)
    
    # Verificar RFC único
    response = table.scan(
        FilterExpression="rfc = :rfc",
        ExpressionAttributeValues={":rfc": cliente.rfc}
    )
    if response.get("Items"):
        raise HTTPException(status_code=400, detail="RFC ya registrado")
    
    now = datetime.utcnow().isoformat()
    item = {
        "id": str(uuid.uuid4()),
        "razon_social": cliente.razon_social,
        "nombre_comercial": cliente.nombre_comercial,
        "rfc": cliente.rfc,
        "correo_electronico": cliente.correo_electronico,
        "telefono": cliente.telefono,
        "created_at": now,
        "updated_at": now
    }
    
    table.put_item(Item=item)
    put_metric("ClientesCreados", 1)
    return item

@app.get("/clientes", response_model=List[Cliente])
@track_request_metrics
async def listar_clientes():
    """Listar todos los clientes"""
    table = get_table(TABLE_CLIENTES)
    response = table.scan()
    return [convert_decimals(item) for item in response.get("Items", [])]

@app.get("/clientes/{cliente_id}", response_model=Cliente)
@track_request_metrics
async def obtener_cliente(cliente_id: str):
    """Obtener un cliente por ID"""
    table = get_table(TABLE_CLIENTES)
    response = table.get_item(Key={"id": cliente_id})
    item = response.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return convert_decimals(item)

@app.put("/clientes/{cliente_id}", response_model=Cliente)
@track_request_metrics
async def actualizar_cliente(cliente_id: str, cliente: ClienteUpdate):
    """Actualizar un cliente existente"""
    table = get_table(TABLE_CLIENTES)
    
    # Verificar que existe
    existing = table.get_item(Key={"id": cliente_id})
    if not existing.get("Item"):
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Construir expresión de actualización
    update_expression = "SET updated_at = :updated_at"
    expression_values = {":updated_at": datetime.utcnow().isoformat()}
    
    update_data = cliente.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            update_expression += f", {key} = :{key}"
            expression_values[f":{key}"] = value
    
    response = table.update_item(
        Key={"id": cliente_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_values,
        ReturnValues="ALL_NEW"
    )
    
    return convert_decimals(response["Attributes"])

@app.delete("/clientes/{cliente_id}", status_code=204)
@track_request_metrics
async def eliminar_cliente(cliente_id: str):
    """Eliminar un cliente"""
    table = get_table(TABLE_CLIENTES)
    
    # Verificar que existe
    existing = table.get_item(Key={"id": cliente_id})
    if not existing.get("Item"):
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Eliminar domicilios asociados
    table_domicilios = get_table(TABLE_DOMICILIOS)
    domicilios = table_domicilios.scan(
        FilterExpression="cliente_id = :cliente_id",
        ExpressionAttributeValues={":cliente_id": cliente_id}
    )
    for domicilio in domicilios.get("Items", []):
        table_domicilios.delete_item(Key={"id": domicilio["id"]})
    
    table.delete_item(Key={"id": cliente_id})
    put_metric("ClientesEliminados", 1)
    return None

# ==================== ENDPOINTS DE DOMICILIOS ====================

@app.post("/domicilios", response_model=Domicilio, status_code=201)
@track_request_metrics
async def crear_domicilio(domicilio: DomicilioCreate):
    """Crear un nuevo domicilio para un cliente"""
    # Verificar que el cliente existe
    table_clientes = get_table(TABLE_CLIENTES)
    cliente = table_clientes.get_item(Key={"id": domicilio.cliente_id})
    if not cliente.get("Item"):
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    table = get_table(TABLE_DOMICILIOS)
    now = datetime.utcnow().isoformat()
    
    item = {
        "id": str(uuid.uuid4()),
        "cliente_id": domicilio.cliente_id,
        "domicilio": domicilio.domicilio,
        "colonia": domicilio.colonia,
        "municipio": domicilio.municipio,
        "estado": domicilio.estado,
        "tipo_direccion": domicilio.tipo_direccion.value,
        "created_at": now,
        "updated_at": now
    }
    
    table.put_item(Item=item)
    put_metric("DomiciliosCreados", 1)
    return item

@app.get("/domicilios/cliente/{cliente_id}", response_model=List[Domicilio])
@track_request_metrics
async def listar_domicilios_cliente(cliente_id: str):
    """Listar todos los domicilios de un cliente"""
    table = get_table(TABLE_DOMICILIOS)
    response = table.scan(
        FilterExpression="cliente_id = :cliente_id",
        ExpressionAttributeValues={":cliente_id": cliente_id}
    )
    return [convert_decimals(item) for item in response.get("Items", [])]

@app.get("/domicilios/{domicilio_id}", response_model=Domicilio)
@track_request_metrics
async def obtener_domicilio(domicilio_id: str):
    """Obtener un domicilio por ID"""
    table = get_table(TABLE_DOMICILIOS)
    response = table.get_item(Key={"id": domicilio_id})
    item = response.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Domicilio no encontrado")
    return convert_decimals(item)

@app.put("/domicilios/{domicilio_id}", response_model=Domicilio)
@track_request_metrics
async def actualizar_domicilio(domicilio_id: str, domicilio: DomicilioUpdate):
    """Actualizar un domicilio existente"""
    table = get_table(TABLE_DOMICILIOS)
    
    existing = table.get_item(Key={"id": domicilio_id})
    if not existing.get("Item"):
        raise HTTPException(status_code=404, detail="Domicilio no encontrado")
    
    update_expression = "SET updated_at = :updated_at"
    expression_values = {":updated_at": datetime.utcnow().isoformat()}
    
    update_data = domicilio.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            if key == "tipo_direccion":
                value = value.value
            update_expression += f", {key} = :{key}"
            expression_values[f":{key}"] = value
    
    response = table.update_item(
        Key={"id": domicilio_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_values,
        ReturnValues="ALL_NEW"
    )
    
    return convert_decimals(response["Attributes"])

@app.delete("/domicilios/{domicilio_id}", status_code=204)
@track_request_metrics
async def eliminar_domicilio(domicilio_id: str):
    """Eliminar un domicilio"""
    table = get_table(TABLE_DOMICILIOS)
    
    existing = table.get_item(Key={"id": domicilio_id})
    if not existing.get("Item"):
        raise HTTPException(status_code=404, detail="Domicilio no encontrado")
    
    table.delete_item(Key={"id": domicilio_id})
    put_metric("DomiciliosEliminados", 1)
    return None

# ==================== ENDPOINTS DE PRODUCTOS ====================

@app.post("/productos", response_model=Producto, status_code=201)
@track_request_metrics
async def crear_producto(producto: ProductoCreate):
    """Crear un nuevo producto"""
    table = get_table(TABLE_PRODUCTOS)
    now = datetime.utcnow().isoformat()
    
    item = {
        "id": str(uuid.uuid4()),
        "nombre": producto.nombre,
        "unidad_medida": producto.unidad_medida,
        "precio_base": Decimal(str(producto.precio_base)),
        "created_at": now,
        "updated_at": now
    }
    
    table.put_item(Item=item)
    put_metric("ProductosCreados", 1)
    return convert_decimals(item)

@app.get("/productos", response_model=List[Producto])
@track_request_metrics
async def listar_productos():
    """Listar todos los productos"""
    table = get_table(TABLE_PRODUCTOS)
    response = table.scan()
    return [convert_decimals(item) for item in response.get("Items", [])]

@app.get("/productos/{producto_id}", response_model=Producto)
@track_request_metrics
async def obtener_producto(producto_id: str):
    """Obtener un producto por ID"""
    table = get_table(TABLE_PRODUCTOS)
    response = table.get_item(Key={"id": producto_id})
    item = response.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return convert_decimals(item)

@app.put("/productos/{producto_id}", response_model=Producto)
@track_request_metrics
async def actualizar_producto(producto_id: str, producto: ProductoUpdate):
    """Actualizar un producto existente"""
    table = get_table(TABLE_PRODUCTOS)
    
    existing = table.get_item(Key={"id": producto_id})
    if not existing.get("Item"):
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    update_expression = "SET updated_at = :updated_at"
    expression_values = {":updated_at": datetime.utcnow().isoformat()}
    
    update_data = producto.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            if key == "precio_base":
                value = Decimal(str(value))
            update_expression += f", {key} = :{key}"
            expression_values[f":{key}"] = value
    
    response = table.update_item(
        Key={"id": producto_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_values,
        ReturnValues="ALL_NEW"
    )
    
    return convert_decimals(response["Attributes"])

@app.delete("/productos/{producto_id}", status_code=204)
@track_request_metrics
async def eliminar_producto(producto_id: str):
    """Eliminar un producto"""
    table = get_table(TABLE_PRODUCTOS)
    
    existing = table.get_item(Key={"id": producto_id})
    if not existing.get("Item"):
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    table.delete_item(Key={"id": producto_id})
    put_metric("ProductosEliminados", 1)
    return None

# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Endpoint de salud"""
    return {
        "status": "healthy",
        "service": "catalogos",
        "environment": ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }

# Handler para Lambda
handler = Mangum(app, lifespan="off")
