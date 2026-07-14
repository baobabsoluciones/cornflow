# Por qué Cornflow no arrancaba — explicado sin rollos

Dos problemas distintos, cada uno con su arreglo. Aquí van explicados como si no supieras nada de Airflow ni de Kubernetes.

---

## 1. El cambio en `is_alive` (por qué `cornflow-server` no levantaba)

### ¿Qué hace `is_alive`?

Cuando arranca `cornflow-server`, antes de ponerse a atender peticiones, hace una llamada a Airflow para preguntarle "¿estás despierto y funcionando bien?". Esa pregunta la hace un trocito de código llamado `is_alive()`, que vive en el paquete `cornflow_client` (el "traductor" que usa Cornflow para hablar con Airflow).

Para preguntarlo, `is_alive()` hace una petición HTTP a una dirección concreta de Airflow, algo como:

```
GET http://airflow:8080/api/v1/health
```

Y espera una respuesta con esta pinta:

```json
{
  "metadatabase": {"status": "healthy"},
  "scheduler": {"status": "healthy"}
}
```

Si ambos dicen "healthy", `is_alive()` responde que sí, Airflow está vivo, y Cornflow puede seguir arrancando.

### ¿Qué se rompió?

Airflow 3 (la versión nueva a la que hemos migrado) **eliminó esa dirección** `/api/v1/health`. Ya no existe. En su lugar, la nueva dirección es:

```
GET http://airflow:8080/api/v2/monitor/health
```

Cuando `is_alive()` preguntaba en la dirección vieja (`/api/v1/health`), Airflow 3 le contestaba "esa dirección no existe" (un error 404), y el código lo interpretaba como "Airflow no está vivo".

### ¿Por qué eso hacía que Cornflow no arrancara?

Porque cuando Cornflow cree que Airflow no está vivo, **no se rinde a la primera** — insiste. Concretamente, hay dos pasos del arranque de Cornflow (uno que actualiza los "esquemas" de los modelos y otro que actualiza el "registro" de DAGs) que, cada uno por su cuenta, reintentan la pregunta **20 veces, esperando 15 segundos entre intento e intento**. Eso son 5 minutos por cada paso — 10 minutos en total, solo insistiendo en una pregunta que nunca iba a tener respuesta positiva (porque preguntaba en la dirección equivocada).

Kubernetes, mientras tanto, tiene su propia paciencia limitada: si un contenedor no responde a tiempo, lo mata y lo vuelve a arrancar desde cero. Como Cornflow tardaba más de 10 minutos en esos reintentos inútiles, Kubernetes lo mataba antes de que llegara a arrancar el servidor web de verdad. Y al arrancar de nuevo, volvía a caer en el mismo bucle. Eso es lo que viste como "CrashLoopBackOff".

### ¿Cuál es el arreglo?

Un cambio pequeño y quirúrgico, solo dentro de `is_alive()`:

- Antes: preguntaba **solo** en la dirección vieja (`/api/v1/health`).
- Ahora: pregunta primero en la dirección vieja, y **si le dicen que no existe (404)**, pregunta automáticamente en la dirección nueva (`/api/v2/monitor/health`).

Así el mismo código funciona tanto contra Airflow 2 (otros proyectos del cluster que todavía no han migrado) como contra Airflow 3 (este proyecto), sin tener que saber de antemano qué versión hay al otro lado. No hemos tocado nada más del archivo — el resto de llamadas a Airflow (lanzar DAGs, leer variables, etc.) siguen usando la dirección vieja, porque no eran las que bloqueaban el arranque, y tocarlas todas de golpe es un cambio mucho más grande que haremos en otro momento.

**Importante:** este cambio está hecho en el código fuente (`cornflow/libs/client/...`), pero **todavía no está en el contenedor que corre en el cluster** — hace falta publicar una nueva versión del paquete `cornflow_client` y actualizar la versión que usa la imagen de Cornflow antes de que este arreglo llegue a producción. Eso es una decisión que toca gestionar aparte.

---

## 2. Qué le pasaba a `msc-ltf-dag-processor`

### El problema (ya resuelto antes de este documento)

El `dag-processor` es el componente de Airflow 3 que se encarga de leer los DAGs desde el repositorio de Git y prepararlos para que Airflow los pueda ejecutar. Para instalar las dependencias de Python que necesitan esos DAGs (paquetes como `ortools`, usado para los modelos de optimización), tiene un pasito extra que hace `pip install`.

### El problema encontrado ahora

Ese pasito usaba, por defecto, una imagen genérica de Airflow (`apache/airflow:3.2.2`, sin especificar versión de Python). Esa imagen genérica trae **Python 3.13**. Pero el paquete `ortools` (versión `9.8.3296`, la que necesita este proyecto) **todavía no tiene una versión compilada para Python 3.13** — solo hasta Python 3.12.

Resultado: cuando ese pasito intentaba instalar las dependencias, `pip`/`uv` decía "no hay ninguna combinación de paquetes que funcione" y se paraba con un error. Como ese error hacía fallar todo el contenedor, Kubernetes lo reiniciaba sin parar — más de 700 veces en 2 días.

### El arreglo

Cambiar qué imagen usa ese pasito: en vez de la imagen genérica (Python 3.13), que use la imagen propia del proyecto (`baobabsoluciones/airflow-k8s:release-1.3.6`), que está construida específicamente con **Python 3.12** — la misma que ya usan todos los demás componentes de Airflow en este despliegue. Con Python 3.12, `ortools` sí tiene una versión compilada disponible, así que la instalación funciona.

---

## En resumen

| Componente | Síntoma | Causa | Arreglo |
|---|---|---|---|
| `cornflow-server` | CrashLoopBackOff, nunca arranca | `is_alive()` preguntaba en una dirección de Airflow que ya no existe en la v3, y Cornflow insistía durante 10 minutos antes de rendirse | `is_alive()` ahora también prueba la dirección nueva si la vieja no existe |
| `msc-ltf-dag-processor` | CrashLoopBackOff, 700+ reinicios | El paso que instala dependencias de los DAGs usaba una imagen con Python 3.13, y `ortools` no tiene versión para esa versión de Python | Usar la imagen propia del proyecto (Python 3.12) para ese paso |
