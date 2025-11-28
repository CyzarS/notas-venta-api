"""
Tests para el módulo de notificaciones
"""
import pytest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Agregar el path del src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock de boto3 antes de importar
with patch('boto3.client'):
    from app import (
        handler,
        generar_html_correo,
        generar_texto_correo,
        procesar_mensaje_nota_venta
    )


class TestGeneracionCorreo:
    """Tests para generación de contenido de correo"""
    
    def test_generar_html_correo_contiene_elementos(self):
        html = generar_html_correo(
            cliente_nombre="Test Cliente",
            folio="NV-123",
            total=1500.50,
            download_url="https://example.com/download"
        )
        
        assert "Test Cliente" in html
        assert "NV-123" in html
        assert "$1,500.50" in html
        assert "https://example.com/download" in html
        assert "Descargar Nota de Venta" in html
    
    def test_generar_texto_correo_contiene_elementos(self):
        texto = generar_texto_correo(
            cliente_nombre="Test Cliente",
            folio="NV-456",
            total=2000.00,
            download_url="https://example.com/download"
        )
        
        assert "Test Cliente" in texto
        assert "NV-456" in texto
        assert "$2,000.00" in texto
        assert "https://example.com/download" in texto


class TestHandler:
    """Tests para el handler de Lambda"""
    
    @patch('app.enviar_correo_ses')
    def test_handler_evento_sns(self, mock_enviar):
        mock_enviar.return_value = {
            "success": True,
            "message_id": "test-id",
            "destinatario": "test@test.com"
        }
        
        evento = {
            "Records": [
                {
                    "EventSource": "aws:sns",
                    "Sns": {
                        "Message": json.dumps({
                            "type": "NOTA_VENTA_GENERADA",
                            "cliente_email": "test@test.com",
                            "cliente_nombre": "Test",
                            "folio": "NV-123",
                            "total": 100.0,
                            "download_url": "https://example.com/download",
                            "rfc": "TEST123456ABC"
                        })
                    }
                }
            ]
        }
        
        response = handler(evento, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["processed"] == 1
    
    @patch('app.enviar_correo_ses')
    def test_handler_invocacion_directa(self, mock_enviar):
        mock_enviar.return_value = {
            "success": True,
            "message_id": "test-id",
            "destinatario": "test@test.com"
        }
        
        evento = {
            "type": "NOTA_VENTA_GENERADA",
            "cliente_email": "test@test.com",
            "cliente_nombre": "Test",
            "folio": "NV-123",
            "total": 100.0,
            "download_url": "https://example.com/download",
            "rfc": "TEST123456ABC"
        }
        
        response = handler(evento, None)
        
        assert response["statusCode"] == 200


class TestProcesarMensaje:
    """Tests para procesamiento de mensajes"""
    
    def test_mensaje_incompleto_lanza_error(self):
        mensaje = {
            "type": "NOTA_VENTA_GENERADA",
            "cliente_email": "test@test.com"
            # Falta folio y download_url
        }
        
        with pytest.raises(ValueError):
            procesar_mensaje_nota_venta(mensaje)
