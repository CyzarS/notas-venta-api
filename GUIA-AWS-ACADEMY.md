# 🚀 GUÍA COMPLETA: Deploy con AWS Academy + GitHub Actions

Esta guía está diseñada específicamente para **AWS Academy Learner Lab**.

---

## 📋 ÍNDICE

1. [Entender las Limitaciones de AWS Academy](#1-entender-las-limitaciones)
2. [Preparar AWS Academy](#2-preparar-aws-academy)
3. [Crear Repositorio en GitHub](#3-crear-repositorio-en-github)
4. [Subir el Código](#4-subir-el-código)
5. [Configurar Secrets en GitHub](#5-configurar-secrets-en-github)
6. [Despliegue Inicial (Infraestructura)](#6-despliegue-inicial)
7. [CI/CD Automático](#7-cicd-automático)
8. [Verificar el Despliegue](#8-verificar-el-despliegue)
9. [Actualizar Credenciales (Importante)](#9-actualizar-credenciales)
10. [Solución de Problemas](#10-solución-de-problemas)

---

## 1. ENTENDER LAS LIMITACIONES

### ⚠️ AWS Academy tiene estas restricciones:

| Limitación | Impacto | Solución |
|------------|---------|----------|
| Credenciales temporales (4 horas) | Expiran y hay que renovarlas | Actualizar secrets en GitHub |
| No se puede crear usuarios IAM | No podemos usar OIDC | Usamos credenciales directas |
| **No se puede crear ECR** | No podemos subir imágenes Docker | Ver nota abajo |
| Región limitada | Solo `us-east-1` | Ya configurado |

### 🐳 Sobre Docker y el Requisito del Examen

El requisito dice: *"Que cada aplicación pueda generar una imagen de Docker de manera automatizada mediante la ejecución de pipelines"*

**¿Cómo lo cumplimos?**

1. ✅ Cada módulo tiene su `Dockerfile` funcional
2. ✅ El pipeline de GitHub Actions **CONSTRUYE** la imagen Docker (`docker build`)
3. ✅ Se puede verificar en los logs: "Imagen construida exitosamente"
4. ⚠️ No se sube a ECR porque AWS Academy lo prohíbe
5. ✅ Para el despliegue real, se usa ZIP (workaround)

```
Pipeline Flow:
[Test] → [Build Docker Image] → [Package ZIP] → [Deploy to Lambda]
              ↓
         Se construye pero
         no se sube a ECR
         (restricción Academy)
```

**En producción real (no Academy):** Se usaría ECR y Lambda con imágenes de contenedor.

### 🔑 Las 3 credenciales que necesitas:

```
AWS_ACCESS_KEY_ID=ASIA...
AWS_SECRET_ACCESS_KEY=abc123...
AWS_SESSION_TOKEN=FwoGZXIvYXdzE... (MUY LARGO)
```

---

## 2. PREPARAR AWS ACADEMY

### Paso 2.1: Iniciar el Lab

1. Ve a tu curso en **AWS Academy**
2. Click en **"Modules"** → **"Learner Lab"**
3. Click en **"Start Lab"** (botón verde)
4. Espera a que el círculo cambie a **verde** ✅

### Paso 2.2: Obtener las Credenciales

1. Click en **"AWS Details"** (botón a la derecha de Start Lab)

2. Click en **"Show"** junto a "AWS CLI"

3. Verás algo así:
```bash
[default]
aws_access_key_id=ASIAXXXXXXXXXXX
aws_secret_access_key=xxxxxxxxxxxxxxxxxxxxxxxx
aws_session_token=FwoGZXIvYXdzEBYaD... (muy largo)
```

4. **COPIA ESTOS 3 VALORES** - Los necesitarás en GitHub

### Paso 2.3: Abrir la Consola AWS

1. Click en **"AWS"** (el enlace verde a la izquierda)
2. Se abre la consola de AWS en una nueva pestaña

### Paso 2.4: Verificar Servicios (Opcional)

En la consola de AWS, verifica que puedes acceder a:
- **Lambda** (busca "Lambda" en la barra)
- **API Gateway**
- **DynamoDB**
- **S3**
- **ECR** (Elastic Container Registry)
- **CloudWatch**

---

## 3. CREAR REPOSITORIO EN GITHUB

### Paso 3.1: Crear el Repositorio

1. Ve a https://github.com/new

2. Configura:
   - **Repository name:** `notas-venta-api`
   - **Description:** `API REST de Notas de Venta - AWS Lambda`
   - **Visibility:** Private (recomendado)
   - ❌ NO marques "Add a README file"
   - ❌ NO selecciones .gitignore
   - ❌ NO selecciones license

3. Click **"Create repository"**

4. **NO CIERRES ESTA PÁGINA** - la necesitarás

---

## 4. SUBIR EL CÓDIGO

### Paso 4.1: Preparar el Proyecto Local

```bash
# 1. Descomprime el proyecto
unzip proyecto-notas-venta.zip
cd proyecto-notas-venta

# 2. Inicializa Git
git init

# 3. Agrega todos los archivos
git add .

# 4. Primer commit
git commit -m "🚀 Initial commit - Sistema de Notas de Venta"
```

### Paso 4.2: Conectar con GitHub

```bash
# 1. Agrega el repositorio remoto (CAMBIA tu-usuario por tu usuario de GitHub)
git remote add origin https://github.com/tu-usuario/notas-venta-api.git

# 2. Cambia a la rama main
git branch -M main

# 3. Sube el código
git push -u origin main
```

### Paso 4.3: Verificar

Ve a tu repositorio en GitHub y verifica que ves todos los archivos:
- 📁 `modulo-catalogos/`
- 📁 `modulo-notas/`
- 📁 `modulo-notificaciones/`
- 📁 `infrastructure/`
- 📁 `.github/workflows/`

---

## 5. CONFIGURAR SECRETS EN GITHUB

### Paso 5.1: Ir a Secrets

1. En tu repositorio de GitHub
2. Click **"Settings"** (pestaña)
3. En el menú izquierdo: **"Secrets and variables"** → **"Actions"**

### Paso 5.2: Agregar los 4 Secrets de AWS

Click **"New repository secret"** para cada uno:

| Name | Value (de AWS Academy) |
|------|------------------------|
| `AWS_ACCESS_KEY_ID` | `ASIAXXXXXXXXXXX` |
| `AWS_SECRET_ACCESS_KEY` | `tu-secret-access-key` |
| `AWS_SESSION_TOKEN` | `FwoGZXIvYXdzE...` (el token largo) |
| `EXPEDIENTE` | Tu número de expediente (ej: `A01234567`) |

### ⚠️ IMPORTANTE sobre AWS_SESSION_TOKEN

- Este token es **MUY LARGO** (varios párrafos)
- Cópialo **COMPLETO**
- Si lo copias incompleto, fallará

### Paso 5.3: Verificar Secrets

Debes ver 4 secrets configurados:
- ✅ `AWS_ACCESS_KEY_ID`
- ✅ `AWS_SECRET_ACCESS_KEY`
- ✅ `AWS_SESSION_TOKEN`
- ✅ `EXPEDIENTE`

---

## 6. DESPLIEGUE INICIAL

### Paso 6.1: Ejecutar el Workflow de Infraestructura

1. En tu repositorio GitHub, ve a **"Actions"**

2. En el menú izquierdo, click en **"Deploy Infrastructure (AWS Academy)"**

3. Click **"Run workflow"** (botón a la derecha)

4. Ingresa tu **número de expediente** (ej: `A01234567`)

5. Click **"Run workflow"** (botón verde)

### Paso 6.2: Monitorear el Despliegue

1. Click en el workflow que se está ejecutando

2. Verás los pasos:
   - ⏳ Checkout código
   - ⏳ Configurar AWS
   - ⏳ Crear repositorios ECR
   - ⏳ Build y Push imágenes
   - ⏳ Deploy con SAM

3. **Este proceso toma ~10-15 minutos** ☕

### Paso 6.3: Ver los Resultados

Cuando termine (✅ verde):

1. Click en el job **"Deploy Full Infrastructure"**
2. Expande el paso **"Mostrar Outputs"**
3. Verás la **API URL**, por ejemplo:
   ```
   https://abc123xyz.execute-api.us-east-1.amazonaws.com/production
   ```

---

## 7. CI/CD AUTOMÁTICO

### ¿Cómo funciona?

Una vez desplegada la infraestructura, cada vez que hagas push:

| Cambio en... | Se ejecuta... |
|--------------|---------------|
| `modulo-catalogos/` | CI/CD Catálogos |
| `modulo-notas/` | CI/CD Notas |
| `modulo-notificaciones/` | CI/CD Notificaciones |

### Probar el CI/CD

```bash
# 1. Haz un cambio pequeño
echo "# Update" >> modulo-catalogos/README.md

# 2. Commit y push
git add .
git commit -m "🔧 Test CI/CD"
git push
```

Ve a **Actions** en GitHub y verás el workflow ejecutándose.

---

## 8. VERIFICAR EL DESPLIEGUE

### Paso 8.1: Probar la API

Usa tu API URL (la que obtuviste en el paso 6.3):

```bash
# Health check de Catálogos
curl https://TU-API-URL/production/catalogos/health

# Health check de Notas
curl https://TU-API-URL/production/notas/health
```

### Paso 8.2: Probar Endpoints

```bash
# Crear un cliente
curl -X POST https://TU-API-URL/production/catalogos/clientes \
  -H "Content-Type: application/json" \
  -d '{
    "razon_social": "Mi Empresa SA de CV",
    "nombre_comercial": "Mi Empresa",
    "rfc": "XAXX010101000",
    "correo_electronico": "contacto@miempresa.com",
    "telefono": "5551234567"
  }'

# Listar clientes
curl https://TU-API-URL/production/catalogos/clientes
```

### Paso 8.3: Ver Dashboard en CloudWatch

1. En la consola de AWS, busca **"CloudWatch"**
2. En el menú izquierdo: **"Dashboards"**
3. Click en **"production-notas-venta-dashboard"**

---

## 9. ACTUALIZAR CREDENCIALES

### ⚠️ MUY IMPORTANTE

Las credenciales de AWS Academy **expiran cada 4 horas**.

### Cuando el Lab Expira:

1. **Reinicia el Lab** en AWS Academy (Start Lab)

2. **Obtén nuevas credenciales** (AWS Details → Show)

3. **Actualiza los 3 secrets de AWS** en GitHub (EXPEDIENTE no cambia):
   - Ve a Settings → Secrets → Actions
   - Click en cada secret → "Update"
   - Pega el nuevo valor

4. **Vuelve a ejecutar** el workflow si es necesario

### Script para Actualizar Rápido (Opcional)

Si tienes GitHub CLI instalado:

```bash
# Actualizar secrets desde terminal
gh secret set AWS_ACCESS_KEY_ID --body "NUEVO_ACCESS_KEY"
gh secret set AWS_SECRET_ACCESS_KEY --body "NUEVO_SECRET"
gh secret set AWS_SESSION_TOKEN --body "NUEVO_TOKEN"
# EXPEDIENTE no necesita actualizarse
```

---

## 10. SOLUCIÓN DE PROBLEMAS

### Error: "ExpiredTokenException"

**Causa:** Las credenciales de AWS Academy expiraron.

**Solución:**
1. Reinicia el Lab
2. Actualiza los 3 secrets en GitHub
3. Vuelve a ejecutar el workflow

### Error: "Access Denied" o "Not Authorized"

**Causa:** Falta alguna credencial o está mal copiada.

**Solución:**
1. Verifica que copiaste las 3 credenciales
2. El `AWS_SESSION_TOKEN` es muy largo - verifica que esté completo
3. Actualiza los secrets

### Error: "Repository does not exist"

**Causa:** Los repositorios ECR no se crearon.

**Solución:**
1. Ejecuta de nuevo el workflow de infraestructura

### Error en el Build de Docker

**Causa:** Posible problema de sintaxis en el código.

**Solución:**
1. Revisa los logs del workflow
2. Verifica que no hayas modificado mal algún archivo

### El Workflow No Se Ejecuta

**Causa:** Los paths no coinciden.

**Solución:**
1. Ve a Actions → Click en el workflow
2. Click "Run workflow" manualmente

---

## 📊 RESUMEN DE URLs Y RECURSOS

Después del despliegue tendrás:

| Recurso | URL/Nombre |
|---------|------------|
| API Gateway | `https://xxx.execute-api.us-east-1.amazonaws.com/production` |
| Dashboard | CloudWatch → Dashboards → `production-notas-venta-dashboard` |
| Bucket S3 | `{expediente}-esi3898k-examen1` |
| Lambdas | `production-catalogos`, `production-notas`, `production-notificaciones` |

---

## 🎯 CHECKLIST FINAL

- [ ] Lab de AWS Academy iniciado (círculo verde)
- [ ] Credenciales copiadas de AWS Details
- [ ] Repositorio creado en GitHub
- [ ] Código subido al repositorio
- [ ] 4 Secrets configurados en GitHub (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN, EXPEDIENTE)
- [ ] Workflow de infraestructura ejecutado exitosamente
- [ ] API URL funcionando
- [ ] Dashboard de CloudWatch visible

---

## 📞 ¿Necesitas Ayuda?

1. Revisa los logs del workflow en GitHub Actions
2. Revisa CloudWatch Logs en AWS
3. Verifica que el Lab esté activo (círculo verde)

---

## 📄 Documentos Incluidos

| Archivo | Descripción |
|---------|-------------|
| `GUIA-AWS-ACADEMY.md` | Esta guía paso a paso |
| `RESPUESTAS-EXAMEN.md` | Respuestas a las preguntas del examen |
| `README.md` | Documentación técnica del proyecto |

¡Éxito con tu proyecto! 🚀
