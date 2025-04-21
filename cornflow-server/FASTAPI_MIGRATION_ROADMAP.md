# Cornflow FastAPI Migration Roadmap

## Overview

This document outlines the strategy for migrating the Cornflow REST API from Flask to FastAPI while maintaining all core functionalities and ensuring backward compatibility.

## Core Functionalities to Preserve

1. Automatic database migrations (Alembic)
2. Request data validation (Pydantic)
3. Response data validation (Pydantic)
4. Authentication (JWT/OAuth)
5. Python package deployment
6. CLI functionality
7. API extensibility

## Current Models and Endpoints

### Models

1. **User Management**

   - `UserModel`: User accounts and authentication
   - `RoleModel`: User roles and permissions
   - `UserRoleModel`: User-role assignments
   - `ActionModel`: API actions (GET, POST, PUT, DELETE)
   - `ViewModel`: API views/endpoints
   - `PermissionViewRoleModel`: Role-based permissions

2. **Data Models**

   - `BaseDataModel`: Abstract base model with common fields
   - `InstanceModel`: Problem instances
   - `ExecutionModel`: Solution executions
   - `CaseModel`: Case management
   - `DeployedDAG`: DAG deployment registry

3. **Monitoring**
   - `AlarmsModel`: System alarms
   - `MainAlarmsModel`: Main alarm events

### Endpoints

1. **Authentication & Authorization**

   - `/login`: User authentication
   - `/signup`: User registration
   - `/token`: Token management
   - `/user`: User management
   - `/user_role`: User role management
   - `/roles`: Role management
   - `/permission`: Permission management
   - `/apiview`: API view management
   - `/action`: Action management

2. **Data Management**

   - `/instance`: Instance CRUD operations
   - `/execution`: Execution management
   - `/case`: Case management
   - `/dag`: DAG deployment and management
   - `/data_check`: Data validation
   - `/example_data`: Example data management

3. **System**
   - `/health`: System health checks
   - `/alarms`: Alarm management
   - `/main_alarms`: Main alarm management
   - `/licenses`: License management
   - `/tables`: Table management
   - `/meta_resource`: Meta resource management
   - `/schemas`: Schema management

## Phase 1: Project Structure Setup

- [x] Create `cornflow_fastapi` directory
- [x] Set up basic FastAPI application structure
- [x] Configure development environment
- [x] Set up testing infrastructure

### Directory Structure

```
cornflow_f/
├── alembic/
│   └── versions/
├── tests/
│   ├── data/
│   ├── unit/
│   └── conftest.py
├── views/
│   ├── health.py
│   ├── users.py
│   └── __init__.py
├── models/
│   ├── user.py
│   └── __init__.py
├── schemas/
│   ├── user.py
│   └── __init__.py
├── alembic.ini
├── database.py
├── main.py
├── models.py
├── schemas.py
├── security.py
└── README.md
```

## Phase 2: Core Infrastructure Migration

- [x] Database Configuration

  - [x] Migrate SQLAlchemy setup
  - [x] Configure Alembic for migrations
  - [x] Set up database session management

- [ ] Authentication System

  - [x] Basic user model and schemas
  - [ ] Implement JWT authentication
  - [ ] Set up OAuth integration
  - [ ] Migrate user management

- [ ] Data Validation
  - [x] Basic Pydantic schemas
  - [ ] Convert remaining Marshmallow schemas
  - [ ] Implement request/response models
  - [ ] Set up validation middleware

## Phase 3: API Endpoints Migration

- [ ] Authentication & Authorization Endpoints

  - [x] Basic user signup
  - [ ] User management
  - [ ] Authentication
  - [ ] Permissions
  - [ ] Roles
  - [ ] User roles

- [ ] Data Management Endpoints

  - [ ] Instance management
  - [ ] Execution management
  - [ ] Case management
  - [ ] DAG management
  - [ ] Data validation
  - [ ] Example data

- [ ] System Endpoints
  - [x] Basic health checks
  - [ ] Alarm management
  - [ ] License management
  - [ ] Table management
  - [ ] Meta resources
  - [ ] Schema management

## Phase 4: CLI and Package Management

- [ ] CLI Migration

  - [ ] User management commands
  - [ ] Migration commands
  - [ ] Service management

- [ ] Package Configuration
  - [ ] Update setup.py
  - [ ] Configure dependencies
  - [ ] Set up entry points

## Phase 5: Testing Strategy

- [ ] Unit Tests

  - [ ] Model tests
  - [ ] Service tests
  - [ ] API endpoint tests

- [ ] Integration Tests

  - [ ] Database integration
  - [ ] Authentication flow
  - [ ] API workflow

- [ ] Performance Tests
  - [ ] Load testing
  - [ ] Response time benchmarks

## Phase 6: Documentation and Deployment

- [ ] API Documentation

  - [ ] OpenAPI/Swagger setup
  - [ ] API documentation
  - [ ] Usage examples

- [ ] Deployment
  - [ ] Docker configuration
  - [ ] CI/CD pipeline
  - [ ] Production deployment guide

## Migration Strategy

1. **Parallel Development**: Maintain both Flask and FastAPI versions during migration
2. **Incremental Migration**: Migrate one endpoint at a time, ensuring tests pass
3. **Feature Parity**: Ensure all existing features work before adding new ones
4. **Backward Compatibility**: Maintain API compatibility where possible

## Testing Approach

1. **Test-First Development**: Write tests before implementing features
2. **Continuous Integration**: Run tests on every commit
3. **Feature Comparison**: Compare behavior between Flask and FastAPI versions
4. **Performance Benchmarking**: Compare response times and resource usage

## Dependencies to Add

```txt
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.4.2
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
```

## Next Steps

1. Complete the authentication system implementation
2. Begin migrating the data management endpoints
3. Implement the remaining user management features
4. Set up comprehensive testing infrastructure
