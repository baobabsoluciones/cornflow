
# Estructura de `frontend_automation`

Este documento describe cómo se organiza la información dentro del fichero `frontend_automation`.

La estructura sigue el estándar **OpenAPI** y se compone de tres bloques principales:

```
frontend_automation
│
├── available_automations
    ├── sections
    ├── groups
    ├── tables
├── definitions
└── paths
```

---

# 1. available_automations

Este bloque describe cómo se organizan las entidades en el frontend.

No define lógica de negocio ni estructura de datos, sino organización visual y funcional.

---

## 1.1. sections

Las **sections** son agrupaciones visuales de alto nivel.

Cada sección contiene:

* `icon` → Icono representativo
* `title` → Nombre visible

  * Puede ser:

    * Un `string`
    * Un diccionario de traducciones:

      ```json
      {
        "es": "Nombre",
        "en": "Name"
      }
      ```

* `order` → Entero (`0` por defecto si no se define). Orden de presentación de la sección respecto a otras secciones (menor suele mostrarse antes).

Las secciones organizan visualmente el frontend.

---

## 1.2 groups

Los **groups** son agrupaciones funcionales intermedias.

Cada grupo:

* Tiene `title` (igual que en sections, puede ser string o diccionario de traducciones)
* Puede pertenecer a una `section`
* Puede tener `icon`
* `order` → Entero (`0` por defecto si no se define). Orden de presentación del grupo respecto a otros grupos (p. ej. dentro de la misma sección).

Reglas:

* Si pertenece a una `section` → no tiene icono propio.
* Si no pertenece a ninguna `section` → debe tener `icon`.

Sirven para agrupar tablas relacionadas.

---

## 1.3 tables

Las **tables** representan entidades gestionadas vía API.

Cada tabla:

* Tiene `title` (string o diccionario de traducciones)
* Puede pertenecer a una `section`
* Puede pertenecer a un `group`
* Si pertenece a una `section` o `group` → **no tiene icono propio**
* Si no pertenece a ninguno → debe tener `icon`
* `order` → Entero (`0` por defecto si no se define). Orden de presentación de la tabla respecto a otras tablas del mismo agrupamiento (misma sección o mismo grupo).
* Nunca se asocian a ambos (section y group) a la vez, ya que si 
pertenecen a un grupo, ya están dentro de la sección a la que ese 
grupo pertenece (si es que el grupo pertenece a una sección)

Cada tabla se conecta con:

* Una definición en `definitions`
* Un conjunto de endpoints en `paths`
* Un conjunto de operaciones permitidas

---

### 1.3.1 Operaciones permitidas

Cada tabla puede habilitar un subconjunto de las siguientes operaciones estándar:

---

#### 🔹 GET_LIST (`get_list`)

* Obtiene todos los registros.
* No acepta parámetros. Puede aceptar query params para filtros, paginación, etc.
* Devuelve lista de items.
* Código: **200**

---

#### 🔹 GET_ITEM (`get_item`)

* Obtiene un registro por ID.
* Recibe ID como parámetro. 
* Devuelve un item.
* Código: **200**

---

#### 🔹 POST_ITEM (`post_item`)

* Crea un nuevo registro.
* Recibe datos en el body (sin ID).
* Devuelve el item creado.
* Código: **201**

---

#### 🔹 PATCH_ITEM (`patch_item`)

* Actualiza parcialmente un registro.
* Recibe ID + datos parciales.
* Devuelve solo mensaje.
* Código: **200**

---

#### 🔹 PUT_ITEM (`put_item`)

* Reemplaza completamente un registro.
* Recibe ID + objeto completo.
* Devuelve el item actualizado.
* Código: **200**

---

#### 🔹 DELETE_ITEM (`delete_item`)

* Elimina un registro por ID.
* Devuelve solo mensaje.
* Código: **200**

---

#### 🔹 DELETE_ALL (`delete_all`)

* Elimina todos los registros.
* No acepta parámetros.
* Devuelve solo mensaje.
* Código: **200**

---

#### 🔹 POST_BULK (`post_bulk`)

* Crea múltiples registros.
* Recibe lista de objetos (sin IDs).
* Operación atómica:

  * Si hay error → no se crea ninguno.
* Devuelve mensaje.
* Código: **201** o **200**

---

#### 🔹 POST_UPDATE_BULK (`post_update_bulk`)

* Actualiza múltiples registros.
* Recibe lista de objetos (sin IDs)
* Si existe un registro con los mismos campos únicos, se actualiza. 
Si no existe, se crea. 
* Operación atómica:
  * Si hay error → no se actualiza ninguno.
* Devuelve mensaje.
* Código: **201** o **200**

---

#### 🔹 DELETE_BULK (`delete_bulk`)

* Elimina múltiples registros.
* Recibe:

  ```json
  { "ids": [1, 2, 3] }
  ```
* Operación atómica.
* Devuelve mensaje.
* Código: **200**

---

#### 🔹 OVERWRITE_ALL (`overwrite_all`)

* Reemplaza completamente todos los registros.
* Recibe lista de objetos (sin IDs).
* Operación atómica:

  * Si hay error → no crea ni elimina nada.
* Devuelve mensaje.
* Código: **200**

---

#### 🔹 RESTORE_ALL (`restore_all`)

* Elimina todos los registros activos.
* Restaura todos los previamente eliminados.
* No acepta parámetros.
* Operación atómica.
* Devuelve mensaje.
* Código: **200**

---

#### 🔹 DOWNLOAD_EXCEL_TABLE (`download_excel_table`)

* Descarga la tabla como fichero **Excel**.
* No exige parámetros en el path; puede aceptar **query params** de filtrado alineados con el listado (`get_list`), salvo que la implementación excluya explícitamente algunos (p. ej. `limit` / `offset` según el endpoint).
* Devuelve el binario Excel.
* Código: **200**

---

#### 🔹 ASYNC_POST_BULK (`async_post_bulk`)

* Crea múltiples registros de forma **asíncrona** lanzando un job de Airflow.
* Recibe un **Excel sin procesar**.
* Devuelve un `upload_id` y un `status` (string).
* Código: **202**

---

#### 🔹 ASYNC_POST_UPDATE_BULK (`async_post_update_bulk`)

* Actualiza múltiples registros de forma **asíncrona** lanzando un job de Airflow.
* Recibe un **Excel sin procesar**.
* Devuelve un `upload_id` y un `status` (string).
* Código: **202**

---

#### 🔹 ASYNC_OVERWRITE_ALL (`async_overwrite_all`)

* Sobrescribe todos los registros de forma **asíncrona** lanzando un job de Airflow.
* Recibe un **Excel sin procesar**.
* Devuelve un `upload_id` y un `status` (string).
* Código: **202**

---

#### 🔹 ASYNC_UPLOAD_STATUS (`async_upload_status`)

* Consulta el estado de una carga asíncrona.
* Recibe un `upload_id` en la URL.
* Devuelve un JSON con:
  * `status` (string): estado actual de la carga.
  * `total_rows_loaded` (integer): número de filas cargadas.
  * `error_message` (string, opcional): mensaje de error en caso de fallo.
* Código: **200**

---

# 2. definitions

El bloque `definitions` define los **modelos de datos** utilizados por la API.

Cada definición describe la estructura de un objeto usando formato OpenAPI / JSON Schema.

---

## 2.1 Formato general de una definición

Una definición típica tiene esta estructura:

```json
"ExampleEntity": {
  "type": "object",
  "required": ["field_a", "field_b"],
  "properties": {
    "id": {
      "type": "integer",
    },
    "field_a": {
      "type": "string",
      "title": {
        "es": "Campo A",
        "en": "Field A"
      }
    },
    "field_b": {
      "type": "string",
      "title": "Field B",
      "choices": ["option1", "option2", "option3"]
    },
    "field_c": {
      "type": "boolean",
      "nullable": true,
      "title": "Field C"
    },
    "field_d": {
        "type": "string",
        "format": "date-time",
        "title": "Field D"
    },
    "e_id": {
        "type": "integer",
        "title": "ID de E", 
        "columns_to_join": ["e_name"]
    },
    "e_name": {
        "type": "string",
        "title": "Nombre de E",
        "join_from": "TablaE.name",
        "readOnly": true
     }
  }
}
```

---

## 2.2 Elementos principales

Cada definición puede incluir:

### 🔹 type

Siempre es un `"object"`.

---

### 🔹 properties

Diccionario de campos.

Cada propiedad define:

* `type`:

  * `string`
  * `integer`
  * `number`
  * `boolean`
  * `array`
  * `object`
* `format` (opcional). Para los strings solamente:

  * `date`
  * `date-time`
  * `time`
  * `email`
  * `uuid`
  * `url`
* `title`: nombre legible del campo, como string o diccionario de traducciones.
* `nullable` o `x-nullable`: indica si el campo puede ser null.
* `readOnly`: indica que el campo puede ser devuelto por la API pero no enviado en el body.
* `writeOnly`: indica que el campo puede ser enviado en el body pero no devuelto por la API.
* `choices`: lista de opciones válidas (si el campo es un enum).
* `columns_to_join`: indica que el campo es una clave foreana a otra tabla (escondido en el frontend).
* `join_from`: indica que este campo viene de una tabla relacionada
* `compare_primary_key` (booleano): indica que el campo participa en la **clave primaria lógica** de la entidad a efectos de comparación o identificación de filas (p. ej. en vistas por instancia o al emparejar registros).
* `min` y `max` (número): **límite inferior y superior inclusivos** orientativos para la UI.
* `items` (si es array)
* `$ref` (si referencia otra definición)

---

### 🔹 required

Lista de campos obligatorios.

---

### 🔹 Referencias

Las definiciones pueden reutilizar otras mediante:

```json
"$ref": "#/definitions/AnotherDefinition"
```

---

# 3. paths

El bloque `paths` define los endpoints REST asociados a cada tabla.

Estructura general abstracta:

```
/entities/
/entities/{id}/
/entities/bulk/
/entities/overwrite/
/entities/restore/
```

Cada path:

* Define método HTTP (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`)
* Puede tener:

  * `parameters`
  * `responses`
  * `schema` con `$ref` a `definitions`
* Suele estar etiquetado con un `tag` común (por ejemplo: `"Table"`)

---

# 3.1. Parameters

Los endpoints pueden aceptar parámetros:
* En la URL (`path` parameters)
* En la query (`query` parameters)
* En el body (`body` parameters)

###  🔹 Path parameters
Los parámetros aceptados en el path suelen ser:
* `id` → para operaciones sobre un item específico

Los parámetros de path se definen con los siguientes atributos:
* `name`: nombre del parámetro (ej: "id")
* `in`: ubicación del parámetro. Siempre valdrá "path" para los path parameters.
* `required`: indica si el parámetro es obligatorio. Para los path parameters, siempre será `true`.
* `type`: tipo de dato del parámetro (ej: "integer", "string", etc.)

---

### 🔹 Query parameters

Los parámetros aceptados en la query pueden ser variados, dependiendo de la operación. Algunos ejemplos comunes son:
* `force`: para operaciones de eliminación que requieren confirmación
* Diferentes filtros para operaciones de listado

Los parámetros de query se definen con los siguientes atributos:
* `name`: nombre del parámetro (ej: "force")
* `in`: ubicación del parámetro. Siempre valdrá "query" para los query parameters.
* `required`: indica si el parámetro es obligatorio o no.
* `type`: tipo de dato del parámetro (ej: "boolean", "string", etc.)
* Eventualmente, `format` para especificar formatos más concretos (ej: "date-time", "email", etc.). Este atributo es opcional y se utiliza solamente para parámetros de tipo string. Puede tomar los mismos valores que el atributo `format` de las propiedades en las definiciones.

Además, los parámetros de filtro tendrán algunas informaciones adicionales para que el frontend pueda construir la UI de filtros de forma automática:
* `is_filter`: booleano que indica que el parámetro es un filtro. Valdrá `true` para los parámetros que se utilizan como filtros en las operaciones de listado.
* `filter_info`: objeto que contiene información adicional sobre el filtro. Las informaciones que puede contener este objeto son:
  * `filters_on`: el nombre de la columna sobre la cual se aplica el filtro. Puede valer null para los casos en los que el filtro no se aplica directamente sobre una columna (ej: filtros de búsqueda global, limite, offset, etc.)
  * `filter_type`: el tipo de filtro. Puede tomar los siguientes valores:
    * `any_column_contains`: para filtros de búsqueda global sobre columnas strings, enteras, o floats, date-times, dates y times.
    * `string_startswith`: para filtros de texto que buscan coincidencias al inicio del campo.
    * `string_contains`: para filtros de texto que buscan coincidencias en cualquier parte del campo
    * `string_endswith`: para filtros de texto que buscan coincidencias al final del campo.
    * `string_eq`: para filtros de texto que buscan coincidencias exactas.
    * `string_not_eq`: para filtros de texto que buscan valores distintos al valor del filtro
    * `numeric_gt`: para filtros numéricos que buscan valores mayores al valor del filtro.
    * `numeric_gte`: para filtros numéricos que buscan valores mayores o iguales al valor del filtro.
    * `numeric_lt`: para filtros numéricos que buscan valores menores al valor del filtro
    * `numeric_lte`: para filtros numéricos que buscan valores menores o iguales al valor del filtro.
    * `numeric_eq`: para filtros numéricos que buscan valores iguales al valor del filtro.
    * `numeric_not_eq`: para filtros numéricos que buscan valores distintos al valor del filtro.
    * `boolean`: para filtros booleanos que buscan valores verdaderos o falsos.
    * `datetime_lte`: para filtros de fecha que buscan valores anteriores o iguales a la fecha del filtro.
    * `datetime_gte`: para filtros de fecha que buscan valores posteriores o iguales a la fecha del filtro.
    * `datetime_eq`: para filtros de fecha que buscan valores iguales a la fecha del filtro.
    * `datetime_not_eq`: para filtros de fecha que buscan valores distintos a la fecha del filtro.
    * `time_lte`: para filtros de hora que buscan valores anteriores o iguales a la hora del filtro.
    * `time_gte`: para filtros de hora que buscan valores posteriores o iguales a la hora del filtro.
    * `time_eq`: para filtros de hora que buscan valores iguales a la hora del filtro.
    * `time_not_eq`: para filtros de hora que buscan valores diferentes a la hora del filtro.
    * `value_is_none`: para filtros que buscan valores nulos
    * `value_is_not_none`: para filtros que buscan valores no nulos
    * `limit`: para filtros de límite de resultados. En este caso, el valor del filtro indicará el número máximo de resultados a devolver.
    * `offset`: para filtros de desplazamiento en la paginación. En este caso, el valor del filtro indicará el número de resultados a omitir antes de comenzar a devolver resultados.
  * `symmetric`: string que indica el nombre del filtro simétrico a este. Se utiliza para mostrar un mismo filtro de forma simétrica en la interfaz (ej: "Fecha desde" y "Fecha hasta" para filtros `datetime_gte` y `datetime_lte` sobre la misma columna). En caso de que el filtro no tenga un filtro simétrico, este atributo puede valer null o no estar presente.

El frontend se basará en los campos `type` y `format` de los parámetros para saber qué tipo acepta el parámetro, y utilizará la información adicional de `is_filter` y `filter_info` para determinar qué parámetros son filtros, cómo deben aplicarse sobre las columnas correspondientes, y con qué mensaje deben mostrarse en la interfaz.

---

### 🔹 Body parameters

Los parámetros aceptados en el body suelen ser objetos que siguen la estructura de las definiciones. Por ejemplo, para una operación `POST_ITEM` sobre una tabla `ExampleEntity`, el body parameter podría tener un schema con `$ref` a la definición `ExampleEntity`.

Estos parámetros se definen con los siguientes atributos:
* `name`: nombre del parámetro (ej: "body")
* `in`: ubicación del parámetro. Siempre valdrá "body" para los body parameters.
* `required`: indica si el parámetro es obligatorio o no.
* `schema`: objeto que define la estructura del body. Contiene un `$ref` a una definición.

# 3.2. Responses

Las respuestas de los endpoints se definen en el bloque `responses` de cada path. Generalmente, cada operación tendrá una respuesta con código `default`. Esta respuesta suele contener un schema con `$ref` a una definición que describe la estructura de la respuesta. Por ejemplo, para una operación `GET_LIST` sobre una tabla `ExampleEntity`, la respuesta podría tener un schema con `$ref` a una definición `ExampleEntityListResponse`, que a su vez contiene una propiedad `items` que es un array de objetos con `$ref` a `ExampleEntity`.

Ejemplo:

```json

"/example-entities/": {
  "get": {
    "tags": ["ExampleEntity"],
    "parameters": [
      {
        "name": "filter_a",
        "in": "query",
        "required": false,
        "type": "string",
        "is_filter": true,
        "filter_info": {
          "filters_on": "field_a",
          "filter_type": "string_contains"
        }
      },
      {
        "name": "limit",
        "in": "query",
        "required": false,
        "type": "integer",
        "is_filter": true,
        "filter_info": {
          "filter_type": "limit"
        }
      },
      {
        "name": "start_date_lte",
        "in": "query",
        "required": false,
        "type": "string",
        "format": "date-time",
        "is_filter": true,
        "filter_info": {
          "filters_on": "start_date",
          "filter_type": "datetime_lte",
          "symmetric": "start_date_gte"
        }
      },
      {
        "name": "start_date_gte",
        "in": "query",
        "required": false,
        "type": "string",
        "format": "date-time",
        "is_filter": true,
        "filter_info": {
          "filters_on": "start_date",
          "filter_type": "datetime_gte",
          "symmetric": "start_date_lte"
        }
      },
    ],
    "responses": {
      "default": {
        "schema": {
          "$ref": "#/definitions/ExampleEntityListResponse"
        }
      }
    }
  },
  "post": {
    "tags": ["ExampleEntity"],
    "parameters": [
      {
        "name": "body",
        "in": "body",
        "required": true,
        "schema": {
          "$ref": "#/definitions/ExampleEntity"
        }
      }
    ],
    "responses": {
      "default": {
        "schema": {
          "$ref": "#/definitions/ExampleEntity"
        }
      }
    }
  },
}
```




---

# Resumen conceptual

| Bloque                | Responsabilidad                             |
| --------------------- | ------------------------------------------- |
| available_automations | Organización visual y funcional en frontend |
| definitions           | Modelos de datos (OpenAPI / JSON Schema)    |
| paths                 | Endpoints REST y operaciones disponibles    |

---
