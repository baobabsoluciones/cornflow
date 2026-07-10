# Frontend automation — guía técnica (desarrolladores)

**¿Para qué sirve *frontend automation*?** Es el mecanismo del backend que permite publicar, en una **única respuesta JSON**, la documentación de la API en formato **OpenAPI 2.0** (`paths`, `definitions`, …) junto con un bloque adicional, **`available_automations`**, donde se describe **cómo organizar en pantalla** las tablas de datos (menús, títulos, iconos, orden) y **qué URL y método HTTP** corresponden a cada acción sobre cada tabla (listado, alta, borrado, exportación a Excel, etc.). Así un cliente (por ejemplo una aplicación web) puede construir formularios y navegación sin codificar a mano cada ruta del proyecto.

**¿Dónde vive ahora el código?** El **núcleo común** de *frontend automation* está en el paquete `cf_enterprise_poc` (cornflow_enterprise) y se comparte entre todos los proyectos: el **endpoint agregador**, las **clases y métodos** que usa (clases base de sección/grupo/tabla, generación de OpenAPI filtrada por permisos, plugin de Marshmallow), y el **decorador `automate_frontend`** (con el enum `EndpointTypes`), que se importa desde la librería. Lo **específico de cada proyecto** —las declaraciones concretas de secciones, grupos y tablas, los recursos REST decorados, y todo lo que dependa del caso: **nombres de campos, traducciones y `metadata`** de los esquemas Marshmallow— se define en la **aplicación externa** o en los **plugins**, y el endpoint común lo descubre en tiempo de petición. Anteriormente todo esto se definía directamente en el código de cada aplicación o plugin, lo que duplicaba el código entre proyectos; ahora la parte común se reutiliza y solo se mantiene una vez.

**¿Para qué sirve este documento?** Explica el propósito del sistema, la **arquitectura en líneas generales** (qué es común y qué es propio del proyecto), el **código común** solo en la medida necesaria para orientarse, y con detalle la **integración desde la aplicación externa o el plugin**: tipos de operación, decorador `automate_frontend` (importado de `cf_enterprise_poc`), declaración de secciones/grupos/tablas, y uso de `metadata` en Marshmallow. Está dirigido tanto a quien **incorpora** la automatización en un servicio nuevo como a quien **mantiene** o amplía una API que ya la utiliza. El **contrato exhaustivo** del JSON de respuesta (nombres de campos, filtros, etc.) se recoge en [info_frontend_automation_schema.md](./info_frontend_automation_schema.md).

---

## Tabla de contenidos

1. [Objetivo y alcance](#1-objetivo-y-alcance)
2. [Qué es común y qué es del proyecto](#2-qué-es-común-y-qué-es-del-proyecto)
3. [Arquitectura en un vistazo](#3-arquitectura-en-un-vistazo)
4. [La capa común y la integración desde el proyecto](#4-la-capa-común-y-la-integración-desde-el-proyecto)
5. [Checklist de integración](#5-checklist-de-integración-orden-práctico)
6. [Referencia rápida](#6-referencia-rápida)
7. [Extensiones y límites conocidos](#7-extensiones-y-límites-conocidos)
8. [Pruebas y depuración](#8-pruebas-y-depuración)
9. [Documentación relacionada](#9-documentación-relacionada)

---

## 1. Objetivo y alcance

### 1.1. Idea general

En una API con muchas tablas y muchas rutas (listados, detalle, bulk, etc.), un **cliente web** necesita dos cosas a la vez:

1. **Documentación de la API** en formato estándar (aquí, **OpenAPI 2.0**): qué URLs existen, qué método HTTP usar, qué cuerpos y respuestas esperar. Eso sale de los **esquemas Marshmallow** y de las anotaciones que usa **flask-apispec**.
2. **Instrucciones de interfaz**: en qué menú o bloque colocar cada tabla, cómo titularla, qué icono mostrar y en qué orden. Eso **no** forma parte del estándar OpenAPI, por eso se añade el bloque extra **`available_automations`**.

**Frontend automation** es el mecanismo del backend que **marca** qué métodos de qué recursos REST participan en ese catálogo (`@automate_frontend`), **describe** la jerarquía visual (clases de sección / grupo / tabla enlazadas al modelo SQLAlchemy) y **expone** un único `GET` que **junta** todo en un solo JSON para el front.

El mecanismo se reparte en dos capas:

* **Capa común (en `cf_enterprise_poc`)**: el endpoint agregador, el decorador `@automate_frontend` y el enum `EndpointTypes`, las **clases base** de sección/grupo/tabla, la generación de OpenAPI filtrada por permisos y el plugin de Marshmallow. Esta capa **no cambia** entre proyectos y se importa de la librería.
* **Capa de proyecto (en la aplicación externa o los plugins)**: las **subclases concretas** de sección/grupo/tabla, los **recursos REST** decorados con `@automate_frontend`, sus **modelos** con `__frontend_table__`, y los **esquemas Marshmallow** con los nombres de campo, traducciones y `metadata` propios del caso. Esta capa es la que cada proyecto define y mantiene.

### 1.2. ¿Para qué sirve?

* Exponer un **único endpoint** (p. ej. `GET /frontend-automation/`) que devuelve un documento tipo **OpenAPI 2.0** (`definitions`, `paths`, …) más un bloque adicional **`available_automations`**. La lista de operaciones incluida en `paths` y la asociada a cada tabla en `available_automations` **depende del usuario autenticado**: solo se incluyen las rutas y verbos HTTP para los que dicho usuario tiene permiso en el sistema de autorización del despliegue (p. ej. vistas y roles en base de datos). Si no hay permiso para un método concreto, ese método **no aparece** en el JSON aunque exista en el servidor.
* El endpoint acepta un parámetro de query **opcional** `?schema=<nombre>` que permite al cliente solicitar solo las tablas asociadas a un **DAG/schema** concreto. Si el usuario no tiene permiso sobre el schema solicitado, se devuelve un **403**. Si no se pasa el parámetro, se devuelven todas las tablas a las que el usuario tiene acceso según sus permisos de schema.
* Ese bloque describe **cómo debe organizarse la UI** (secciones, grupos, tablas, orden, iconos, títulos) y, para cada tabla de datos, **qué acciones ofrece la API** y **con qué URL y método HTTP** debe llamarlas el cliente. Por ejemplo: cuál es la llamada que devuelve **todas las filas** de la tabla, cuál crea **una sola** fila, cuál crea **varias** de golpe, cuál borra una fila concreta por id, cuál descarga un Excel, etc. Cada una de esas acciones aparece bajo una clave fija (`get_list`, `post_item`, `post_bulk`, …) junto a `url` y `http_method`, para que el front no tenga que adivinar la convención de rutas del proyecto.
* La spec de **paths** y **definitions** se genera a partir de **recursos Flask** decorados con **`@automate_frontend`**, usando esquemas **Marshmallow** y **flask-apispec**.

### 1.3. Qué queda fuera de este documento

* Detalle campo a campo del JSON de respuesta → [info_frontend_automation_schema.md](./info_frontend_automation_schema.md).
* Lógica de negocio de cada tabla (CRUD, ETL, etc.).

---

## 2. Qué es común y qué es del proyecto

La parte común ya está resuelta en `cf_enterprise_poc`: no hay que copiarla ni portarla, solo **importarla y usarla**. Lo que cada proyecto aporta es la **configuración propia del caso**. Este es el reparto:

| Pieza | Dónde vive | Quién la mantiene |
|-------|------------|-------------------|
| Endpoint agregador (`FrontendAutomationEndpoint`, `GET /frontend-automation/`) | `cf_enterprise_poc` (común) | cornflow_enterprise |
| Decorador `@automate_frontend` y enum `EndpointTypes` | `cf_enterprise_poc.frontend_automation` (común) | cornflow_enterprise |
| Clases base de sección/grupo/tabla (`BaseFrontendSection/Group/Table`) | `cf_enterprise_poc.frontend_automation` (común) | cornflow_enterprise |
| Generación de OpenAPI filtrada por permisos (`CornflowUIApiSpec`) y plugin de Marshmallow | `cf_enterprise_poc.frontend_automation` (común) | cornflow_enterprise |
| **Subclases concretas** de sección, grupo y tabla del caso | **Aplicación externa o plugin** | el proyecto |
| **Recursos REST** decorados (`*Endpoint`) y sus **modelos** con `__frontend_table__` | **Aplicación externa o plugin** | el proyecto |
| **Esquemas Marshmallow** con nombres de campo, traducciones y `metadata` | **Aplicación externa o plugin** | el proyecto |

Dependencias técnicas que asume la capa común: **Flask / Flask-RESTful** (el endpoint es un recurso REST), **flask-apispec + apispec** (anotaciones `__apispec__` y generación de paths), **Marshmallow** (esquemas de request/response/query y `metadata={}`), **SQLAlchemy** (modelos con `data_model` y `__tablename__`, que alimenta las claves de `available_automations["tables"]`), y la **capa de permisos del Core** (vistas y roles en BD): `CornflowUIApiSpec` **filtra** `paths` según los permisos del usuario, y el filtrado por `?schema` se apoya en los permisos de DAG.

> El proyecto **no** necesita reimplementar nada de la capa común; basta con importar `automate_frontend`, `EndpointTypes` y las clases base desde `cf_enterprise_poc` y declarar lo propio del caso.

---

## 3. Arquitectura en un vistazo

```text
PROYECTO (aplicación externa / plugin)
  Modelo SQLAlchemy (__tablename__, __frontend_table__)
          │
          ▼
  Recurso REST (p. ej. *Endpoint)  ──►  data_model apunta al modelo
          │   importa @automate_frontend y las clases base de cf_enterprise_poc
          ├─ métodos HTTP (get, post, …) decorados con @automate_frontend
          │       └─ anotan endpoint_type + esquemas (request/response/query)
          │
          ▼
  Lista `resources` del proyecto (URL ↔ clase recurso)
          │  expuesta como `<módulo>.endpoints.resources` (app externa)
          │  o devuelta por `plugin.get_resources()` (plugin)
          ▼
COMÚN (cf_enterprise_poc)
  GET FrontendAutomationEndpoint(?schema=...)
          │
          ├─ reúne las `resources`: propias + de la app externa (EXTERNAL_APP)
          │       + de los plugins (get_resources)
          ├─ valida permiso sobre ?schema (si se pasa) → 403 si no tiene acceso
          ├─ recorre resources con data_model
          │       └─ filtra por schema solicitado y permisos del usuario sobre schemas de la tabla
          ├─ CornflowUIApiSpec.register(...)  →  rellena paths + definitions (filtrado por permisos del usuario)
          └─ _add_automation(...)             →  rellena available_automations
```

Respuesta única: **spec OpenAPI 2.0** + **`available_automations`** inyectado en el diccionario raíz. El endpoint común **descubre en tiempo de petición** los recursos del proyecto, sin que estos tengan que registrarse en cornflow_enterprise.

---

## 4. La capa común y la integración desde el proyecto

La capa común vive en `cf_enterprise_poc`: el paquete `cf_enterprise_poc/frontend_automation/` (decorador, enum, clases base, generación de OpenAPI y plugin de Marshmallow) y el recurso agregador en `cf_enterprise_poc/endpoints/frontend_automation.py`. **No hay que modificarla.** Desde el proyecto solo se importa y se declara lo propio del caso.

---

### 4.1. Alcance: capa común frente a configuración del proyecto

| Situación | Tratamiento en esta guía |
|-----------|-------------------------|
| Componentes comunes que no se modifican (`apispec_tools.py`, plugin de Marshmallow, el `GET` agregador) | Descripción a alto nivel del propósito conjunto (generación de OpenAPI, permisos, descubrimiento de recursos), sin recorrido línea a línea (§4.2). |
| **`EndpointTypes` y `automate_frontend`** (comunes, se importan de `cf_enterprise_poc`) | Uso en los recursos REST del proyecto: decorador, llamada imperativa en `__init__`, argumentos y ejemplos (§§4.3–4.7). |
| **Clases de menú** (secciones, grupos, tablas) y **`metadata` en Marshmallow** (propias del proyecto) | Declaración en el código de la aplicación externa o el plugin. Se resumen los atributos sin alcanzar el nivel de [info_frontend_automation_schema.md](./info_frontend_automation_schema.md) (§§4.8 y 4.9). |

---

### 4.2. Componentes comunes (solo orientación)

Estos viven en `cf_enterprise_poc` y se comparten entre proyectos:

**`frontend_automation/custom_marshmallow_plugin.py`** — Al traducir esquemas Marshmallow al JSON de `definitions`, permite que tipos como `fields.Time` y las claves adicionales de `metadata={...}` en cada campo se reflejen en la spec en lugar de omitirse.

**`frontend_automation/apispec_tools.py`** (`CornflowUIApiSpec`) — Construye la documentación OpenAPI **en memoria y para un usuario concreto**. Solo entra en la spec cada combinación **(URL, método HTTP)** para la que se cumplen **todas** estas condiciones: el método del recurso está decorado con `automate_frontend`, y el usuario autenticado tiene permiso de ejecución sobre esa vista y ese verbo según la política del Core. Si falta la fila de vista en base de datos o no hay ningún rol con permiso, **ningún** método de esa URL se documenta para ese usuario. En consecuencia, el JSON de respuesta **no lista rutas “ocultas”**: solo aparecen las que el usuario podría invocar según la política de acceso.

El mismo criterio alimenta el armado de **`available_automations`**: las entradas por operación (`get_list`, `post_item`, …) se generan a partir de los métodos que han pasado ese filtro, de modo que el menú de acciones **no** muestra botones ligados a llamadas prohibidas para el usuario actual.

**`endpoints/frontend_automation.py`** (`FrontendAutomationEndpoint`) — Recurso con el `GET` agregador. Reúne los recursos a documentar (los del propio enterprise, los de la **aplicación externa** y los de los **plugins** — ver §4.2.1), obtiene la spec del flujo anterior y añade el bloque `available_automations` (menús y acciones por tabla). Es el documento único consumido por el cliente. Las entradas de `paths` cuyo usuario no tiene ningún método permitido se **eliminan** del payload para no devolver objetos vacíos. Acepta un parámetro de query opcional `?schema=<nombre>` (validado por un esquema Marshmallow dedicado) que filtra las tablas incluidas en la respuesta:

* Si se pasa `?schema=X` y el usuario **no** tiene permiso sobre ese schema → respuesta **403**.
* Si se pasa `?schema=X` y el usuario tiene permiso → solo se incluyen las tablas cuyo `schemas` contenga `X` (más las tablas sin restricción de schema, es decir, aquellas con `schemas = None`).
* Si **no** se pasa `?schema` → se incluyen todas las tablas a las que el usuario tiene acceso según los permisos de sus schemas asociados. Las tablas sin `schemas` definido se incluyen siempre.

**`frontend_automation/__init__.py`** — Reexporta lo que el proyecto necesita importar: `automate_frontend` y `EndpointTypes`. Las **clases base** se importan de `cf_enterprise_poc.frontend_automation.base_frontend_groups`.

---

### 4.2.1. Cómo descubre el endpoint común los recursos del proyecto

El endpoint agregador no conoce de antemano los recursos de cada proyecto: los **reúne en tiempo de petición** desde dos orígenes, además de los propios de enterprise.

* **Aplicación externa** — Si `EXTERNAL_APP=1` y la variable de entorno `EXTERNAL_APP_MODULE` apunta al módulo de la aplicación, el endpoint importa `<módulo>.endpoints.resources` y añade esos recursos. Sus URLs se prefijan con `/external/`. El proyecto solo debe exponer su lista `resources` en `endpoints.resources` (la misma convención URL ↔ clase de recurso del Core).
* **Plugins** — Por cada plugin registrado (entry points del grupo `cornflow.plugins`), si el plugin implementa el método **`get_resources()`**, el endpoint añade los recursos que devuelve. Un plugin que no lo implemente simplemente no aporta recursos.

En ambos casos, lo único que el proyecto necesita es:

1. Declarar sus **clases base de menú** importando de `cf_enterprise_poc` (§4.8) y enlazarlas a sus modelos con `__frontend_table__`.
2. Decorar los métodos de sus **recursos REST** con `@automate_frontend` (§§4.3–4.7).
3. Hacer visibles esos recursos al endpoint común mediante `endpoints.resources` (app externa) o `get_resources()` (plugin).

---

### 4.3. `EndpointTypes` — etiquetas de tipo de operación

Constituyen un conjunto de **cadenas fijas** (`get_list`, `post_item`, …). El verbo HTTP real (`GET`, `POST`, …) se define en Flask de forma independiente; el enum indica únicamente **qué papel** cumple ese método dentro del catálogo enviado al cliente.

Bajo cada tabla en `available_automations`, el cliente obtiene, por cada acción expuesta, la **URL** y el **método HTTP** asociados. Ejemplos de interpretación:

* **`get_list`** — Llamada que devuelve el **conjunto de filas** de la tabla (con filtros o paginación en query si la API lo define).
* **`get_item`** — Llamada que devuelve **una fila** identificada por id en la ruta.
* **`post_item`** — Llamada para **crear una** fila nueva.
* **`post_bulk`** — Llamada para **crear muchas** filas en una sola petición.
* **`post_update_bulk`**, **`put_item`**, **`patch_item`**, **`delete_item`**, **`delete_all`**, **`delete_bulk`**, **`overwrite_all`**, **`restore_all`** — Otras acciones de actualización masiva, sustitución, borrado o restauración, según lo implementado y decorado.
* **`download_excel_table`** — Llamada de **exportación a Excel**.
* **`async_post_bulk`** — Llamada para **crear muchas** filas de forma **asíncrona** lanzando un job de Airflow. Acepta un **Excel sin procesar**. Devuelve un `upload_id` y un `status`. Código **202**.
* **`async_post_update_bulk`** — Llamada para **actualizar muchas** filas de forma **asíncrona** lanzando un job de Airflow. Acepta un **Excel sin procesar**. Devuelve un `upload_id` y un `status`. Código **202**.
* **`async_overwrite_all`** — Llamada para **sobrescribir todas** las filas de forma **asíncrona** lanzando un job de Airflow. Acepta un **Excel sin procesar**. Devuelve un `upload_id` y un `status`. Código **202**.
* **`async_upload_status`** — Llamada para **consultar el estado** de una carga asíncrona. Acepta un `upload_id` en la URL. Devuelve un JSON con `status`, `total_rows_loaded` y, en caso de fallo, `error_message`. Código **200**.

Cada clave va acompañada de `url` y `http_method` para evitar que el cliente infiera convenciones a partir del nombre de la clase Python del recurso.

### 4.4. Esquemas de petición y de respuesta según el tipo de operación

No es necesario conocer detalles internos del decorador: basta con la regla siguiente.

* Para operaciones que **devuelven listas u objetos de datos** (`GET_LIST`, `GET_ITEM`), debe existir documentación de **esquema de respuesta**, bien mediante el argumento `schema_response=...` de `automate_frontend`, bien mediante **`@marshal_with(...)`** situado por debajo de `@automate_frontend` en el código fuente. Si falta ambos, el método no se marca para automatización y se registra un aviso en log; el endpoint de negocio puede seguir respondiendo.
* Para operaciones que **reciben cuerpo JSON** (`POST_ITEM`, `PUT_ITEM`, `PATCH_ITEM`, operaciones bulk, `OVERWRITE_ALL`, `DELETE_BULK`, etc.), debe existir documentación de **esquema de petición**, mediante `schema_request=...` o **`@use_kwargs(..., location="json")`**. En caso contrario, mismo efecto: sin anotación de automatización y aviso en log.

Las operaciones que solo devuelven un mensaje (`DELETE_ITEM`, `DELETE_ALL`, …) no exigen esquema de respuesta elaborado; las que no llevan cuerpo no exigen esquema de petición.

### 4.5. Uso como decorador sobre los métodos del recurso

Convención recomendada por el propio módulo: colocar **`@automate_frontend`** **por encima** de `@marshal_with` y `@use_kwargs` en el fichero, de modo que el decorador pueda leer o completar las anotaciones generadas por estos. El primer argumento posicional es siempre el `EndpointType`; los esquemas opcionales (`schema_request`, `schema_response`, `schema_query`) se indican cuando no basta con `marshal_with` / `use_kwargs` o cuando se desea fijarlos explícitamente en `automate_frontend`.

**Ejemplo** — Listado con respuesta declarada en el decorador:

```python
from cf_enterprise_poc.frontend_automation import automate_frontend, EndpointTypes
from flask_apispec import doc, marshal_with
from myapp.schemas import ProductListResponseSchema  # esquema propio del proyecto

class ProductListEndpoint(BaseMetaResource):
    data_model = ProductModel

    @doc(description="List products")
    @automate_frontend(EndpointTypes.GET_LIST, schema_response=ProductListResponseSchema)
    @marshal_with(ProductListResponseSchema)
    def get(self):
        ...
```

**Ejemplo** — Alta con cuerpo documentado mediante `use_kwargs`:

```python
    @doc(description="Create product")
    @automate_frontend(EndpointTypes.POST_ITEM)
    @use_kwargs(ProductSchema, location="json")
    def post(self, **kwargs):
        ...
```

### 4.6. Uso imperativo en el `__init__` del recurso

`automate_frontend` es una **función que devuelve un decorador**. Además de la forma `@automate_frontend(...)` sobre la definición del método, puede aplicarse **después** de definir el método, asignando el resultado de `automate_frontend(...)(self.get)` (o `self.post`, etc.) dentro del **`__init__`** de la clase.

Este patrón se utiliza cuando el esquema Marshmallow **depende de parámetros del constructor** (por ejemplo, la clase `schema` pasada al `__init__` de una clase base genérica). Así se pasa `schema`, `schema(many=True)` o `schema_query` directamente a `automate_frontend` sin duplicar la lógica en cada subclase mediante decoradores estáticos.

**Ejemplo** — Clase base genérica de recurso de tabla: el constructor recibe `data_model`, `schema` y opcionalmente `schema_query`, instancia el schema y envuelve `get` y `post`:

```python
def __init__(self, data_model, schema, schema_query=None):
    super().__init__(data_model)
    self.schema = schema()
    self.get = automate_frontend(
        endpoint_type=EndpointTypes.GET_LIST,
        schema_response=schema(many=True),
        schema_query=schema_query,
    )(self.get)
    self.post = automate_frontend(
        endpoint_type=EndpointTypes.POST_ITEM, schema_request=schema
    )(self.post)
```

Una clase base de detalle puede aplicar el mismo enfoque sobre `get`, `put` y `delete` con los `EndpointTypes` correspondientes.

### 4.7. Reaplicación del decorador y `overwrite_existing_annotations`

Por defecto, `overwrite_existing_annotations=False`. Si el método **ya** posee `__automate_frontend__` (por ejemplo porque la clase base lo aplicó en su `__init__`), una **segunda** llamada a `automate_frontend` sobre el mismo método **no modifica nada** y se deja constancia en el log.

Cuando una subclase debe **sustituir** la automatización heredada (otro `EndpointTypes`, otros esquemas o ambos), debe invocarse de nuevo `automate_frontend(...)(self.get)` (o el método que corresponda) con **`overwrite_existing_annotations=True`**.

**Ejemplo** — Recurso de **ajustes globales** (`Settings`) que hereda de una base de tabla ya decorada en `__init__`: el padre documenta el listado como `schema(many=True)`, pero este recurso solo expone **un único** registro de configuración y debe documentar la respuesta como un **solo** objeto. Tras `super().__init__(SettingsModel, SettingsSchema)`, se **vuelve a decorar** con `overwrite_existing_annotations=True`:

```python
class SettingsTableEndpoint(BaseTableEndpoint):
    def __init__(self):
        super().__init__(SettingsModel, SettingsSchema)

        self.get = automate_frontend(
            endpoint_type=EndpointTypes.GET_LIST,
            schema_response=SettingsSchema,
            overwrite_existing_annotations=True,
        )(self.get)
        self.post = automate_frontend(
            endpoint_type=EndpointTypes.POST_ITEM,
            schema_request=SettingsSchema,
            overwrite_existing_annotations=True,
        )(self.post)
```

**Argumentos de `automate_frontend`** (referencia):

| Argumento | Uso |
|-----------|-----|
| `endpoint_type` | Obligatorio. Miembro de `EndpointTypes`. |
| `schema_response` | Esquema Marshmallow de salida cuando no basta `marshal_with` o se combina con el patrón imperativo. |
| `schema_request` | Esquema del cuerpo JSON cuando no basta `use_kwargs` en JSON o en el patrón imperativo. |
| `schema_query` | Esquema para parámetros de query. Si ya existía anotación de query, la nueva puede ignorarse con aviso en log. |
| `overwrite_existing_annotations` | `True` solo cuando deba reemplazarse una automatización ya presente en el método (típicamente tras `super().__init__` en una subclase). |

Si el decorador encuentra un error interno, el método permanece como el original; la ruta de negocio no se rompe, pero el método puede quedar excluido del JSON de automatización.

---

### 4.8. Declaración en el proyecto: secciones, grupos y tablas (menú)

Estas clases son **propias del proyecto** y se declaran en la aplicación externa o el plugin, **no** en cornflow_enterprise. Son **clases de configuración** (atributos en la propia clase; no hace falta instanciarlas) que heredan de las clases base **comunes** `BaseFrontendSection`, `BaseFrontendGroup` y `BaseFrontendTable`, importadas de `cf_enterprise_poc`:

```python
from cf_enterprise_poc.frontend_automation.base_frontend_groups import (
    BaseFrontendSection,
    BaseFrontendGroup,
    BaseFrontendTable,
)
```

Lo habitual es agrupar las subclases concretas del proyecto en un módulo dedicado (p. ej. `frontend_groups.py` o el nombre que se elija), **dentro del código del proyecto**, e importarlas donde haga falta.

**Sección** (`BaseFrontendSection`):

| Atributo | Obligatorio | Descripción breve |
|----------|-------------|-------------------|
| `name` | Sí | Identificador estable; sale como clave en `available_automations["sections"]`. |
| `title` | Sí | Texto o diccionario por idioma (`en`, `es`, …). |
| `icon` | Sí | Nombre del icono para la UI. |
| `order` | No (por defecto `0`) | Orden entre secciones. |

**Grupo** (`BaseFrontendGroup`):

| Atributo | Obligatorio | Descripción breve |
|----------|-------------|-------------------|
| `name` | Sí | Clave en `available_automations["groups"]`. |
| `title`, `icon` | Sí | Igual que en sección. |
| `frontend_section` | Sí | Sección padre (clase). |
| `order` | No | Orden entre grupos de la misma sección. |

**Tabla** (`BaseFrontendTable`):

| Atributo | Obligatorio | Descripción breve |
|----------|-------------|-------------------|
| `title` | Sí | Nombre de la tabla en la UI (texto o i18n). |
| `icon` | Sí como declaración en la base; en la práctica a menudo `None` si la tabla va dentro de un **grupo** | Si hay `frontend_group`, el icono de la tabla **no se usa** (se avisa en log). |
| `frontend_group` | No (`None` si la tabla cuelga directo de sección) | Grupo (clase) al que pertenece la tabla. |
| `frontend_section` | No | Sección directa si **no** hay grupo. Si se definen grupo y sección a la vez, **solo se utiliza el grupo** (se avisa en log). |
| `schemas` | No (por defecto `None`) | Lista de identificadores de DAG/schema a los que pertenece la tabla (p. ej. `["ie_scheduling_dag", "ie_exams"]`). Determina la visibilidad de la tabla según los permisos del usuario y el filtrado por `?schema=`. Si es `None`, la tabla se muestra a cualquier usuario con acceso al endpoint, sin restricción de schema. |
| `model_table_name` | No (por defecto `__tablename__`) | Nombre de la tabla tal como la identifica el modelo de optimización o el DAG asociado, que puede diferir del nombre en base de datos (`__tablename__`). Permite al frontend y al DAG referirse a la misma entidad lógica aunque internamente la tabla de la BBDD tenga otro nombre. |
| `order` | No | Orden entre tablas del mismo grupo o sección. |

**Ejemplo** (nombres deliberadamente explícitos): la **sección** agrupa todo lo relacionado con el almacén; el **grupo** reúne solo las pantallas sobre entradas de mercancía; la **tabla** es el listado concreto de albaranes de entrada (sin icono propio en la tabla porque el grupo ya da contexto visual).

```python
class FrontendSectionWarehouse(BaseFrontendSection):
    """Bloque de menú de alto nivel: todo lo del almacén."""
    name = "warehouse"
    title = {"en": "Warehouse", "es": "Almacén", "fr": "Entrepôt"}
    icon = "mdi-warehouse"
    order = 1


class FrontendGroupInboundGoods(BaseFrontendGroup):
    """Submenú: solo pantallas sobre mercancía que ENTRA al almacén."""
    frontend_section = FrontendSectionWarehouse
    name = "inbound_goods"
    title = {
        "en": "Inbound goods",
        "es": "Entradas de mercancía",
        "fr": "Réceptions marchandises",
    }
    icon = "mdi-truck-delivery"
    order = 0


class FrontendTableInboundDeliveryNotes(BaseFrontendTable):
    """Tabla concreta: albaranes vinculados a entradas."""
    frontend_section = None
    frontend_group = FrontendGroupInboundGoods
    title = {
        "en": "Inbound delivery notes",
        "es": "Albaranes de entrada",
        "fr": "Bons de livraison entrantes",
    }
    icon = None
    schemas = ["warehouse_dag"]  # solo visible para usuarios con permiso sobre este DAG
    order = 0
```

En el modelo SQLAlchemy de esa tabla se declara `__frontend_table__ = FrontendTableInboundDeliveryNotes` para que el agregador asocie `__tablename__` con el título, la sección y el grupo anteriores.

---

### 4.9. Declaración en el proyecto: `metadata` en campos Marshmallow

Los **esquemas Marshmallow son propios del proyecto** (los nombres de campo, las traducciones y la `metadata` dependen del caso) y se declaran en la aplicación externa o el plugin. En cada `fields.*(..., metadata={...})` es posible añadir pistas para el cliente (los títulos traducidos suelen declararse en ese diccionario como `title`; otras claves se copian al JSON de definiciones salvo las reservadas por la capa de conversión Marshmallow → OpenAPI, que es común).

**Ejemplo** — Esquema de línea de albarán: identificador de producto con título y columnas relacionadas; nombre de producto solo lectura rellenado por join; cantidad con límites numéricos para la UI.

```python
from marshmallow import Schema, fields


class InboundDeliveryLineSchema(Schema):
    product_id = fields.Integer(
        required=True,
        metadata={
            "title": {"en": "Product", "es": "Producto"},
            "columns_to_join": ["product_name"],
        },
    )
    product_name = fields.String(
        dump_only=True,
        metadata={
            "title": {"en": "Product name", "es": "Nombre del producto"},
            "join_from": "products.name",
            "readOnly": True,
        },
    )
    quantity = fields.Number(
        required=True,
        metadata={
            "title": {"en": "Quantity", "es": "Cantidad"},
            "min": 0,
            "max": 9999,
        },
    )
```

Claves **frecuentes** (para el significado completo de cada una y el formato en el JSON de respuesta, ver [info_frontend_automation_schema.md](./info_frontend_automation_schema.md) §2.2 y §2.3):

| Clave (ejemplo) | Para qué sirve, en una frase |
|-----------------|------------------------------|
| `columns_to_join` | Indica columnas relacionadas que el front puede ocultar o tratar como FK. |
| `join_from` | Indica de qué tabla/campo “viene” un valor mostrado. |
| `choices` | Lista de valores permitidos (enum en la UI). |
| `compare_primary_key` | Marca campos que forman la “clave lógica” de la fila además del `id`. |
| `min`, `max` | Límites numéricos orientativos (p. ej. validación o sliders). |

---

### 4.10. Resumen de ficheros (una línea cada uno)

**Comunes (en `cf_enterprise_poc`, no se modifican):**

| Fichero | Rol |
|---------|-----|
| `frontend_automation/frontend_automation.py` | Enum `EndpointTypes` + decorador `@automate_frontend`. |
| `frontend_automation/base_frontend_groups.py` | Clases base para sección, grupo y tabla de menú. |
| `frontend_automation/custom_marshmallow_plugin.py` | Hace visibles en OpenAPI los extras de Marshmallow. |
| `frontend_automation/apispec_tools.py` | Monta la spec y filtra por usuario/permisos. |
| `frontend_automation/__init__.py` | Reexporta `automate_frontend` y `EndpointTypes`. |
| `endpoints/frontend_automation.py` | Endpoint `GET` que reúne recursos y devuelve spec + `available_automations`. |

**Propios del proyecto (en la aplicación externa o el plugin):**

| Fichero / pieza | Rol |
|-----------------|-----|
| Declaraciones de secciones, grupos y tablas (p. ej. `frontend_groups.py`) | Subclases concretas del caso, heredando de las bases comunes. |
| Recursos REST (`*Endpoint`) y sus modelos con `__frontend_table__` | Métodos decorados con `@automate_frontend`; expuestos vía `endpoints.resources` o `get_resources()`. |
| Esquemas Marshmallow | Nombres de campo, traducciones y `metadata` propios del caso. |

---

## 5. Checklist de integración (orden práctico)

El endpoint común ya está disponible en `cf_enterprise_poc`; los pasos de integración se hacen **en el proyecto** (aplicación externa o plugin).

1. **Importar la capa común** — `from cf_enterprise_poc.frontend_automation import automate_frontend, EndpointTypes` y las clases base desde `cf_enterprise_poc.frontend_automation.base_frontend_groups`. No hay que copiar ni reimplementar nada.
2. **Menú por tabla** — Crear las clases concretas de sección, grupo y tabla del proyecto (§4.8) heredando de las bases comunes, y declarar `__frontend_table__` en el modelo correspondiente.
3. **Marcar cada operación** — Sobre cada método del recurso REST (`get`, `post`, …), aplicar `@automate_frontend` o el patrón imperativo descrito en §§4.5–4.7, con los esquemas exigidos por el tipo de operación (§4.4).
4. **Hacer visibles los recursos al endpoint común** — Exponer la lista `resources` del proyecto en `endpoints.resources` (aplicación externa, con `EXTERNAL_APP=1` y `EXTERNAL_APP_MODULE`) o devolverla desde `get_resources()` (plugin). Ver §4.2.1.
5. **Permisos** — Asegurar que existe la **vista** de permisos alineada con la URL de cada recurso de tabla; sin ella un usuario puede recibir **ninguna** operación en `paths` aunque el recurso exista.
6. **Opcional: `metadata` en Marshmallow** — §4.9 y el documento de esquema para el detalle del JSON.
7. **Probar** — `GET /frontend-automation/` debe responder 200; en `available_automations["tables"]` debe aparecer el `__tablename__` esperado con las claves de acción (`get_list`, …).

---

## 6. Referencia rápida

### 6.1. Valores de `EndpointTypes` (cadenas en el JSON de automatización)

`get_list`, `get_item`, `post_item`, `patch_item`, `put_item`, `delete_item`, `delete_all`, `post_bulk`, `post_update_bulk`, `delete_bulk`, `overwrite_all`, `restore_all`, `download_excel_table`, `async_post_bulk`, `async_post_update_bulk`, `async_overwrite_all`, `async_upload_status`.

Según el miembro de `EndpointTypes` elegido, el decorador exige documentación de **respuesta** y/o de **petición** en los términos descritos en §4.4; no es necesario modificar el código del enum.

### 6.2. Claves en `available_automations["tables"][tablename]`

Además de `title`, `icon`, `section`, `group`, `schemas`, `model_table_name`, `order`, por cada operación habilitada: clave = valor del enum (p. ej. `get_list`) → objeto `{ "url": "...", "http_method": "GET" }`. El campo `schemas` es una lista de DAGs asociados o `null` si la tabla no está restringida a ningún schema concreto.

### 6.3. Convención de nombres en diccionarios

* **`tables`**: clave = `__tablename__` del modelo.
* **`groups`** / **`sections`**: clave = atributo de clase **`name`**.

---

## 7. Extensiones y límites conocidos

* **Permisos**: la spec es **por usuario**. En `paths` solo figuran operaciones (URL + método HTTP) autorizadas para quien realiza la petición; las rutas que quedan sin ningún método permitido se eliminan del JSON. En `available_automations`, las acciones listadas por tabla siguen la misma lógica (no se publican enlaces a operaciones no permitidas).
* **Filtrado por schema**: las tablas que declaran un atributo `schemas` (lista de DAGs) se incluyen en la respuesta **solo** si el usuario tiene permiso sobre al menos uno de esos schemas. El parámetro `?schema=X` permite restringir la respuesta a un schema concreto (con validación de permiso: 403 si no está autorizado). Las tablas con `schemas = None` no están sujetas a este filtrado y se incluyen siempre.
* **Duplicados**: dos métodos que registren el mismo `endpoint_type` para la misma tabla: se conserva el primero y se emite **warning** en log.
* **Un solo `@automate_frontend` por función**: el decorador no está pensado para apilar múltiples automatizaciones en el mismo handler.
* **Descubrimiento de recursos**: el endpoint común documenta los recursos propios de enterprise, los de la aplicación externa (`EXTERNAL_APP`) y los de los plugins que implementen `get_resources()`. Un recurso del proyecto que no se exponga por ninguna de esas vías **no aparecerá** en la respuesta, aunque sus métodos estén decorados.
* **Capa común inmutable desde el proyecto**: la lógica de permisos y de generación de OpenAPI (`CornflowUIApiSpec` y su conversor) vive en `cf_enterprise_poc` y la comparten todos los proyectos. Cualquier cambio en esa lógica se hace **una sola vez** en cornflow_enterprise, no por proyecto.

---

## 8. Pruebas y depuración

* En el repositorio de referencia existen pruebas unitarias sobre el decorador, `available_automations` y agrupación de menús (buscar `test_frontend_automation` en los tests del paquete).
* Si faltan esquemas obligatorios, `automate_frontend` **no** anota el método y escribe **warnings** en log (no rompe el endpoint de negocio).
* Comprobar logs por conflictos entre `icon` y `frontend_group`, o tabla con `frontend_group` y `frontend_section` a la vez (`BaseFrontendTable`).

---

## 9. Documentación relacionada

| Documento | Contenido |
|-----------|------------|
| [info_frontend_automation_schema.md](./info_frontend_automation_schema.md) | Contrato de respuesta para consumidores del JSON (front, herramientas). |
| Código común | `cf_enterprise_poc/frontend_automation/` (decorador, enum, clases base, generación de OpenAPI, plugin de Marshmallow) y `cf_enterprise_poc/endpoints/frontend_automation.py` (recurso `GET` agregador). |
| Código de proyecto | En la aplicación externa o el plugin: subclases de menú, recursos REST decorados y esquemas Marshmallow del caso. |

---

### Alcance del documento

La sección 4 distingue entre la **capa común** que vive en `cf_enterprise_poc` (endpoint, decorador `automate_frontend`, enum `EndpointTypes`, clases base, generación de OpenAPI y permisos) y la **configuración propia del proyecto** que se declara en la aplicación externa o el plugin (subclases de menú, recursos REST, y esquemas Marshmallow con nombres de campo, traducciones y `metadata`). El detalle exhaustivo del JSON de respuesta permanece centralizado en [info_frontend_automation_schema.md](./info_frontend_automation_schema.md).
