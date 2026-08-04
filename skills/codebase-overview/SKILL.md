---
name: codebase-overview
description: "Use this skill to produce a high-level overview of a codebase: behavior, purpose, roles, concerns, and technical stack."
---


## Sections

### 1. Behavior

#### Business Purpose
Describe the primary function of the system and the problem it solves.

#### Customer Base
Identify who the system serves:
- Internal teams
- External customers
- Partners or third‑party integrators

#### Information Domain
List the major categories of information the system stores or processes:
- Core domain entities
- Sensitive or regulated data
- Derived or computed data

#### Roles
Identify distinct user types or permission groups:
- Admin
- Staff
- Customer
- API client
- Any domain‑specific roles

#### Key Concerns
Highlight the aspects that matter most to users, clients, or staff:
- Reliability
- Performance
- Security
- Compliance
- Usability
- Operational visibility


### 2. Technical Stack

#### Framework & Language
Identify the primary language and framework used by the system.  
Examples include:
- Ruby on Rails
- Django / Python
- Express / Node.js
- mux / Golang
- Spring Boot / Java
- Laravel / PHP

#### Third‑Party Components
List external dependencies and integrations:
- Dependency libraries (rubygems, npm packages, jars, etc.)
- JavaScript widgets (analytics, chat widgets, marketing trackers)
- External APIs or services
- Systems providing webhook events or upstream data

#### Datastores
Identify storage and caching technologies:
- SQL (PostgreSQL, MySQL, MariaDB)
- NoSQL (MongoDB, DynamoDB)
- Caches (Redis, Memcached)
- Search engines (Elasticsearch, OpenSearch)
- Message queues (Kafka, RabbitMQ, SQS)

#### Infrastructure Indicators
Capture any visible operational or deployment components:
- Containerization (Docker, Kubernetes)
- CI/CD pipelines
- Cloud providers (AWS, GCP, Azure)
- Logging/monitoring tools


## Evidence Format

Each section may include:
- **Status:** Identified, Partially Identified, or Unknown  
- **Evidence:** References to files, directories, configuration, or code  
- **Notes:** Clarifications, assumptions, or gaps in available information


## Output Structure

The final overview should follow this structure:

1. **Behavior**
   - Business Purpose
   - Customer Base
   - Information Domain
   - Roles
   - Key Concerns

2. **Technical Stack**
   - Framework & Language
   - Third‑Party Components
   - Datastores
   - Infrastructure Indicators

3. **Evidence**
   - Status
   - Evidence
   - Notes


