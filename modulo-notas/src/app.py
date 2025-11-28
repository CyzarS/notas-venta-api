"""
Módulo de Notas de Venta - Creación y gestión de notas con generación de PDF
Implementa métricas de CloudWatch para monitoreo
"""
import os
import json
import time
import uuid
import boto3
from io import BytesIO
from decimal import Decimal
from datetime import datetime
from functools import wraps
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from mangum import Mangum
from pydantic import BaseModel, Field
from typing import List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

# Configuración de ambiente
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
EXPEDIENTE = os.getenv("EXPEDIENTE", "A01234567")
S3_BUCKET = os.getenv("S3_BUCKET", f"{EXPEDIENTE}-esi3898k-examen1")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8002")

TABLE_NOTAS = os.getenv("TABLE_NOTAS", "notas_venta")
TABLE_CONTENIDO_NOTAS = os.getenv("TABLE_CONTENIDO_NOTAS", "contenido_notas")
TABLE_CLIENTES = os.getenv("TABLE_CLIENTES", "clientes")
TABLE_DOMICILIOS = os.getenv("TABLE_DOMICILIOS", "domicilios")
TABLE_PRODUCTOS = os.getenv("TABLE_PRODUCTOS", "productos")

# Inicializar clientes AWS
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
s3_client = boto3.client('s3', region_name=AWS_REGION)
sns_client = boto3.client('sns', region_name=AWS_REGION)
cloudwatch = boto3.client('cloudwatch', region_name=AWS_REGION)

app = FastAPI(
    title="API Notas de Venta",
    description="Creación y gestión de notas de venta con generación de PDF",
    version="1.0.0"
)

# ==================== MÉTRICAS ====================

def put_metric(metric_name: str, value: float, unit: str = "Count", dimensions: dict = None):
    """Envía una métrica a CloudWatch"""
    try:
        metric_dimensions = [
            {"Name": "Environment", "Value": ENVIRONMENT},
            {"Name": "Service", "Value": "notas-venta"}
        ]
        if dimensions:
            for key, val in dimensions.items():
                metric_dimensions.append({"Name": key, "Value": str(val)})
        
        cloudwatch.put_metric_data(
            Namespace="NotasVenta/Notas",
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
            
            if 200 <= status_code < 300:
                put_metric("HTTPRequests2xx", 1, dimensions={"Endpoint": func.__name__})
            elif 400 <= status_code < 500:
                put_metric("HTTPRequests4xx", 1, dimensions={"Endpoint": func.__name__})
            elif 500 <= status_code < 600:
                put_metric("HTTPRequests5xx", 1, dimensions={"Endpoint": func.__name__})
            
            return response
        except HTTPException as e:
            if 400 <= e.status_code < 500:
                put_metric("HTTPRequests4xx", 1, dimensions={"Endpoint": func.__name__})
            elif 500 <= e.status_code < 600:
                put_metric("HTTPRequests5xx", 1, dimensions={"Endpoint": func.__name__})
            raise
        except Exception as e:
            put_metric("HTTPRequests5xx", 1, dimensions={"Endpoint": func.__name__})
            raise
        finally:
            execution_time = (time.time() - start_time) * 1000
            put_metric("ExecutionTime", execution_time, "Milliseconds", {"Endpoint": func.__name__})
    
    return wrapper

# ==================== MODELOS ====================

class ContenidoNotaCreate(BaseModel):
    producto_id: str
    cantidad: int = Field(..., gt=0)
    precio_unitario: float = Field(..., gt=0)

class ContenidoNota(BaseModel):
    id: str
    nota_id: str
    producto_id: str
    producto_nombre: Optional[str] = None
    cantidad: int
    precio_unitario: float
    importe: float

class NotaVentaCreate(BaseModel):
    cliente_id: str
    direccion_facturacion_id: str
    direccion_envio_id: str
    contenido: List[ContenidoNotaCreate]

class NotaVenta(BaseModel):
    id: str
    folio: str
    cliente_id: str
    cliente_info: Optional[dict] = None
    direccion_facturacion_id: str
    direccion_facturacion_info: Optional[dict] = None
    direccion_envio_id: str
    direccion_envio_info: Optional[dict] = None
    total: float
    contenido: Optional[List[ContenidoNota]] = None
    pdf_url: Optional[str] = None
    created_at: str

# ==================== HELPERS ====================

def get_table(table_name: str):
    """Obtiene una referencia a la tabla de DynamoDB"""
    return dynamodb.Table(table_name)

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def convert_decimals(item: dict) -> dict:
    if item is None:
        return None
    return json.loads(json.dumps(item, default=decimal_default))

def generar_folio() -> str:
    """Genera un folio único para la nota"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_suffix = str(uuid.uuid4())[:4].upper()
    return f"NV-{timestamp}-{random_suffix}"

def obtener_cliente(cliente_id: str) -> dict:
    """Obtiene información del cliente"""
    table = get_table(TABLE_CLIENTES)
    response = table.get_item(Key={"id": cliente_id})
    return convert_decimals(response.get("Item"))

def obtener_domicilio(domicilio_id: str) -> dict:
    """Obtiene información del domicilio"""
    table = get_table(TABLE_DOMICILIOS)
    response = table.get_item(Key={"id": domicilio_id})
    return convert_decimals(response.get("Item"))

def obtener_producto(producto_id: str) -> dict:
    """Obtiene información del producto"""
    table = get_table(TABLE_PRODUCTOS)
    response = table.get_item(Key={"id": producto_id})
    return convert_decimals(response.get("Item"))

# ==================== GENERACIÓN DE PDF ====================

def generar_pdf_nota(nota: dict, cliente: dict, contenido: list) -> bytes:
    """Genera un PDF con la información de la nota de venta"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para el título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        alignment=1  # Centrado
    )
    
    # Título
    elements.append(Paragraph("NOTA DE VENTA", title_style))
    elements.append(Spacer(1, 20))
    
    # Información de la nota
    elements.append(Paragraph(f"<b>Folio:</b> {nota['folio']}", styles['Normal']))
    elements.append(Paragraph(f"<b>Fecha:</b> {nota['created_at']}", styles['Normal']))
    elements.append(Spacer(1, 15))
    
    # Información del cliente
    elements.append(Paragraph("<b>DATOS DEL CLIENTE</b>", styles['Heading2']))
    elements.append(Paragraph(f"<b>Razón Social:</b> {cliente.get('razon_social', 'N/A')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Nombre Comercial:</b> {cliente.get('nombre_comercial', 'N/A')}", styles['Normal']))
    elements.append(Paragraph(f"<b>RFC:</b> {cliente.get('rfc', 'N/A')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Correo:</b> {cliente.get('correo_electronico', 'N/A')}", styles['Normal']))
    elements.append(Paragraph(f"<b>Teléfono:</b> {cliente.get('telefono', 'N/A')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Tabla de contenido
    elements.append(Paragraph("<b>DETALLE DE LA NOTA</b>", styles['Heading2']))
    elements.append(Spacer(1, 10))
    
    # Encabezados de la tabla
    table_data = [['Cantidad', 'Producto', 'Precio Unitario', 'Importe']]
    
    # Agregar contenido
    for item in contenido:
        table_data.append([
            str(item['cantidad']),
            item.get('producto_nombre', 'Producto'),
            f"${item['precio_unitario']:,.2f}",
            f"${item['importe']:,.2f}"
        ])
    
    # Agregar fila de total
    table_data.append(['', '', 'TOTAL:', f"${nota['total']:,.2f}"])
    
    # Crear tabla
    table = Table(table_data, colWidths=[1*inch, 3*inch, 1.5*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (2, -1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
    ]))
    
    elements.append(table)
    
    # Construir el PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

def subir_pdf_a_s3(pdf_bytes: bytes, rfc_cliente: str, folio: str) -> str:
    """Sube el PDF a S3 con los metadatos requeridos"""
    object_key = f"{rfc_cliente}/{folio}.pdf"
    
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=object_key,
        Body=pdf_bytes,
        ContentType='application/pdf',
        Metadata={
            'hora-envio': datetime.utcnow().isoformat(),
            'nota-descargada': 'false',
            'veces-enviado': '1'
        }
    )
    
    put_metric("PDFGenerados", 1)
    return object_key

def actualizar_metadatos_s3(rfc_cliente: str, folio: str, descargada: bool = False):
    """Actualiza los metadatos del PDF en S3"""
    object_key = f"{rfc_cliente}/{folio}.pdf"
    
    # Obtener metadatos actuales
    try:
        response = s3_client.head_object(Bucket=S3_BUCKET, Key=object_key)
        metadata = response.get('Metadata', {})
        
        if descargada:
            metadata['nota-descargada'] = 'true'
        else:
            # Incrementar veces enviado
            veces_enviado = int(metadata.get('veces-enviado', '1'))
            metadata['veces-enviado'] = str(veces_enviado + 1)
            metadata['hora-envio'] = datetime.utcnow().isoformat()
        
        # Copiar objeto con nuevos metadatos
        s3_client.copy_object(
            Bucket=S3_BUCKET,
            CopySource={'Bucket': S3_BUCKET, 'Key': object_key},
            Key=object_key,
            Metadata=metadata,
            MetadataDirective='REPLACE',
            ContentType='application/pdf'
        )
    except Exception as e:
        print(f"Error actualizando metadatos: {e}")
        raise

def publicar_notificacion_sns(cliente: dict, nota: dict, download_url: str):
    """Publica notificación a SNS para envío de correo"""
    if not SNS_TOPIC_ARN:
        print("SNS_TOPIC_ARN no configurado, saltando notificación")
        return
    
    message = {
        "type": "NOTA_VENTA_GENERADA",
        "cliente_email": cliente.get('correo_electronico'),
        "cliente_nombre": cliente.get('nombre_comercial'),
        "folio": nota['folio'],
        "rfc": cliente.get('rfc'),
        "total": nota['total'],
        "download_url": download_url,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    sns_client.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=json.dumps(message),
        Subject=f"Nueva Nota de Venta - {nota['folio']}"
    )
    
    put_metric("NotificacionesEnviadas", 1)

# ==================== ENDPOINTS ====================

@app.post("/notas", response_model=NotaVenta, status_code=201)
@track_request_metrics
async def crear_nota_venta(nota_data: NotaVentaCreate):
    """Crear una nueva nota de venta con generación de PDF y notificación"""
    start_time = time.time()
    
    # Validar cliente
    cliente = obtener_cliente(nota_data.cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Validar direcciones
    dir_facturacion = obtener_domicilio(nota_data.direccion_facturacion_id)
    if not dir_facturacion:
        raise HTTPException(status_code=404, detail="Dirección de facturación no encontrada")
    
    dir_envio = obtener_domicilio(nota_data.direccion_envio_id)
    if not dir_envio:
        raise HTTPException(status_code=404, detail="Dirección de envío no encontrada")
    
    # Validar productos y calcular totales
    contenido_procesado = []
    total = 0
    
    for item in nota_data.contenido:
        producto = obtener_producto(item.producto_id)
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {item.producto_id} no encontrado")
        
        importe = item.cantidad * item.precio_unitario
        total += importe
        
        contenido_procesado.append({
            "id": str(uuid.uuid4()),
            "producto_id": item.producto_id,
            "producto_nombre": producto.get('nombre'),
            "cantidad": item.cantidad,
            "precio_unitario": item.precio_unitario,
            "importe": importe
        })
    
    # Crear nota
    now = datetime.utcnow().isoformat()
    folio = generar_folio()
    nota_id = str(uuid.uuid4())
    
    nota = {
        "id": nota_id,
        "folio": folio,
        "cliente_id": nota_data.cliente_id,
        "direccion_facturacion_id": nota_data.direccion_facturacion_id,
        "direccion_envio_id": nota_data.direccion_envio_id,
        "total": Decimal(str(total)),
        "created_at": now
    }
    
    # Guardar nota en DynamoDB
    table_notas = get_table(TABLE_NOTAS)
    table_notas.put_item(Item=nota)
    
    # Guardar contenido
    table_contenido = get_table(TABLE_CONTENIDO_NOTAS)
    for item in contenido_procesado:
        item["nota_id"] = nota_id
        item["precio_unitario"] = Decimal(str(item["precio_unitario"]))
        item["importe"] = Decimal(str(item["importe"]))
        table_contenido.put_item(Item=item)
    
    # Generar PDF
    nota_dict = convert_decimals(nota)
    pdf_bytes = generar_pdf_nota(nota_dict, cliente, contenido_procesado)
    
    # Subir PDF a S3
    object_key = subir_pdf_a_s3(pdf_bytes, cliente['rfc'], folio)
    
    # URL de descarga
    download_url = f"{API_BASE_URL}/notas/{nota_id}/pdf"
    
    # Publicar notificación SNS
    publicar_notificacion_sns(cliente, nota_dict, download_url)
    
    # Métrica de tiempo de generación de nota completa
    generation_time = (time.time() - start_time) * 1000
    put_metric("TiempoGeneracionNota", generation_time, "Milliseconds")
    put_metric("NotasCreadas", 1)
    
    # Preparar respuesta
    response_nota = convert_decimals(nota)
    response_nota["cliente_info"] = cliente
    response_nota["direccion_facturacion_info"] = dir_facturacion
    response_nota["direccion_envio_info"] = dir_envio
    response_nota["contenido"] = [convert_decimals(c) for c in contenido_procesado]
    response_nota["pdf_url"] = download_url
    
    return response_nota

@app.get("/notas/{nota_id}", response_model=NotaVenta)
@track_request_metrics
async def obtener_nota_venta(nota_id: str):
    """Obtener una nota de venta por ID"""
    table_notas = get_table(TABLE_NOTAS)
    response = table_notas.get_item(Key={"id": nota_id})
    nota = response.get("Item")
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    
    nota = convert_decimals(nota)
    
    # Obtener información relacionada
    cliente = obtener_cliente(nota['cliente_id'])
    dir_facturacion = obtener_domicilio(nota['direccion_facturacion_id'])
    dir_envio = obtener_domicilio(nota['direccion_envio_id'])
    
    # Obtener contenido
    table_contenido = get_table(TABLE_CONTENIDO_NOTAS)
    contenido_response = table_contenido.scan(
        FilterExpression="nota_id = :nota_id",
        ExpressionAttributeValues={":nota_id": nota_id}
    )
    contenido = [convert_decimals(item) for item in contenido_response.get("Items", [])]
    
    nota["cliente_info"] = cliente
    nota["direccion_facturacion_info"] = dir_facturacion
    nota["direccion_envio_info"] = dir_envio
    nota["contenido"] = contenido
    nota["pdf_url"] = f"{API_BASE_URL}/notas/{nota_id}/pdf"
    
    return nota

@app.get("/notas")
@track_request_metrics
async def listar_notas():
    """Listar todas las notas de venta"""
    table = get_table(TABLE_NOTAS)
    response = table.scan()
    return [convert_decimals(item) for item in response.get("Items", [])]

@app.get("/notas/{nota_id}/pdf")
@track_request_metrics
async def descargar_pdf_nota(nota_id: str):
    """Descargar el PDF de una nota de venta y actualizar metadato nota-descargada"""
    # Obtener nota
    table_notas = get_table(TABLE_NOTAS)
    response = table_notas.get_item(Key={"id": nota_id})
    nota = response.get("Item")
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    
    nota = convert_decimals(nota)
    
    # Obtener cliente para el RFC
    cliente = obtener_cliente(nota['cliente_id'])
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Descargar PDF de S3
    object_key = f"{cliente['rfc']}/{nota['folio']}.pdf"
    
    try:
        s3_response = s3_client.get_object(Bucket=S3_BUCKET, Key=object_key)
        pdf_content = s3_response['Body'].read()
        
        # Actualizar metadato nota-descargada a true
        actualizar_metadatos_s3(cliente['rfc'], nota['folio'], descargada=True)
        
        put_metric("PDFDescargados", 1)
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={nota['folio']}.pdf"
            }
        )
    except s3_client.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="PDF no encontrado")
    except Exception as e:
        print(f"Error descargando PDF: {e}")
        raise HTTPException(status_code=500, detail="Error al descargar PDF")

@app.post("/notas/{nota_id}/reenviar")
@track_request_metrics
async def reenviar_notificacion(nota_id: str):
    """Reenviar notificación de una nota de venta"""
    # Obtener nota
    table_notas = get_table(TABLE_NOTAS)
    response = table_notas.get_item(Key={"id": nota_id})
    nota = response.get("Item")
    
    if not nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    
    nota = convert_decimals(nota)
    
    # Obtener cliente
    cliente = obtener_cliente(nota['cliente_id'])
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Actualizar metadatos de veces enviado
    actualizar_metadatos_s3(cliente['rfc'], nota['folio'], descargada=False)
    
    # Reenviar notificación
    download_url = f"{API_BASE_URL}/notas/{nota_id}/pdf"
    publicar_notificacion_sns(cliente, nota, download_url)
    
    put_metric("NotificacionesReenviadas", 1)
    
    return {"message": "Notificación reenviada exitosamente"}

# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Endpoint de salud"""
    return {
        "status": "healthy",
        "service": "notas-venta",
        "environment": ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }

# Handler para Lambda
handler = Mangum(app, lifespan="off")
