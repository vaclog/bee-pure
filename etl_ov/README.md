# ETL OV

Proceso nuevo, autocontenido, para el circuito automático de clientes nuevos de Órdenes de Venta.

El flujo principal ya no depende de una descarga manual desde el Dashboard OV. El ETL consulta al backend los clientes pendientes, los marca como `clients_csv_downloaded`, procesa el alta/confirmación contra VKM y reporta el resultado final al backend.

El legacy vive fuera de esta carpeta y no se toma como base para el flujo nuevo.

## Ejecución aislada

`etl_ov/` es autocontenido:

- no importa Django;
- no usa `backend/hojaruta/settings.py`;
- no depende de las carpetas legacy;
- se comunica con el sistema del depósito sólo por HTTP;
- se conecta a VKM por SQL Server usando `pyodbc`.

Para deploy, crear un `.env` local y ejecutar el job desde esta carpeta etl_ov/.

Ejemplo de ubicación esperada:

```text
./
├─ procesos_legacy_existentes/
├─ common/
├─ otros_archivos_legacy/
└─ etl_ov/
   ├─ src/
   ├─ tests/
   ├─ README.md
   ├─ requirements.txt
   └─ .env
```

El proceso legacy puede seguir corriendo en paralelo fuera de `etl_ov/`.

## Instalación y puesta en marcha

Estos pasos dejan `etl_ov` listo para ejecutarse como job aislado.

### 1. Copiar la carpeta

Copiar la carpeta completa `etl_ov/` al servidor donde se va a ejecutar el proceso.

Ubicación recomendada:

```text
./
├─ procesos_legacy_existentes/
├─ common/
├─ otros_archivos_legacy/
└─ etl_ov/
   ├─ src/
   ├─ tests/
   ├─ README.md
   ├─ requirements.txt
   ├─ .env.example
   └─ .env
```

El proceso legacy queda fuera de `etl_ov/` y puede seguir funcionando en paralelo.

### 2. Entrar a la carpeta del ETL

```powershell
cd C:\..\etl_ov
```

Todos los comandos del ETL deben ejecutarse desde esta carpeta.

### 3. Crear el entorno virtual

En Windows:

```powershell
python -m venv .venv
```

Activar el entorno:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación por política de ejecución, usar:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

y volver a activar:

```powershell
.\.venv\Scripts\Activate.ps1
```

En Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Actualizar pip e instalar dependencias

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Dependencias principales:

- `requests`: comunicación HTTP con el sistema del depósito.
- `python-dotenv`: lectura del archivo `.env`.
- `pyodbc`: conexión a SQL Server/VKM.

### 5. Verificar driver ODBC de SQL Server

El servidor debe tener instalado el driver ODBC para SQL Server.

Driver esperado por defecto:

```text
ODBC Driver 17 for SQL Server
```

Ese valor debe coincidir con la variable:

```text
VKM_SQLSERVER_DRIVER
```

Si el servidor usa otro driver, ajustar el `.env`.

### 6. Crear archivo `.env`

Copiar el ejemplo:

```powershell
Copy-Item .env.example .env
```

Editar `.env` y completar las variables reales:

```env
DEPOSITO_API_BASE_URL=https://url-del-sistema-deposito
DEPOSITO_API_TOKEN=token-interno

VKM_SQLSERVER_HOST=host-sqlserver
VKM_SQLSERVER_PORT=1433
VKM_SQLSERVER_DATABASE=VKM_Interfaz_Prod
VKM_SQLSERVER_USER=usuario
VKM_SQLSERVER_PASSWORD=password
VKM_SQLSERVER_DRIVER=ODBC Driver 17 for SQL Server
VKM_CUENTA_ID=cuenta-logistica-vkm

ETL_OV_NEW_CUSTOMER_PATH=C:\..\etl_ov\out\new_customers
ETL_OV_DRY_RUN=true
ETL_OV_LOG_LEVEL=INFO
```

Importante:

- No versionar `.env`.
- `DEPOSITO_API_TOKEN` debe coincidir con `DEPOSITO_ETL_API_TOKEN` configurado en el sistema del depósito.
- `VKM_CUENTA_ID` debe ser la cuenta/logística de VKM equivalente a `CUENTA_ID` del proceso legacy.
- `ETL_OV_DRY_RUN=true` es seguro para pruebas porque no toca backend ni VKM.

### 7. Validar instalación sin tocar sistemas externos

Ejecutar:

```powershell
python -m src.main --dry-run
```

Resultado esperado:

- el script arranca correctamente;
- carga configuración;
- no consulta backend;
- no conecta a VKM;
- no genera CSV;
- no confirma resultados.

### 8. Ejecutar tests

Desde `etl_ov/`:

```powershell
python -m unittest discover tests
```

Resultado esperado:

```text
OK
```

### 9. Probar modo automático real

Antes de usar el job en producción, cambiar en `.env`:

```env
ETL_OV_DRY_RUN=false
```

Ejecutar para una cuenta específica:

```powershell
python -m src.main --client-id 123
```

Este comando:

1. consulta clientes pendientes al backend;
2. marca exportación interna;
3. genera CSV local si `ETL_OV_NEW_CUSTOMER_PATH` está configurado;
4. procesa alta/confirmación en VKM;
5. confirma resultado al backend.

### 10. Configurar ejecución programada

Ejemplo de comando para scheduler en Windows:

```powershell
cd C:\..\etl_ov
.\.venv\Scripts\python.exe -m src.main --client-id 123
```

Ejemplo sin cuenta específica:

```powershell
cd C:\..\etl_ov
.\.venv\Scripts\python.exe -m src.main
```

En este caso el backend selecciona una cuenta con clientes pendientes.

### 11. Checklist final

Antes de dejarlo productivo, confirmar:

- `.env` existe y no está versionado;
- `.venv` está creado;
- dependencias instaladas;
- driver ODBC instalado;
- `DEPOSITO_API_BASE_URL` apunta al backend correcto;
- `DEPOSITO_API_TOKEN` coincide con `DEPOSITO_ETL_API_TOKEN`;
- credenciales VKM correctas;
- `VKM_CUENTA_ID` correcto;
- `ETL_OV_DRY_RUN=false` para ejecución real;
- `ETL_OV_NEW_CUSTOMER_PATH` existe o puede ser creado por el proceso;
- `python -m unittest discover tests` pasa OK;
- `python -m src.main --dry-run` ejecuta OK.

## Proceso actualizado de alta de clientes

El alta de clientes nuevos se gestiona con una cola interna y un proceso automático.

Flujo completo:

```text
BackOffice importa clientes
  ↓
CustomerSyncQueue queda pending_export
  ↓
Proceso automático real exporta clientes
  ↓
Proceso automático marca clients_csv_downloaded con historial
  ↓
ETL procesa alta en VKM
  ↓
ETL confirma etl_confirmed / etl_partial / etl_error
  ↓
Dashboard OV libera CSV OV si corresponde
```

Estados principales:

- `pending_export`: el cliente fue dado de alta en BackOffice y está pendiente de exportación interna.
- `clients_csv_downloaded`: el proceso automático tomó el cliente para procesarlo.
- `etl_confirmed`: el cliente fue confirmado correctamente.
- `etl_partial`: hubo confirmación parcial o alguna observación.
- `etl_error`: hubo error en el alta o confirmación.

El Dashboard OV sólo libera el `CSV OV` cuando los clientes necesarios para ese batch están confirmados correctamente.

## Flujo automático

1. BackOffice registra clientes nuevos en `CustomerSyncQueue` con estado `pending_export`.
2. El ETL llama al backend para tomar pendientes y marcarlos `clients_csv_downloaded`.
3. El ETL guarda un CSV local de respaldo si `ETL_OV_NEW_CUSTOMER_PATH` está configurado.
4. El ETL procesa esos clientes en VKM.
5. El ETL confirma al backend `confirmed`, `partial` o `error`.
6. El backend traduce esos resultados a `etl_confirmed`, `etl_partial` o `etl_error`.
7. El Dashboard OV libera `CSV OV` sólo cuando la confirmación queda OK.

Endpoint automático:

```text
POST /api/ordenes-venta/customer-sync/export/
```

Payload opcional:

```json
{
  "client_id": 123,
  "request_id": "opcional",
  "limit": 500
}
```

## Entrada manual de respaldo

El modo manual acepta un CSV separado por `;` con headers mínimos:

```csv
cliente_id;nombre;direccion;localidad;provincia;codigo_postal
```

Columnas requeridas:

- `cliente_id`
- `nombre`
- `direccion`
- `localidad`
- `provincia`
- `codigo_postal`

El modo manual es sólo un respaldo operativo. No consulta pendientes al backend y no marca `clients_csv_downloaded`.

## Configuración

Crear un `.env` local a partir de `.env.example`.

Variables:

- `DEPOSITO_API_BASE_URL`: URL base del backend, por ejemplo `http://localhost:8000`.
- `DEPOSITO_API_TOKEN`: token Bearer para endpoints internos; debe coincidir con `DEPOSITO_ETL_API_TOKEN` en el backend.
- `VKM_SQLSERVER_HOST`: host SQL Server de VKM.
- `VKM_SQLSERVER_PORT`: puerto SQL Server. Por defecto `1433`.
- `VKM_SQLSERVER_DATABASE`: base de datos VKM.
- `VKM_SQLSERVER_USER`: usuario SQL Server.
- `VKM_SQLSERVER_PASSWORD`: password SQL Server.
- `VKM_SQLSERVER_DRIVER`: driver ODBC. Por defecto `ODBC Driver 17 for SQL Server`.
- `VKM_CUENTA_ID`: cuenta/logística usada en VKM, equivalente a `CUENTA_ID` del legacy.
- `ETL_OV_NEW_CUSTOMER_PATH`: carpeta local opcional para guardar el CSV de respaldo de clientes exportados.
- `ETL_OV_DRY_RUN`: `true` por defecto.
- `ETL_OV_LOG_LEVEL`: `INFO` por defecto.

En el sistema del depósito configurar `DEPOSITO_ETL_API_TOKEN` con el mismo valor que `DEPOSITO_API_TOKEN`.

## Alta en VKM

El cliente VKM usa `pyodbc` y SQL parametrizado.

Existencia:

```text
ENT.EntEntIDC = cliente_id
ENT6.EntLogID = VKM_CUENTA_ID
```

Alta:

```text
INSERT INTO [VKM_Interfaz_Prod].[dbo].[IntEntidad]
```

Campos principales:

- `INEntId`, `INEntNTdi`: `cliente_id`
- `INEntNombre`: `nombre`
- `INEntDir`: `direccion`
- `INEntLclNom`: `localidad`
- `INEntPrvNom`: `provincia`
- `INEntCP`: `codigo_postal`
- `INEntObs`: `observacion`
- `INEntLogE`: `VKM_CUENTA_ID`

El insert mantiene los valores fijos del legacy:

- `INEntOper=0`
- `INEntDep='N'`
- `INEntDest='N'`
- `INEntOrig='S'`
- `INEntTDI=80`
- `INEEst='1'`
- `INEntUsuReg='vaclog'`
- `INEntAgc='1'`

## Modos de ejecución

Todos los comandos deben ejecutarse desde la carpeta `etl_ov/`.

El ETL tiene dos modos principales:

1. Modo automático.
2. Modo manual.

También existe `dry-run` para validar sin tocar sistemas externos.

## Modo automático

Es el modo normal de operación y el que debe usar el job programado.

```text
backend pending_export
  ↓
export endpoint
  ↓
clients_csv_downloaded
  ↓
VKM
  ↓
confirm_customer_sync
```

Comando con cuenta específica:

```powershell
python -m src.main --client-id 123
```

Si no se informa `--client-id`, el backend selecciona una cuenta con clientes pendientes:

```powershell
python -m src.main
```

Si se quiere limitar la cantidad de clientes tomados en una ejecución:

```powershell
python -m src.main --client-id 123 --limit 100
```

Qué hace:

1. Consulta al sistema del depósito los clientes pendientes de alta interna.
2. Marca esos clientes como exportados para proceso interno.
3. Genera un CSV local de respaldo si `ETL_OV_NEW_CUSTOMER_PATH` está configurado.
4. Verifica si cada cliente ya existe en VKM.
5. Si el cliente no existe, lo inserta en SQL Server VKM.
6. Informa el resultado al sistema del depósito.

Ejemplo de uso con scheduler:

```powershell
cd C:\..\etl_ov
python -m src.main --client-id 123
```

## Modo automático dry-run

Este modo sirve para validar que el proceso levanta correctamente sin tocar sistemas externos.

```powershell
python -m src.main --dry-run
```

Qué hace:

- no consulta al backend;
- no marca clientes como exportados;
- no genera CSV local;
- no conecta a VKM;
- no inserta clientes;
- no confirma resultados.

Usar este modo para validar instalación, imports, configuración básica y arranque del script.

## Modo manual de respaldo con CSV

Este modo procesa un CSV local existente.

```text
--csv-path
  ↓
respaldo operativo
  ↓
no marca exportación en backend
```

Comando:

```powershell
python -m src.main --csv-path .\clientes_nuevos.csv --request-id req-123
```

Qué hace:

1. Lee el CSV indicado.
2. Valida columnas requeridas.
3. Procesa los clientes contra VKM.
4. Confirma el resultado al sistema del depósito usando el `request_id` informado.

Qué no hace:

- no consulta clientes pendientes al backend;
- no marca clientes como exportados;
- no genera otro CSV de respaldo.

Este modo debe usarse sólo como respaldo operativo o para reprocesar un archivo puntual.

Ejemplo con dry-run manual:

```powershell
python -m src.main --csv-path .\clientes_nuevos.csv --request-id req-123 --dry-run
```

En este caso valida el archivo, pero no conecta a VKM ni confirma resultados.

## Resumen de modos

### Modo automático real con cuenta específica

```powershell
python -m src.main --client-id 123
```

Uso recomendado para el job programado cuando se quiere procesar una cuenta concreta.

Hace:

- consulta clientes pendientes al backend;
- marca exportación interna;
- genera CSV de respaldo si `ETL_OV_NEW_CUSTOMER_PATH` está configurado;
- inserta o confirma clientes en VKM;
- confirma el resultado al backend.

---

### Modo automático real sin cuenta específica

```powershell
python -m src.main
```

Uso recomendado cuando se quiere que el backend seleccione automáticamente una cuenta con clientes pendientes.

Hace lo mismo que el modo automático real con cuenta específica:

- consulta clientes pendientes al backend;
- marca exportación interna;
- genera CSV de respaldo si `ETL_OV_NEW_CUSTOMER_PATH` está configurado;
- inserta o confirma clientes en VKM;
- confirma el resultado al backend.

---

### Modo automático dry-run

```powershell
python -m src.main --dry-run
```

Sirve para validar que el proceso arranca correctamente.

No hace:

- no consulta backend;
- no marca exportación;
- no genera CSV;
- no conecta a VKM;
- no inserta clientes;
- no confirma resultado.

---

### Modo manual real con CSV

```powershell
python -m src.main --csv-path archivo.csv --request-id req-123
```

Sirve para procesar un CSV local existente como respaldo operativo.

Hace:

- lee un CSV local;
- valida columnas requeridas;
- inserta o confirma clientes en VKM;
- confirma el resultado al backend usando el `request_id`.

No hace:

- no consulta clientes pendientes al backend;
- no marca `clients_csv_downloaded`;
- no genera otro CSV de respaldo.

---

### Modo manual dry-run con CSV

```powershell
python -m src.main --csv-path archivo.csv --request-id req-123 --dry-run
```

Sirve para validar un CSV local sin tocar sistemas externos.

No hace:

- no conecta a VKM;
- no inserta clientes;
- no confirma resultado;
- no marca exportación en backend.

## CSV local de respaldo

En modo automático real, si `ETL_OV_NEW_CUSTOMER_PATH` está configurado, se genera un archivo local:

```text
clientes_nuevos_<YYYYMMDD_HHMMSS>_<request_id>.csv
```

Este archivo sirve como respaldo operativo de los clientes que el backend entregó al ETL.

El CSV usa delimitador `;` y columnas:

- `cliente_id`
- `nombre`
- `direccion`
- `localidad`
- `provincia`
- `codigo_postal`
- `observacion`
- `tipo`
- `numero_documento`

Este archivo no es la fuente principal del proceso automático. La fuente principal es la API del sistema del depósito.

## Confirmación al sistema del depósito

Endpoint backend:

```text
POST /api/ordenes-venta/customer-sync/confirm/
```

Payload:

```json
{
  "request_id": "req-123",
  "status": "confirmed|partial|error",
  "queue_type": "customers",
  "error_detail": "opcional"
}
```

## Estado actual

La conexión a SQL Server/VKM y el alta de clientes están encapsuladas en `src/vkm_client.py`.

En modo automático real, el ETL consulta el backend, genera respaldo local si corresponde, procesa VKM y confirma resultado.

En modo `dry-run` automático, el ETL no consulta backend, no genera CSV local, no conecta a VKM y no informa confirmación.

En modo manual con `--csv-path --dry-run`, sólo valida el CSV local.

## Tests

Desde la raíz del repo:

```powershell
python -m unittest discover etl_ov/tests
```

Desde `etl_ov/`:

```powershell
python -m unittest discover tests
python -m src.main --dry-run
```
