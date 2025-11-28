"""
Módulo de Notificaciones - Procesamiento de eventos SNS y envío de correos con SES
Implementa métricas de CloudWatch para monitoreo
"""
import os
import json
import time
import boto3
from datetime import datetime
from functools import wraps

# Configuración de ambiente
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SES_SOURCE_EMAIL = os.getenv("SES_SOURCE_EMAIL", "noreply@example.com")
SES_CONFIGURATION_SET = os.getenv("SES_CONFIGURATION_SET", "")

# Inicializar clientes AWS
ses_client = boto3.client('ses', region_name=AWS_REGION)
cloudwatch = boto3.client('cloudwatch', region_name=AWS_REGION)

# ==================== MÉTRICAS ====================

def put_metric(metric_name: str, value: float, unit: str = "Count", dimensions: dict = None):
    """Envía una métrica a CloudWatch"""
    try:
        metric_dimensions = [
            {"Name": "Environment", "Value": ENVIRONMENT},
            {"Name": "Service", "Value": "notificaciones"}
        ]
        if dimensions:
            for key, val in dimensions.items():
                metric_dimensions.append({"Name": key, "Value": str(val)})
        
        cloudwatch.put_metric_data(
            Namespace="NotasVenta/Notificaciones",
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

def track_execution_time(func):
    """Decorador para trackear tiempo de ejecución"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            put_metric("ProcessingSuccess", 1, dimensions={"Function": func.__name__})
            return result
        except Exception as e:
            put_metric("ProcessingError", 1, dimensions={"Function": func.__name__})
            raise
        finally:
            execution_time = (time.time() - start_time) * 1000
            put_metric("ExecutionTime", execution_time, "Milliseconds", {"Function": func.__name__})
    
    return wrapper

# ==================== PLANTILLAS DE CORREO ====================

def generar_html_correo(cliente_nombre: str, folio: str, total: float, download_url: str) -> str:
    """Genera el HTML del correo de notificación"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #2c3e50;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px;
                border: 1px solid #ddd;
            }}
            .info-box {{
                background-color: #fff;
                padding: 15px;
                border-left: 4px solid #3498db;
                margin: 20px 0;
            }}
            .button {{
                display: inline-block;
                background-color: #27ae60;
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .button:hover {{
                background-color: #219a52;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 12px;
            }}
            .total {{
                font-size: 24px;
                color: #27ae60;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📄 Nota de Venta Generada</h1>
        </div>
        <div class="content">
            <p>Estimado/a <strong>{cliente_nombre}</strong>,</p>
            
            <p>Le informamos que se ha generado una nueva nota de venta a su nombre.</p>
            
            <div class="info-box">
                <p><strong>Folio:</strong> {folio}</p>
                <p><strong>Total:</strong> <span class="total">${total:,.2f} MXN</span></p>
                <p><strong>Fecha:</strong> {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')} UTC</p>
            </div>
            
            <p>Puede descargar su nota de venta en formato PDF haciendo clic en el siguiente enlace:</p>
            
            <center>
                <a href="{download_url}" class="button">📥 Descargar Nota de Venta</a>
            </center>
            
            <p><small>Si el botón no funciona, copie y pegue el siguiente enlace en su navegador:</small></p>
            <p><small><a href="{download_url}">{download_url}</a></small></p>
        </div>
        <div class="footer">
            <p>Este es un correo automático, por favor no responda a este mensaje.</p>
            <p>© {datetime.utcnow().year} Sistema de Notas de Venta</p>
        </div>
    </body>
    </html>
    """

def generar_texto_correo(cliente_nombre: str, folio: str, total: float, download_url: str) -> str:
    """Genera el texto plano del correo de notificación"""
    return f"""
    NOTA DE VENTA GENERADA
    ======================
    
    Estimado/a {cliente_nombre},
    
    Le informamos que se ha generado una nueva nota de venta a su nombre.
    
    Detalles:
    - Folio: {folio}
    - Total: ${total:,.2f} MXN
    - Fecha: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')} UTC
    
    Para descargar su nota de venta en formato PDF, visite:
    {download_url}
    
    Este es un correo automático, por favor no responda a este mensaje.
    """

# ==================== ENVÍO DE CORREO ====================

@track_execution_time
def enviar_correo_ses(destinatario: str, asunto: str, html_body: str, text_body: str) -> dict:
    """Envía un correo usando Amazon SES"""
    try:
        email_params = {
            'Source': SES_SOURCE_EMAIL,
            'Destination': {
                'ToAddresses': [destinatario]
            },
            'Message': {
                'Subject': {
                    'Data': asunto,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': text_body,
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data': html_body,
                        'Charset': 'UTF-8'
                    }
                }
            }
        }
        
        # Agregar configuration set si está configurado
        if SES_CONFIGURATION_SET:
            email_params['ConfigurationSetName'] = SES_CONFIGURATION_SET
        
        response = ses_client.send_email(**email_params)
        
        put_metric("CorreosEnviados", 1)
        print(f"Correo enviado exitosamente a {destinatario}. MessageId: {response['MessageId']}")
        
        return {
            "success": True,
            "message_id": response['MessageId'],
            "destinatario": destinatario
        }
        
    except ses_client.exceptions.MessageRejected as e:
        put_metric("CorreosRechazados", 1)
        print(f"Correo rechazado: {e}")
        raise
    except ses_client.exceptions.MailFromDomainNotVerifiedException as e:
        put_metric("ErroresDominio", 1)
        print(f"Dominio no verificado: {e}")
        raise
    except Exception as e:
        put_metric("ErroresEnvio", 1)
        print(f"Error enviando correo: {e}")
        raise

# ==================== PROCESAMIENTO DE EVENTOS ====================

def procesar_mensaje_nota_venta(mensaje: dict) -> dict:
    """Procesa un mensaje de nota de venta generada"""
    
    # Extraer información del mensaje
    cliente_email = mensaje.get('cliente_email')
    cliente_nombre = mensaje.get('cliente_nombre', 'Cliente')
    folio = mensaje.get('folio')
    total = mensaje.get('total', 0)
    download_url = mensaje.get('download_url')
    rfc = mensaje.get('rfc', '')
    
    if not all([cliente_email, folio, download_url]):
        raise ValueError("Mensaje incompleto: falta cliente_email, folio o download_url")
    
    # Generar contenido del correo
    asunto = f"Nota de Venta {folio} - Descarga disponible"
    html_body = generar_html_correo(cliente_nombre, folio, total, download_url)
    text_body = generar_texto_correo(cliente_nombre, folio, total, download_url)
    
    # Enviar correo
    resultado = enviar_correo_ses(cliente_email, asunto, html_body, text_body)
    
    put_metric("NotasNotificadas", 1, dimensions={"RFC": rfc[:4] if rfc else "UNKNOWN"})
    
    return resultado

# ==================== HANDLER DE LAMBDA ====================

def handler(event, context):
    """
    Handler principal para procesar eventos de SNS
    
    El evento puede venir de:
    1. SNS directamente (invocación asíncrona)
    2. API Gateway (para testing)
    """
    start_time = time.time()
    print(f"Evento recibido: {json.dumps(event)}")
    
    try:
        results = []
        
        # Procesar registros de SNS
        if 'Records' in event:
            for record in event['Records']:
                if record.get('EventSource') == 'aws:sns' or record.get('eventSource') == 'aws:sns':
                    # Mensaje de SNS
                    sns_message = record.get('Sns', {}).get('Message', '{}')
                    mensaje = json.loads(sns_message)
                    
                    if mensaje.get('type') == 'NOTA_VENTA_GENERADA':
                        resultado = procesar_mensaje_nota_venta(mensaje)
                        results.append(resultado)
                    else:
                        print(f"Tipo de mensaje no soportado: {mensaje.get('type')}")
                        
        # Procesar invocación directa (para testing)
        elif 'body' in event:
            body = event.get('body', '{}')
            if isinstance(body, str):
                mensaje = json.loads(body)
            else:
                mensaje = body
                
            if mensaje.get('type') == 'NOTA_VENTA_GENERADA':
                resultado = procesar_mensaje_nota_venta(mensaje)
                results.append(resultado)
        
        # Invocación directa sin body
        elif event.get('type') == 'NOTA_VENTA_GENERADA':
            resultado = procesar_mensaje_nota_venta(event)
            results.append(resultado)
        
        execution_time = (time.time() - start_time) * 1000
        put_metric("TotalExecutionTime", execution_time, "Milliseconds")
        put_metric("MensajesProcesados", len(results))
        
        response = {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Notificaciones procesadas exitosamente",
                "processed": len(results),
                "results": results
            })
        }
        
        print(f"Procesamiento completado: {len(results)} notificaciones enviadas")
        return response
        
    except Exception as e:
        put_metric("ErroresProcesamiento", 1)
        print(f"Error procesando evento: {e}")
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "message": "Error procesando notificaciones"
            })
        }

# ==================== HEALTH CHECK (para API Gateway) ====================

def health_handler(event, context):
    """Handler para health check vía API Gateway"""
    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "healthy",
            "service": "notificaciones",
            "environment": ENVIRONMENT,
            "timestamp": datetime.utcnow().isoformat()
        })
    }
