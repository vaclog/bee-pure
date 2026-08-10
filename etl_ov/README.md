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

La version desplegada vive en `etl_ov/VERSION` y viaja automaticamente al copiar la carpeta completa. Para publicar una nueva version alcanza con editar ese archivo antes de copiar `etl_ov/`.

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
VKM_CUENTA_ID=cuenta-logistica-vkm-opcional

ETL_OV_NEW_CUSTOMER_PATH=C:\..\etl_ov\out\new_customers
ETL_OV_DRY_RUN=true
ETL_OV_LOG_LEVEL=INFO
```

Importante:

- No versionar `.env`.
- `DEPOSITO_API_TOKEN` debe coincidir con `DEPOSITO_ETL_API_TOKEN` configurado en el sistema del depósito.
- En modo automático, la cuenta VKM sale de `Client.vkm_cliente_id` y viaja como `vkm_cuenta_id` en cada fila exportada.
- `CustomerSyncQueue.client_id` identifica la cuenta interna `clients.id`; no es el valor que se informa a VKM.
- `VKM_CUENTA_ID` queda sólo como fallback opcional para modo manual/transición si el CSV no trae `vkm_cuenta_id`.
- `ETL_OV_DRY_RUN=true` es seguro para pruebas porque no toca backend ni VKM.

### 7. Validar instalación sin tocar sistemas externos

Ejecutar:

```powershell
type VERSION
python -m src.main --version
python -m src.main --dry-run
```

Resultado esperado:

- `VERSION` contiene la version desplegada, por ejemplo `1.0.0`;
- `python -m src.main --version` imprime `ETL OV 1.0.0`;
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

Orden de despliegue recomendado:

1. desplegar primero el backend que acepta `customer_mappings`;
2. aplicar todas las migraciones pendientes de ese backend antes de validar la release;
3. verificar el backend antes de cambiar el ETL, incluyendo al menos `python manage.py check` y la comprobación del flujo `POST /api/ordenes-venta/etl/customer-sync/confirm/` con y sin `customer_mappings`;
4. desplegar después `etl_ov` versión `1.1.0`.

No automatizar rollbacks de migraciones para este orden de despliegue. La compatibilidad con payloads antiguos sin `customer_mappings` debe mantenerse hasta completar la verificación del backend.

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

En este caso el ETL procesa clientes pendientes de todas las cuentas exportables.

### 11. Checklist final

Antes de dejarlo productivo, confirmar:

- `.env` existe y no está versionado;
- `.venv` está creado;
- dependencias instaladas;
- driver ODBC instalado;
- `DEPOSITO_API_BASE_URL` apunta al backend correcto;
- `DEPOSITO_API_TOKEN` coincide con `DEPOSITO_ETL_API_TOKEN`;
- credenciales VKM correctas;
- `Client.vkm_cliente_id` configurado para las cuentas a procesar;
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
ETL informa etl_queued tras insertar en IntEntidad
  ↓
ETL confirma etl_confirmed cuando VKM pasa INEEst a 2
  ↓
Dashboard OV libera CSV OV si corresponde
```

| Valor técnico | Texto en admin | Qué significa |
| --- | --- | --- |
| `pending_export` | Pendiente exportar clientes | Estado inicial/default. Cliente nuevo dado de alta en BackOffice y pendiente de ser tomado por el ETL. |
| `clients_csv_downloaded` | CSV clientes descargado | El ETL ya tomó/exportó el cliente para procesarlo. Todavía no fue insertado ni confirmado en VKM. |
| `etl_queued` | En cola VKM | El ETL insertó el cliente en `IntEntidad` con `INEEst=1`. Es un estado intermedio: VKM todavía no lo incorporó. |
| `etl_confirmed` | ETL clientes confirmado | VKM ya incorporó el cliente y el ETL verificó `INEEst=2`. Recién en este estado se considera confirmado. |
| `etl_partial` | ETL clientes parcial | El ETL confirmó parcialmente; hubo alguna diferencia, procesamiento incompleto o caso que requiere seguimiento. |
| `etl_error` | ETL clientes error | El ETL falló o devolvió error. |

Notas:

- `pending_export` es el estado inicial/default.
- Si el backend detecta un cliente incompleto antes de exportarlo al ETL, no lo marca como `clients_csv_downloaded`: lo deja en `etl_error` con detalle para correcciÃ³n y reintento operativo.
- Si la validaciÃ³n defensiva del ETL falla luego de una exportaciÃ³n, el ETL informa `error` al backend por IDs de cola cuando estÃ¡n disponibles, o por `request_id` como respaldo.
- `etl_queued` puede permanecer pendiente si VKM nunca cambia `INEEst` de `1` a `2`.
- El Dashboard OV muestra `REVISAR` cuando un cliente queda en `etl_queued` por más de 5 minutos.

El Dashboard OV sólo libera el `CSV OV` cuando los clientes necesarios para ese batch están confirmados correctamente.

Desde este flujo, `etl_confirmed` significa algo más específico: VKM ya dejó listo el cliente, el ETL resolvió `ENT.EntID`, el backend persistió `customers.codigo_valkimia` y recién después confirmó la fila de `CustomerSyncQueue`.

Si `INEEst=2` pero `ENT.EntID` todavía no puede resolverse, el ETL no confirma la fila y la deja en un estado seguro no confirmado para reintentar en una corrida posterior.

## Flujo automático

Endpoint automático:

```text
POST /api/ordenes-venta/etl/customer-sync/export/
POST /api/ordenes-venta/etl/customer-sync/queued/
POST /api/ordenes-venta/etl/customer-sync/confirm/
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

Estas columnas corresponden al contrato de clientes del BackOffice: `codigo`, `nombre`, `direccion`, `localidad`, `provincia` y `cp`.

El modo manual es sólo un respaldo operativo. No consulta pendientes al backend y no marca `clients_csv_downloaded`.
Puede incluir `vkm_cuenta_id`; si no lo incluye, el ETL usa `VKM_CUENTA_ID` como fallback.

## Configuración

Variables:

- `DEPOSITO_API_BASE_URL`: URL base del backend, por ejemplo `http://localhost:8000`.
- `DEPOSITO_API_TOKEN`: token Bearer para endpoints internos; debe coincidir con `DEPOSITO_ETL_API_TOKEN` en el backend.
- `VKM_SQLSERVER_HOST`: host SQL Server de VKM.
- `VKM_SQLSERVER_PORT`: puerto SQL Server. Por defecto `1433`.
- `VKM_SQLSERVER_DATABASE`: base de datos VKM.
- `VKM_SQLSERVER_USER`: usuario SQL Server.
- `VKM_SQLSERVER_PASSWORD`: password SQL Server.
- `VKM_SQLSERVER_DRIVER`: driver ODBC. Por defecto `ODBC Driver 17 for SQL Server`.
- `VKM_CUENTA_ID`: fallback opcional para modo manual/transición si la fila no trae `vkm_cuenta_id`.
- `ETL_OV_NEW_CUSTOMER_PATH`: carpeta local opcional para guardar el CSV de respaldo de clientes exportados.
- `ETL_OV_DRY_RUN`: `true` por defecto.
- `ETL_OV_LOG_LEVEL`: `INFO` por defecto.

En el sistema del depósito configurar `DEPOSITO_ETL_API_TOKEN` con el mismo valor que `DEPOSITO_API_TOKEN`.

## Alta en VKM

El cliente VKM usa `pyodbc` y SQL parametrizado.

Existencia:

```text
ENT.EntEntIDC = cliente_id
ENT6.EntLogID = vkm_cuenta_id
```

Resolución de `codigo_valkimia` en confirmación automática:

```text
ENT.EntEntIDC = customer_code
ENT6.EntLogID = vkm_cuenta_id
ENT.EntID = codigo_valkimia
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
- `INEntLogE`: `vkm_cuenta_id`

El insert mantiene los valores fijos del legacy:

- `INEntOper=0`
- `INEntDep='N'`
- `INEntDest='N'`
- `INEntOrig='S'`
- `INEntTDI=80`
- `INEEst='1'`
- `INEntUsuReg='vaclog'`
- `INEntAgc=NULL`
- `INEntIVA='1'`

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
etl_queued si IntEntidad queda en INEEst=1
  ↓
confirmación posterior si INEEst=2
  ↓
confirm_customer_sync
```

Comando con cuenta específica:

```powershell
python -m src.main --client-id 123
```

Si no se informa `--client-id`, el ETL procesa clientes pendientes de todas las cuentas exportables:

```powershell
python -m src.main
```

El modo automático usa un lock local `.etl_ov.automatic.lock` para evitar ejecuciones superpuestas del mismo job. Si detecta otra corrida en curso, la nueva ejecución sale sin procesar filas.

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
6. Si el cliente ya existe en `ENT/ENT6`, confirma usando `ENT.EntID`.
7. Si un cliente en `etl_queued` pasa a `INEEst=2`, vuelve a resolver `ENT.EntID` y recién ahí confirma al backend.
8. Informa el resultado al sistema del depósito.

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

Uso recomendado cuando se quieren procesar todas las cuentas con clientes pendientes.

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

- `client_id`
- `cliente_id`
- `nombre`
- `direccion`
- `localidad`
- `provincia`
- `codigo_postal`
- `observacion`
- `tipo`
- `numero_documento`
- `vkm_cuenta_id`

Este archivo no es la fuente principal del proceso automático. La fuente principal es la API del sistema del depósito.

## Confirmación al sistema del depósito

Endpoint backend:

```text
POST /api/ordenes-venta/etl/customer-sync/confirm/
```

Payload por `request_id`:

```json
{
  "request_id": "req-123",
  "status": "confirmed|queued|partial|error",
  "error_detail": "opcional"
}
```

Payload por IDs de cola:

```json
{
  "ids": [123, 456],
  "status": "confirmed|queued|error",
  "error_detail": "opcional"
}
```

Payload por IDs de cola con `customer_mappings` opcional:

```json
{
  "ids": [123, 456],
  "status": "confirmed",
  "error_detail": "",
  "customer_mappings": [
    {
      "id": 123,
      "customer_code": "C001",
      "codigo_valkimia": "501"
    },
    {
      "id": 456,
      "customer_code": "C002",
      "codigo_valkimia": "502"
    }
  ]
}
```

Reglas operativas:

- `customer_mappings` es opcional y sólo se envía cuando hay filas automáticas confirmadas.
- Cada mapping incluye `CustomerSyncQueue.id`, el código de cliente normalizado y `codigo_valkimia`.
- `codigo_valkimia` sale de `ENT.EntID`.
- El ETL resuelve `ENT.EntID` usando `ENT.EntEntIDC = customer_code` y `ENT6.EntLogID = vkm_cuenta_id`.
- El backend persiste `customers.codigo_valkimia` antes de marcar la fila como `etl_confirmed`.
- Una fila no se confirma si `ENT.EntID` todavía no puede resolverse.
- Las confirmaciones manuales o legacy por `request_id` siguen funcionando sin `customer_mappings`.

## Estado actual

La conexión a SQL Server/VKM y el alta de clientes están encapsuladas en `src/vkm_client.py`.

En modo automático real, el ETL consulta el backend, genera respaldo local si corresponde, procesa VKM y confirma resultado.

En modo `dry-run` automático, el ETL no consulta backend, no genera CSV local, no conecta a VKM y no informa confirmación.

En modo manual con `--csv-path --dry-run`, sólo valida el CSV local.

## Versionado

La fuente de verdad de la version desplegada es `etl_ov/VERSION`.

- Editar solo `VERSION` antes de copiar la carpeta completa `etl_ov/`.
- `python -m src.main --version` muestra la version efectiva sin tocar backend ni VKM.
- Si `VERSION` falta, esta vacio o no puede leerse, el ETL sigue ejecutando y usa `unknown`.
- Cada corrida normal registra `version=<valor>` al inicio y al final.

Comandos utiles desde `etl_ov/`:

```powershell
type VERSION
python -m src.main --version
```

Sugerencia de progresion:

- patch: `1.0.1`
- feature compatible: `1.1.0`
- cambio incompatible: `2.0.0`

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
