"""
Tests para el módulo de catálogos
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
    from app import app

client = TestClient(app)


class TestHealthCheck:
    """Tests para el endpoint de health check"""
    
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "catalogos"


class TestClientes:
    """Tests para endpoints de clientes"""
    
    @patch('app.get_table')
    def test_crear_cliente_exitoso(self, mock_get_table):
        mock_table = MagicMock()
        mock_table.scan.return_value = {"Items": []}
        mock_get_table.return_value = mock_table
        
        cliente_data = {
            "razon_social": "Empresa Test SA de CV",
            "nombre_comercial": "Test Corp",
            "rfc": "TEST123456ABC",
            "correo_electronico": "test@empresa.com",
            "telefono": "5551234567"
        }
        
        response = client.post("/clientes", json=cliente_data)
        assert response.status_code == 201
        data = response.json()
        assert data["razon_social"] == cliente_data["razon_social"]
        assert "id" in data
    
    @patch('app.get_table')
    def test_crear_cliente_rfc_duplicado(self, mock_get_table):
        mock_table = MagicMock()
        mock_table.scan.return_value = {"Items": [{"id": "existing"}]}
        mock_get_table.return_value = mock_table
        
        cliente_data = {
            "razon_social": "Empresa Test SA de CV",
            "nombre_comercial": "Test Corp",
            "rfc": "TEST123456ABC",
            "correo_electronico": "test@empresa.com",
            "telefono": "5551234567"
        }
        
        response = client.post("/clientes", json=cliente_data)
        assert response.status_code == 400
    
    @patch('app.get_table')
    def test_listar_clientes(self, mock_get_table):
        mock_table = MagicMock()
        mock_table.scan.return_value = {"Items": []}
        mock_get_table.return_value = mock_table
        
        response = client.get("/clientes")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    @patch('app.get_table')
    def test_obtener_cliente_no_encontrado(self, mock_get_table):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_get_table.return_value = mock_table
        
        response = client.get("/clientes/id-no-existe")
        assert response.status_code == 404


class TestDomicilios:
    """Tests para endpoints de domicilios"""
    
    @patch('app.get_table')
    def test_crear_domicilio_cliente_no_existe(self, mock_get_table):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_get_table.return_value = mock_table
        
        domicilio_data = {
            "cliente_id": "cliente-no-existe",
            "domicilio": "Calle Test 123",
            "colonia": "Centro",
            "municipio": "Guadalajara",
            "estado": "Jalisco",
            "tipo_direccion": "FACTURACION"
        }
        
        response = client.post("/domicilios", json=domicilio_data)
        assert response.status_code == 404


class TestProductos:
    """Tests para endpoints de productos"""
    
    @patch('app.get_table')
    def test_crear_producto_exitoso(self, mock_get_table):
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        
        producto_data = {
            "nombre": "Producto Test",
            "unidad_medida": "PZA",
            "precio_base": 100.50
        }
        
        response = client.post("/productos", json=producto_data)
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == producto_data["nombre"]
    
    @patch('app.get_table')
    def test_listar_productos(self, mock_get_table):
        mock_table = MagicMock()
        mock_table.scan.return_value = {"Items": []}
        mock_get_table.return_value = mock_table
        
        response = client.get("/productos")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_crear_producto_precio_invalido(self):
        producto_data = {
            "nombre": "Producto Test",
            "unidad_medida": "PZA",
            "precio_base": -10  # Precio negativo inválido
        }
        
        response = client.post("/productos", json=producto_data)
        assert response.status_code == 422  # Validation error
