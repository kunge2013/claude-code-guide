# Technology Mapping Reference

This document provides a comprehensive reference of common technologies, their typical use cases, problems they solve, and alternatives. Use this when analyzing projects to understand why specific technologies were chosen.

## Backend Languages & Frameworks

### Python

**Typical Use Cases**: Web APIs, Data Science, Machine Learning, Scripting, Automation

**Business Problems Solved**:
- Rapid development and prototyping
- Easy to read and maintain codebase
- Rich ecosystem for data processing and AI/ML

**Technical Problems Solved**:
- Quick iteration on business features
- Extensive library availability reduces custom code
- Good integration with C/C++ for performance-critical sections

**Alternatives Not Chosen**: JavaScript/Node.js (better for real-time), Java (better for enterprise scale), Go (better for concurrency)

**Common Frameworks**:
- **FastAPI**: Modern async API development, automatic API docs, type hints
- **Django**: Full-featured framework with ORM, admin panel, authentication built-in
- **Flask**: Microframework for simple services and APIs

### Java / Spring Boot

**Typical Use Cases**: Enterprise applications, Microservices, High-throughput systems

**Business Problems Solved**:
- Enterprise-grade reliability and stability
- Large talent pool for enterprise hiring
- Strong typing reduces production bugs

**Technical Problems Solved**:
- Excellent multithreading and concurrency
- Mature ecosystem with battle-tested libraries
- Strong backward compatibility

**Alternatives Not Chosen**: Go (simpler, faster startup), Python (faster development)

### Node.js / TypeScript

**Typical Use Cases**: Real-time applications, Microservices, Full-stack JavaScript

**Business Problems Solved**:
- Single language across frontend/backend reduces context switching
- Real-time features (websockets, chat, notifications)
- Fast development cycle

**Technical Problems Solved**:
- Event-driven, non-blocking I/O for high concurrency
- NPM ecosystem with huge package availability
- TypeScript adds type safety to JavaScript

**Alternatives Not Chosen**: Python (better for CPU-intensive tasks), Go (better performance)

### Go

**Typical Use Cases**: Microservices, CLI tools, Cloud-native applications, High-performance services

**Business Problems Solved**:
- Fast compilation and deployment
- Single binary deployment simplifies operations
- Good performance with low resource usage

**Technical Problems Solved**:
- Excellent concurrency with goroutines
- Fast startup time (good for serverless)
- Strong standard library reduces dependencies

**Alternatives Not Chosen**: Java (heavier), Python (slower), Rust (steeper learning curve)

## Web Frameworks

### FastAPI (Python)

**Problems Solved**:
- Automatic OpenAPI documentation generation
- Request validation with Pydantic
- Async support for better performance
- Type hints improve IDE support

**Alternatives**: Flask (lighter, less opinionated), Django (more batteries included)

### Django (Python)

**Problems Solved**:
- Rapid development with admin panel built-in
- ORM eliminates most SQL writing
- Built-in authentication, forms, routing
- MTV architecture pattern enforcement

**Alternatives**: Flask (more flexibility), FastAPI (modern async), Ruby on Rails (similar philosophy)

### Spring Boot (Java)

**Problems Solved**:
- Convention over configuration reduces setup
- Embedded server for simplified deployment
- Production-ready metrics, health checks
- Extensive ecosystem for enterprise needs

**Alternatives**: Micronaut (faster startup), Quarkus (native compilation)

### Express.js (Node.js)

**Problems Solved**:
- Minimal and unopinionated
- Huge middleware ecosystem
- Full-stack JavaScript synergy
- Good for REST APIs and microservices

**Alternatives**: Koa (more modern), Fastify (better performance)

## Databases

### PostgreSQL

**Typical Use Cases**: Relational data, Complex queries, ACID requirements, JSON storage needs

**Business Problems Solved**:
- Data integrity and consistency
- Complex relationships between entities
- Regulatory compliance requiring transactions

**Technical Problems Solved**:
- Advanced SQL capabilities (CTEs, window functions)
- JSONB for semi-structured data
- Extension ecosystem (PostGIS, pgvector)
- Excellent replication and high availability

**Alternatives Not Chosen**: MySQL (less advanced features), MongoDB (no ACID before v4)

### MySQL

**Typical Use Cases**: Web applications, Read-heavy workloads, Simple relational data

**Problems Solved**:
- Proven reliability at scale
- Easy to find expertise
- Good read performance with MyRocks/Aria

**Alternatives**: PostgreSQL (more features), MariaDB (more open)

### MongoDB

**Typical Use Cases**: Document storage, Flexible schemas, Real-time analytics, Content management

**Business Problems Solved**:
- Flexible schema for evolving data models
- Fast iteration on product features
- Good for unstructured/semi-structured data

**Technical Problems Solved**:
- Horizontal scaling with sharding
- Document model maps well to objects in code
- Aggregation pipeline for analytics

**Alternatives**: PostgreSQL (with JSONB), CouchDB (multi-master), DynamoDB (managed)

### Redis

**Typical Use Cases**: Caching, Session storage, Rate limiting, Pub/Sub, Leaderboards

**Business Problems Solved**:
- Improve response times for hot data
- Reduce load on primary database
- Enable real-time features

**Technical Problems Solved**:
- In-memory operations are extremely fast
- Rich data structures (sets, sorted sets, hashes)
- Pub/Sub for messaging
- Distributed locking

**Alternatives**: Memcached (simpler, just caching), Hazelcast (distributed computing)

## Message Queues

### RabbitMQ

**Typical Use Cases**: Task queues, Message routing, Reliable delivery, Complex routing needs

**Business Problems Solved**:
- Asynchronous processing for better UX
- Service decoupling
- Reliable message delivery

**Technical Problems Solved**:
- Flexible routing with exchanges
- Message acknowledgments and retries
- Multiple messaging protocols (AMQP, MQTT, STOMP)
- Management UI for monitoring

**Alternatives**: Redis (simpler, less reliable), Kafka (better for streaming)

### Apache Kafka

**Typical Use Cases**: Event streaming, Log aggregation, Real-time analytics, Microservices communication

**Business Problems Solved**:
- Event-driven architecture
- Real-time data pipelines
- Audit log and event sourcing

**Technical Problems Solved**:
- High throughput (millions of messages/sec)
- Message replay capability
- Distributed architecture
- Exactly-once semantics

**Alternatives**: RabbitMQ (simpler, traditional messaging), Pulsar (more features)

### Redis (as Message Queue)

**Typical Use Cases**: Simple pub/sub, Lightweight task queues, Real-time notifications

**Problems Solved**:
- Very fast, in-memory messaging
- Simple to set up and use
- Already running for caching

**Trade-offs**: Less reliable than RabbitMQ, message loss on restart

## ORM / Database Access

### SQLAlchemy (Python)

**Problems Solved**:
- Database-agnostic query building
- Pythonic API instead of raw SQL
- Relationship mapping (foreign keys become objects)
- Migration support with Alembic

**Alternatives**: Django ORM (tightly coupled to Django), Tortoise ORM (async)

### Prisma (TypeScript/Node.js)

**Problems Solved**:
- Type-safe database access
- Auto-generated types from schema
- Great developer experience
- Multiple database support

**Alternatives**: TypeORM (more traditional), Sequelize (mature but verbose)

### Hibernate (Java)

**Problems Solved**:
- JPA standard implementation
- Caching (first and second level)
- Automatic dirty checking
- Complex relationship mapping

**Alternatives**: MyBatis (more SQL control), jOOQ (type-safe SQL builder)

## Caching

### Redis (Cache)

**Problems Solved**:
- Sub-millisecond read latency
- Reduced database load
- Session storage
- Query result caching
- Distributed locking

**Typical Patterns**:
- Cache-aside (lazy loading)
- Write-through (write to cache and DB)
- Write-back (write to cache, async to DB)

### Memcached

**Problems Solved**:
- Simple, fast object caching
- Multi-threaded architecture
- LRU eviction

**When to use over Redis**: Simple caching needs, already have infrastructure

## Authentication & Authorization

### JWT (JSON Web Tokens)

**Problems Solved**:
- Stateless authentication (no server-side session storage)
- Cross-service authentication
- Mobile app authentication
- Microservices

**Business Problem**: Eliminates session store lookup on each request

**Technical Trade-offs**: Cannot revoke tokens easily (need short expiry + refresh tokens)

### OAuth 2.0 / OpenID Connect

**Problems Solved**:
- Third-party login (Google, GitHub, etc.)
- Delegated authorization
- Single Sign-On (SSO)

**Business Problem**: Reduce friction of user registration, improve security

### Session-based Authentication

**Problems Solved**:
- Easy to revoke (delete session)
- Server-side control
- Simple implementation

**When to use**: Traditional web apps, admin panels

### RBAC (Role-Based Access Control)

**Problems Solved**:
- Fine-grained permissions by role
- Admin vs user vs guest access
- Audit and compliance requirements

**Alternatives**: ABAC (attribute-based), Casbin (policy-based)

## Search Engines

### Elasticsearch

**Problems Solved**:
- Full-text search
- Faceted search and filtering
- Log analytics (ELK stack)
- Geospatial queries

**Business Problem**: Better search experience than database LIKE queries

**Technical Trade-offs**: Eventually consistent, more infrastructure

**Alternatives**: Solr (more traditional), Meilisearch (simpler), PostgreSQL full-text search (simpler)

## API Gateway

### Nginx

**Problems Solved**:
- Load balancing
- Reverse proxy
- SSL termination
- Static file serving
- Rate limiting

### Traefik

**Problems Solved**:
- Automatic service discovery
- Let's Encrypt integration
- Docker/Kubernetes native
- Dashboard UI

### Kong

**Problems Solved**:
- API management
- Authentication plugins
- Rate limiting
- Request/response transformation
- Analytics

## Container & Orchestration

### Docker

**Problems Solved**:
- Environment consistency (dev/prod parity)
- Dependency isolation
- Simplified deployment
- Microservices packaging

**Business Problem**: "Works on my machine" issues, deployment complexity

### Kubernetes

**Problems Solved**:
- Container orchestration at scale
- Auto-scaling
- Self-healing
- Service discovery
- Rolling deployments

**Business Problem**: Managing hundreds of containers, high availability

**Alternatives**: Docker Compose (simpler, smaller scale), Nomad (simpler)

## Infrastructure as Code

### Terraform

**Problems Solved**:
- Multi-cloud infrastructure
- Reproducible environments
- State management
- Dependency management

**Alternatives**: AWS CloudFormation (AWS only), Pulumi (real programming languages)

## CI/CD

### GitHub Actions

**Problems Solved**:
- Integrated with GitHub
- YAML configuration
- Free for public repos
- Large marketplace

**Alternatives**: GitLab CI (integrated with GitLab), Jenkins (self-hosted, powerful)

## Monitoring & Observability

### Prometheus + Grafana

**Problems Solved**:
- Metrics collection and visualization
- Alerting
- Time-series data
- Service discovery

**Business Problem**: System health visibility, SLA monitoring

### ELK Stack (Elasticsearch, Logstash, Kibana)

**Problems Solved**:
- Centralized logging
- Log search and analysis
- Visualization and dashboards

**Alternatives**: Loki + Grafana (lighter), Splunk (commercial)

### Jaeger / OpenTelemetry

**Problems Solved**:
- Distributed tracing
- Performance bottlenecks
- Request flow across services
- Root cause analysis

## Frontend Technologies

### React

**Problems Solved**:
- Component-based UI
- Virtual DOM for performance
- Large ecosystem and community
- Reusable components

**Alternatives**: Vue (simpler), Svelte (no virtual DOM), Angular (full framework)

### Vue.js

**Problems Solved**:
- Gentle learning curve
- Progressive framework
- Two-way data binding
- Single-file components

**Alternatives**: React (more popular), Svelte (modern, faster)

### Next.js

**Problems Solved**:
- Server-side rendering (SEO)
- Static site generation
- API routes
- File-based routing

**Business Problem**: SEO optimization, initial page load performance

**Alternatives**: Remix (simpler), Nuxt.js (Vue equivalent)

## File Upload & Storage

### AWS S3 / Compatible (MinIO)

**Problems Solved**:
- Scalable object storage
- CDN integration
- Direct uploads from browser
- Lifecycle policies

**Business Problem**: Storing user uploads, static assets, backups

### Local File System

**Problems Solved**:
- Simple implementation
- No external dependency
- Fast for small scale

**Trade-offs**: Not scalable, single point of failure

## Task Processing / Background Jobs

### Celery (Python)

**Problems Solved**:
- Asynchronous task execution
- Scheduled tasks (cron-like)
- Distributed task queue
- Retries and error handling

**Business Problems**: Email sending, report generation, data processing

**Alternatives**: RQ (simpler, Redis-only), Dramatiq (modern)

### Bull / BullMQ (Node.js)

**Problems Solved**:
- Redis-based job queue
- UI dashboard
- Job retries
- Scheduled jobs

**Alternatives**: Agenda (MongoDB-based), RabbitMQ-based solutions

## API Styles

### REST

**Problems Solved**:
- Standardized interface
- Cacheability through HTTP
- Statelessness
- Separation of concerns

**When to use**: CRUD operations, resource-oriented APIs

### GraphQL

**Problems Solved**:
- Overfetching/underfetching data
- Single endpoint
- Strongly typed schema
- Self-documenting

**When to use**: Complex data requirements, mobile apps, flexible queries

### gRPC

**Problems Solved**:
- High performance (binary protocol)
- Code generation from proto
- Bidirectional streaming
- Strong typing

**When to use**: Microservices communication, high-performance needs

## Testing Frameworks

### pytest (Python)

**Problems Solved**:
- Simple test discovery
- Powerful fixtures
- Assertion introspection
- Plugin ecosystem

**Alternatives**: unittest (built-in), nose2 (legacy)

### Jest (JavaScript/TypeScript)

**Problems Solved**:
- Zero configuration
- Built-in mocking
- Coverage reports
- Parallel test execution

**Alternatives**: Mocha + Chai (more flexible), Vitest (faster)

### JUnit (Java)

**Problems Solved**:
- Standard testing framework
- IDE integration
- Test suites and lifecycle
- Parameterized tests

## Common Architecture Patterns

### Layered Architecture

**Components**: Presentation → Application → Domain → Data

**Problems Solved**:
- Separation of concerns
- Testability
- Parallel development

**When to use**: Traditional business applications

### Microservices

**Problems Solved**:
- Independent deployment
- Technology diversity
- Fault isolation
- Team scaling

**Trade-offs**: Distributed complexity, data consistency challenges

### Event-Driven

**Problems Solved**:
- Service decoupling
- Async processing
- Audit trail through events
- Real-time updates

**When to use**: High scalability, loose coupling needed

### CQRS (Command Query Responsibility Segregation)

**Problems Solved**:
- Optimized read models
- Complex business logic
- Performance at scale

**When to use**: Complex domains, read/write performance mismatch

---

## Usage Tips

When analyzing a project:

1. **Identify the category** of each technology (language, framework, database, etc.)
2. **Consider the context** - project age, team size, domain requirements
3. **Think about alternatives** - what wasn't chosen and why
4. **Map to business problems** - what user need does this address?
5. **Note technical constraints** - scale, performance, security, compliance

Example analysis for Redis:
```
Technology: Redis
Category: Caching / Message Queue
Business Problem Solved: Fast user experience, real-time features
Technical Problem Solved: Sub-millisecond reads, pub/sub messaging, session storage
Alternative Not Chosen: Memcached (less features), RabbitMQ (heavier for simple caching)
```
