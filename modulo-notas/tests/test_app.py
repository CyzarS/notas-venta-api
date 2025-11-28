"""
Tests para el módulo de notas de venta
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

# Agregar el path del src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock de boto3 antes de importar la app
with patch('boto3.resource'), patch('boto3.client'):
    from app import app, generar_folio

client = TestClient(app)


class TestHealthCheck:
    """Tests para el endpoint de health check"""
    
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "notas-venta"


class TestFolio:
    """Tests para generación de folios"""
    
    def test_generar_folio_formato(self):
        folio = generar_folio()
        assert folio.startswith("NV-")
        parts = folio.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 14  # Timestamp
        assert len(parts[2]) == 4   # Random suffix


class TestNotasVenta:
    """Tests para endpoints de notas de venta"""
    
    @patch('app.obtener_cliente')
    @patch('app.obtener_domicilio')
    @patch('app.obtener_producto')
    @patch('app.get_table')
    @patch('app.subir_pdf_a_s3')
    @patch('app.publicar_notificacion_sns')
    def test_crear_nota_exitoso(
        self, 
        mock_sns, 
        mock_s3, 
        mock_get_table, 
        mock_producto, 
        mock_domicilio, 
        mock_cliente
    ):
        mock_cliente.return_value = {
            "id": "cliente-1",
            "razon_social": "Test SA",
            "nombre_comercial": "Test",
            "rfc": "TEST123456ABC",
            "correo_electronico": "test@test.com",
            "telefono": "5551234567"
        }
        mock_domicilio.return_value = {
            "id": "dom-1",
            "domicilio": "Calle Test 123",
            "colonia": "Centro",
            "municipio": "Guadalajara",
            "estado": "Jalisco",
            "tipo_direccion": "FACTURACION"
        }
        mock_producto.return_value = {
            "id": "prod-1",
            "nombre": "Producto Test",
            "unidad_medida": "PZA",
            "precio_base": 100.0
        }
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        mock_s3.return_value = "TEST123456ABC/NV-123.pdf"
        
        nota_data = {
            "cliente_id": "cliente-1",
            "direccion_facturacion_id": "dom-1",
            "direccion_envio_id": "dom-1",
            "contenido": [
                {
                    "producto_id": "prod-1",
                    "cantidad": 2,
                    "precio_unitario": 100.0
                }
            ]
        }
        
        response = client.post("/notas", json=nota_data)
        assert response.status_code == 201
        data = response.json()
        assert "folio" in data
        assert data["total"] == 200.0
    
    @patch('app.obtener_cliente')
    def test_crear_nota_cliente_no_existe(self, mock_cliente):
        mock_cliente.return_value = None
        
        nota_data = {
            "cliente_id": "cliente-no-existe",
            "direccion_facturacion_id": "dom-1",
            "direccion_envio_id": "dom-1",
            "contenido": [
                {
                    "producto_id": "prod-1",
                    "cantidad": 2,
                    "precio_unitario": 100.0
                }
            ]
        }
        
        response = client.post("/notas", json=nota_data)
        assert response.status_code == 404


class TestDescargarPDF:
    """Tests para descarga de PDF"""
    
    @patch('app.get_table')
    def test_descargar_pdf_nota_no_existe(self, mock_get_table):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_get_table.return_value = mock_table
        
        response = client.get("/notas/nota-no-existe/pdf")
        assert response.status_code == 404
