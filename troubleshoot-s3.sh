#!/bin/bash

# 🔍 Script de Diagnóstico: Problema S3 Bucket
# Este script te ayuda a identificar y resolver el problema del bucket faltante

set -e

echo "=========================================="
echo "🔍 Diagnóstico de Bucket S3"
echo "=========================================="
echo ""

# 1. Verificar variables de entorno
echo "1️⃣ Verificando credenciales AWS..."
if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "❌ AWS_ACCESS_KEY_ID no configurado"
    echo "⚠️ Configura las credenciales de AWS Academy:"
    echo "   export AWS_ACCESS_KEY_ID=ASIA..."
    echo "   export AWS_SECRET_ACCESS_KEY=..."
    echo "   export AWS_SESSION_TOKEN=..."
    exit 1
else
    echo "✅ AWS_ACCESS_KEY_ID configurado"
fi

if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "❌ AWS_SECRET_ACCESS_KEY no configurado"
    exit 1
else
    echo "✅ AWS_SECRET_ACCESS_KEY configurado"
fi

if [ -z "$AWS_SESSION_TOKEN" ]; then
    echo "❌ AWS_SESSION_TOKEN no configurado"
    exit 1
else
    echo "✅ AWS_SESSION_TOKEN configurado"
fi

echo ""
echo "2️⃣ Listando todos los buckets S3..."
BUCKETS=$(aws s3 ls | awk '{print $3}')
echo "Buckets encontrados:"
echo "$BUCKETS" | sed 's/^/  ✓ /'

echo ""
echo "3️⃣ Buscando bucket de código lambda..."
LAMBDA_BUCKETS=$(echo "$BUCKETS" | grep "lambda-code" || true)

if [ -z "$LAMBDA_BUCKETS" ]; then
    echo "❌ No hay ningún bucket '*-lambda-code' en tu cuenta"
    echo ""
    echo "📋 Posibles soluciones:"
    echo "   A) El workflow 'Deploy Infrastructure' NO se ha ejecutado"
    echo "   B) Se ejecutó pero con error y no creó el bucket"
    echo "   C) El bucket se creó con otro nombre"
    echo ""
    echo "🚀 Solución recomendada:"
    echo "   1. Ve a GitHub → Actions → 'Deploy Infrastructure (AWS Academy)'"
    echo "   2. Click 'Run workflow'"
    echo "   3. Ingresa tu número de expediente"
    echo "   4. Espera a que termine (10-15 minutos)"
    echo ""
else
    echo "✅ Buckets encontrados:"
    echo "$LAMBDA_BUCKETS" | sed 's/^/  ✓ /'
fi

echo ""
echo "4️⃣ Buscando bucket PDF/docs (para notas)..."
PDF_BUCKETS=$(echo "$BUCKETS" | grep "esi3898k-examen1" || true)

if [ -z "$PDF_BUCKETS" ]; then
    echo "❌ No hay ningún bucket '*-esi3898k-examen1' en tu cuenta"
    echo "   Esto confirma que la infraestructura NO se ha desplegado"
else
    echo "✅ Buckets encontrados:"
    echo "$PDF_BUCKETS" | sed 's/^/  ✓ /'
    echo ""
    echo "📊 Si ves buckets aquí, significa que:"
    echo "   ✓ La infraestructura SÍ se desplegó"
    echo "   ✓ Pero el bucket de código lambda NO se creó"
    echo ""
    echo "🔧 Próxima acción:"
    echo "   Ejecuta el workflow 'Deploy Infrastructure' nuevamente"
fi

echo ""
echo "5️⃣ Verificando región de AWS..."
REGION=${AWS_DEFAULT_REGION:-"us-east-1"}
echo "Región configurada: $REGION"

echo ""
echo "6️⃣ Resumen de diagnóstico:"
echo "=========================================="

if [ -n "$LAMBDA_BUCKETS" ]; then
    echo "✅ STATUS: Bucket de código existe"
    echo ""
    echo "📝 Bucket encontrado: $LAMBDA_BUCKETS"
    echo ""
    echo "Próximos pasos:"
    echo "  1. Verifica que secrets.EXPEDIENTE en GitHub coincida"
    echo "  2. Ejecuta un push para disparar los workflows CI/CD"
else
    echo "❌ STATUS: Bucket de código NO existe"
    echo ""
    if [ -n "$PDF_BUCKETS" ]; then
        echo "⚠️ Infraestructura parcialmente desplegada"
        echo "   - Buckets de datos: SÍ"
        echo "   - Bucket de código: NO"
    else
        echo "⚠️ Infraestructura NO desplegada"
        echo "   - Nada se ha creado en AWS"
    fi
    echo ""
    echo "🚀 ACCIÓN REQUERIDA:"
    echo "  1. Ve a GitHub → Actions"
    echo "  2. Busca 'Deploy Infrastructure (AWS Academy)'"
    echo "  3. Click 'Run workflow'"
    echo "  4. Ingresa expediente (número de alumno)"
    echo "  5. Espera ~15 minutos"
    echo "  6. Vuelve a ejecutar este script"
fi

echo "=========================================="
