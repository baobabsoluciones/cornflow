# CUSTOM_ROLES_ACTIONS - Configuración de Acciones para Roles Personalizados

## Descripción

La funcionalidad `CUSTOM_ROLES_ACTIONS` permite definir de manera granular qué acciones pueden ejecutar los roles personalizados (custom roles) en los endpoints de una external app en Cornflow.

## Problema que Resuelve

Anteriormente, todos los roles personalizados solo recibían permisos de `GET_ACTION` por defecto. Con esta nueva funcionalidad, cada rol personalizado puede tener acciones específicas definidas según las necesidades del negocio.

## Configuración

### 1. Definir la Constante en la External App

En el archivo `shared/const.py` de tu external app, define la constante `CUSTOM_ROLES_ACTIONS`:

```python
from cornflow.shared.const import GET_ACTION, POST_ACTION, PUT_ACTION, PATCH_ACTION, DELETE_ACTION

# Diccionario que mapea cada rol personalizado a sus acciones permitidas
CUSTOM_ROLES_ACTIONS = {
    # Rol de producción - puede leer, crear y actualizar
    888: [GET_ACTION, POST_ACTION, PUT_ACTION],
    # Rol de calidad - puede leer y modificar parcialmente           
    777: [GET_ACTION, PATCH_ACTION],
    # Rol de solo lectura                      
    999: [GET_ACTION],
    # Rol administrador personalizado
    1001: [GET_ACTION, POST_ACTION, PUT_ACTION, DELETE_ACTION],  
}
```

### 2. Usar los Roles en los Endpoints

En tus endpoints, define qué roles tienen acceso usando `ROLES_WITH_ACCESS`:

```python
class ProductionPlanningResource(BaseInstanceResource):
    # Rol personalizado 888 + rol estándar
    ROLES_WITH_ACCESS = [888, PLANNER_ROLE]  
    DESCRIPTION = "Endpoint para planificación de producción"
    
    # ... resto de la implementación

class QualityControlResource(BaseInstanceResource):
    # Rol personalizado 777 + rol estándar
    ROLES_WITH_ACCESS = [777, VIEWER_ROLE]   
    DESCRIPTION = "Endpoint para control de calidad"
    
    # ... resto de la implementación
```

### 3. Estructura Completa de la External App

```
external_app/
├── shared/
│   └── const.py              # Contiene CUSTOM_ROLES_ACTIONS
├── endpoints/
│   ├── __init__.py
│   └── resources.py          # Define los endpoints con ROLES_WITH_ACCESS
└── __init__.py
```

## Ejemplo Completo

### `external_app/shared/const.py`

```python
from cornflow.shared.const import GET_ACTION, POST_ACTION, PUT_ACTION, PATCH_ACTION, DELETE_ACTION

# Permisos adicionales específicos por endpoint
EXTRA_PERMISSION_ASSIGNATION = [
    # Permiso específico adicional
    (888, DELETE_ACTION, "production_planning"),  
]

# Acciones por defecto para roles personalizados
CUSTOM_ROLES_ACTIONS = {
    # Rol de producción
    888: [GET_ACTION, POST_ACTION, PUT_ACTION],    
    # Rol de calidad
    777: [GET_ACTION, PATCH_ACTION],               
    # Rol de consulta
    999: [GET_ACTION],                             
}
```

### `external_app/endpoints/resources.py`

```python
from cornflow.endpoints import BaseInstanceResource
from cornflow.shared.const import PLANNER_ROLE, VIEWER_ROLE

class ProductionPlanningResource(BaseInstanceResource):
    ROLES_WITH_ACCESS = [888, PLANNER_ROLE]
    DESCRIPTION = "Production planning endpoint"

class QualityControlResource(BaseInstanceResource):
    ROLES_WITH_ACCESS = [777, VIEWER_ROLE] 
    DESCRIPTION = "Quality control endpoint"

class ReportsResource(BaseInstanceResource):
    ROLES_WITH_ACCESS = [999, 888, 777, VIEWER_ROLE]
    DESCRIPTION = "Reports endpoint - accessible by multiple roles"

# Lista de recursos para exportar
resources = [
    {
        "endpoint": "production_planning",
        "urls": "/production-planning/",
        "resource": ProductionPlanningResource,
    },
    {
        "endpoint": "quality_control", 
        "urls": "/quality-control/",
        "resource": QualityControlResource,
    },
    {
        "endpoint": "reports",
        "urls": "/reports/",
        "resource": ReportsResource,
    },
]
```

## Validaciones y Errores

### Error por Rol No Definido

Si un rol personalizado se usa en `ROLES_WITH_ACCESS` pero no está definido en `CUSTOM_ROLES_ACTIONS`, se levantará un `ValueError`:

```
ValueError: The following custom roles are used in code but not defined in CUSTOM_ROLES_ACTIONS: {888}. 
Please define their allowed actions in the CUSTOM_ROLES_ACTIONS dictionary in shared/const.py.
```

### Ejemplo de Error

```python
# ❌ INCORRECTO - Rol 888 usado pero no definido
CUSTOM_ROLES_ACTIONS = {
    # Solo se define 777
    777: [GET_ACTION, PATCH_ACTION],  
}

# En endpoints se usa rol 888 -> ERROR
class ProductionResource(BaseInstanceResource):
    # 888 no está definido en CUSTOM_ROLES_ACTIONS
    ROLES_WITH_ACCESS = [888, PLANNER_ROLE]  
```

### Solución

```python
# ✅ CORRECTO - Todos los roles están definidos
CUSTOM_ROLES_ACTIONS = {
    777: [GET_ACTION, PATCH_ACTION],
    # Ahora 888 está definido
    888: [GET_ACTION, POST_ACTION, PUT_ACTION],  
}
```

## Compatibilidad hacia Atrás

- Si una external app no define `CUSTOM_ROLES_ACTIONS`, la funcionalidad sigue trabajando normalmente
- Los roles estándar (`VIEWER_ROLE`, `PLANNER_ROLE`, `ADMIN_ROLE`, `SERVICE_ROLE`) no se ven afectados
- Solo se requiere definir `CUSTOM_ROLES_ACTIONS` si se usan roles personalizados

## Acciones Disponibles

Las acciones disponibles que puedes usar en `CUSTOM_ROLES_ACTIONS` son:

```python
# Lectura (GET)
GET_ACTION = 1      
# Actualización parcial (PATCH)
PATCH_ACTION = 2    
# Creación (POST)
POST_ACTION = 3     
# Actualización completa (PUT)
PUT_ACTION = 4      
# Eliminación (DELETE)
DELETE_ACTION = 5   
```

## Testing

Para probar tu configuración, puedes usar los tests unitarios como referencia:

```python
def test_custom_roles_actions():
    # Mock de la configuración
    mock_const.CUSTOM_ROLES_ACTIONS = {
        888: [GET_ACTION, POST_ACTION, PUT_ACTION],
        777: [GET_ACTION, PATCH_ACTION],
    }
    
    # Ejecutar inicialización de permisos
    access_init_command(verbose=True)
    
    # Verificar que los permisos se crearon correctamente
    permissions_888 = PermissionViewRoleModel.query.filter_by(role_id=888).all()
    actions_888 = {perm.action_id for perm in permissions_888}
    
    assert GET_ACTION in actions_888
    assert POST_ACTION in actions_888
    assert PUT_ACTION in actions_888
``` 