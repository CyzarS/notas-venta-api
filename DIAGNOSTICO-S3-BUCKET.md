# 🔍 Diagnóstico: Error NoSuchBucket en CI/CD

## ❌ El Problema

El error que viste significa que el bucket S3 **no existe**:

```
An error occurred (NoSuchBucket) when calling the CreateMultipartUpload operation: 
The specified bucket does not exist
```

El nombre del bucket que buscaba era: `744165-lambda-code`

---

## 🔎 Causa Raíz

**El workflow de infraestructura NO se ejecutó correctamente**, o **no se ejecutó en absoluto**.

El flujo debería ser:

```
GitHub Actions: Deploy Infrastructure
    ↓
    1. Empaquetar código Lambda
    2. ✅ Crear bucket: 744165-lambda-code
    3. Subir código a S3
    4. Deploy CloudFormation
    ↓
GitHub Actions: CI/CD (catalogos/notas/notificaciones)
    ↓
    Usa el bucket creado en el paso anterior
```

**Lo que pasó en tu caso:**
- ❌ No se ejecutó el workflow "Deploy Infrastructure"
- ❌ O se ejecutó pero falló
- ❌ El bucket `744165-lambda-code` NUNCA fue creado

---

## ✅ Solución - 4 Pasos Simples

### Paso 1: Verificar que tienes el Secret EXPEDIENTE

1. Ve a tu repositorio en GitHub
2. **Settings** → **Secrets and variables** → **Actions**
3. Verifica que existe el secret `EXPEDIENTE` con valor `744165`
4. Si no existe, créalo:
   - Name: `EXPEDIENTE`
   - Secret: `744165`

### Paso 2: Ejecutar el Workflow de Infraestructura

**ESTO ES CRUCIAL - DEBES HACER ESTO PRIMERO**

1. Ve a GitHub → **Actions**
2. En el menú izquierdo, busca: **"Deploy Infrastructure (AWS Academy)"**
3. Click en el nombre del workflow
4. Click en el botón **"Run workflow"** (a la derecha)
5. En el campo "Tu número de expediente", ingresa: `744165`
6. Click en el botón verde **"Run workflow"**

### Paso 3: Esperar a que Termine

1. Verás que el workflow comienza a ejecutarse
2. **Espera ~10-15 minutos** ☕
3. Debería terminar con ✅ verde
4. Si falla, expande los pasos y mira qué salió mal

### Paso 4: Hacer un Push para Activar CI/CD

Una vez que la infraestructura esté lista:

```bash
# Haz cualquier cambio pequeño
echo "# Infrastructure ready" >> README.md

# Commit y push
git add .
git commit -m "🚀 Infrastructure deployed"
git push
```

Esto disparará los workflows CI/CD que necesitan el bucket.

---

## 📊 Verificar el Progreso

### En GitHub Actions

1. Ve a: **Actions**
2. Deberías ver:
   - ✅ **Deploy Infrastructure (AWS Academy)** - Completado (verde)
   - ✅ **CI/CD Módulo Catálogos** - En progreso o completado
   - ✅ **CI/CD Módulo Notas** - En progreso o completado
   - ✅ **CI/CD Módulo Notificaciones** - En progreso o completado

### En AWS Console

1. Ve a **AWS Academy** → Abre la consola
2. Ve a **S3**
3. Deberías ver 2 buckets:
   - ✅ `744165-lambda-code` (código)
   - ✅ `744165-esi3898k-examen1` (PDFs)

---

## ⚠️ Si el Workflow de Infraestructura Falla

### Error: "ExpiredTokenException" o "Not Authorized"

**Causa:** Las credenciales de AWS Academy expiraron

**Solución:**
1. Reinicia el Lab en AWS Academy (botón Start Lab)
2. Copia nuevas credenciales (AWS Details → Show)
3. Actualiza los 3 secrets en GitHub:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_SESSION_TOKEN`
4. Vuelve a ejecutar el workflow

### Error: "User: ... is not authorized to perform: ..."

**Causa:** Credenciales mal copiadas o incompletas

**Solución:**
1. Verifica que copiaste completo el `AWS_SESSION_TOKEN` (es MUY largo)
2. Vuelve a copiar todos los 3 valores
3. Actualiza los secrets
4. Reintenta

### El Workflow No Aparece en Actions

**Causa:** GitHub Actions necesita el archivo .yml en la rama main

**Solución:**
```bash
git push origin main
# Espera 1-2 minutos
# Recarga la página de Actions
```

---

## 🧪 Testing Manual (Opcional)

Si quieres verificar manualmente que el bucket existe:

```bash
# 1. Configura credenciales de AWS Academy
export AWS_ACCESS_KEY_ID="ASIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_SESSION_TOKEN="..."

# 2. Verifica que el bucket existe
aws s3 ls s3://744165-lambda-code/

# Si ves la salida sin errores, el bucket existe ✅
```

---

## 📋 Checklist Final

- [ ] Secret `EXPEDIENTE` existe en GitHub con valor `744165`
- [ ] Ejecuté el workflow "Deploy Infrastructure (AWS Academy)" con expediente `744165`
- [ ] El workflow terminó con ✅ verde
- [ ] Veo 2 buckets en AWS S3:
  - [ ] `744165-lambda-code`
  - [ ] `744165-esi3898k-examen1`
- [ ] Hice un push para activar los CI/CD workflows
- [ ] Los workflows CI/CD terminaron con ✅ verde

---

## 🎯 ORDEN CORRECTO DE EJECUCIÓN

```
1️⃣ Configurar Secrets en GitHub
   ↓
2️⃣ Ejecutar "Deploy Infrastructure"
   ↓
3️⃣ Esperar ~15 minutos
   ↓
4️⃣ Verificar buckets en AWS S3
   ↓
5️⃣ Hacer push de código
   ↓
6️⃣ CI/CD workflows se disparan automáticamente
   ↓
7️⃣ Verificar que todo termina con ✅
```

---

## 📚 Documentación Relacionada

Ver las secciones en `GUIA-AWS-ACADEMY.md`:
- **Sección 5:** Configurar Secrets en GitHub
- **Sección 6:** Despliegue Inicial (Infraestructura)
- **Sección 9:** Actualizar Credenciales

---

## 💡 Resumen Rápido

| Problema | Solución |
|----------|----------|
| Bucket no existe | Ejecutar workflow "Deploy Infrastructure" |
| Credenciales expiradas | Reiniciar Lab y actualizar secrets |
| Workflows no aparecen | Hacer push a main y esperar 1-2 min |
| Upload a S3 falla | Esperar a que termine "Deploy Infrastructure" |
