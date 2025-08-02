# Test Automation Platform

A production-ready, open-source test automation platform that records UI actions, converts them to maintainable Robot Framework tests using AI, and provides comprehensive test execution with team collaboration features.

## 🚀 Features

### Core Functionality
- **UI Recording**: Record user interactions using Playwright Codegen in multiple browsers (Chromium, Firefox, WebKit)
- **AI-Powered Conversion**: Automatically convert Playwright scripts to Robot Framework Browser Library tests using Azure OpenAI
- **Test Execution**: Execute Robot Framework tests with video capture and detailed results
- **Cross-Platform**: Works seamlessly on Windows, Linux, macOS, and containerized CI environments

### Team Collaboration
- **Role-Based Access Control**: Admin, Tester, and Viewer roles with granular permissions
- **Project Management**: Organize tests into projects with team member access controls
- **Email Invitations**: Invite team members via email with automatic account setup

### Analytics & Reporting
- **Interactive Dashboards**: Visual analytics with pass/fail trends, duration metrics, and flakiness analysis
- **Execution History**: Comprehensive test execution logs with video playback
- **Performance Insights**: Script performance analysis and stability scoring
- **Export Capabilities**: CSV export for external analysis

### Enterprise Ready
- **Security First**: CSRF protection, password hashing, input sanitization, and XSS prevention
- **Scalable Architecture**: Modular Flask application with background job processing
- **White-Label**: No platform-specific dependencies or branding
- **Production Hardened**: Comprehensive error handling and monitoring

## 📋 Prerequisites

- Python 3.11 or higher
- Node.js and npm (for Playwright browser installation)
- Azure OpenAI account with GPT-4o deployment
- Git

## 🔧 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd test-automation-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt





# Test Automation Platform - Development Guide

## Overview

This is a production-ready, open-source test automation platform built with Flask that records UI actions, converts them to maintainable Robot Framework tests using AI, and provides comprehensive test execution with team collaboration features. The platform is designed to be white-label and platform-agnostic, similar to Testim.io but self-hosted.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
- **Flask Web Application**: Modular architecture with blueprints for different functional areas
- **SQLAlchemy ORM**: Database abstraction layer with model-based approach
- **Flask-Login**: User session management and authentication
- **Problem Addressed**: Need for scalable, maintainable web application structure
- **Solution**: Blueprint-based modular Flask app with clear separation of concerns
- **Pros**: Easy to extend, good separation of concerns, established patterns
- **Cons**: More complex than single-file apps for simple use cases

### Database Layer
- **SQLite by default**: File-based database for development and small deployments
- **PostgreSQL ready**: Can be easily switched via DATABASE_URL environment variable
- **Problem Addressed**: Flexible database support for different deployment scenarios
- **Solution**: SQLAlchemy with configurable database URLs
- **Pros**: Easy development setup, production-ready scaling path
- **Cons**: SQLite limitations for high-concurrency scenarios

### AI Integration
- **Azure OpenAI**: GPT-4o model for Playwright to Robot Framework conversion
- **Problem Addressed**: Automated test script conversion between formats
- **Solution**: Azure OpenAI API integration with structured prompts
- **Pros**: High-quality AI conversion, enterprise-grade service
- **Cons**: Requires Azure subscription, API costs, external dependency

## Key Components

### Authentication & Authorization
- **Role-Based Access Control**: Admin, Tester, Viewer roles with hierarchical permissions
- **Project-Level Access**: Fine-grained permissions per project with member management
- **Invitation System**: Email-based team member invitations with token expiration
- **Security Features**: CSRF protection, password hashing, input sanitization

### Test Recording Workflow
- **Playwright Codegen**: Browser automation for recording user interactions
- **Multi-Browser Support**: Chromium, Firefox, WebKit recording capabilities
- **Cross-Platform**: Windows, Linux, macOS compatibility with headless mode support
- **File Management**: Safe file naming, project isolation, collision handling

### Test Execution Engine
- **Robot Framework**: Industry-standard test automation framework
- **Video Capture**: Execution recording for debugging and reporting
- **Background Processing**: Async execution with status tracking
- **Results Management**: Comprehensive execution history and artifact storage

### Analytics & Reporting
- **Dashboard Metrics**: Pass/fail rates, execution trends, performance insights
- **Data Visualization**: Chart.js integration for interactive analytics
- **Export Capabilities**: CSV export for external analysis
- **Project-Specific Views**: Analytics filtering by project and time range

### Team Collaboration
- **Project Management**: Multi-project workspace with team access controls
- **Member Invitations**: Email-based onboarding with role assignment
- **Activity Tracking**: User actions and execution history
- **Shared Resources**: Project-level test script and execution sharing

## Data Flow

### Recording to Execution Pipeline
1. **User Initiates Recording**: Selects project, names script, chooses browser
2. **Playwright Codegen Launch**: Server spawns browser automation session
3. **User Interaction Capture**: Raw Playwright script generation
4. **AI Conversion**: Azure OpenAI converts to Robot Framework format
5. **Script Storage**: Organized file system storage with metadata tracking
6. **Execution Ready**: Scripts available for individual or suite execution

### Execution Flow
1. **Script Selection**: User chooses scripts or full project suite
2. **Robot Framework Execution**: Background process with video capture
3. **Result Processing**: Status tracking, artifact collection, database storage
4. **Analytics Update**: Metrics aggregation for dashboard and reporting

### User Management Flow
1. **Invitation Creation**: Admin/Tester creates invitation with role/project assignment
2. **Email Delivery**: SMTP-based invitation with secure token
3. **Account Creation**: Invited user completes registration
4. **Access Activation**: Automatic project access based on invitation parameters

## External Dependencies

### Required Services
- **Azure OpenAI**: GPT-4o deployment for script conversion
  - Endpoint, API key, and deployment name required
  - Fallback: Manual script editing if service unavailable
- **SMTP Server**: Email delivery for team invitations
  - Configurable host, port, credentials
  - Fallback: Manual user creation without email workflow

### Browser Dependencies
- **Playwright**: Automated browser control
  - Requires Node.js and npm for installation
  - Downloads browser binaries automatically
  - Cross-platform browser support

### Python Packages
- **Core Framework**: Flask, SQLAlchemy, Flask-Login
- **Security**: Werkzeug password hashing, CSRF protection
- **AI Integration**: OpenAI Python client
- **Test Automation**: Robot Framework, Playwright
- **Utilities**: Pathlib for file operations, threading for background jobs

## Deployment Strategy

### Development Setup
- **Virtual Environment**: Isolated Python dependencies
- **Environment Variables**: Configuration via .env or system environment
- **SQLite Database**: File-based storage for quick setup
- **Debug Mode**: Enhanced error reporting and auto-reload

### Production Considerations
- **Database Migration**: SQLite to PostgreSQL for scalability
- **Environment Hardening**: Secure secret keys, HTTPS enforcement
- **Process Management**: WSGI server (Gunicorn) with reverse proxy
- **File Storage**: Persistent volumes for test artifacts and videos
- **Background Jobs**: Consider Celery for heavy execution workloads

### Security Hardening
- **CSRF Protection**: All forms protected with tokens
- **Input Sanitization**: User inputs cleaned and validated
- **Path Traversal Prevention**: Safe file operations with path validation
- **Role Enforcement**: Decorator-based access control throughout application
- **Session Security**: Secure session configuration with proper timeouts

### Monitoring & Maintenance
- **Health Endpoints**: System status checking for monitoring tools
- **Logging**: Structured logging for debugging and audit trails
- **Error Handling**: Graceful degradation with user-friendly error messages
- **File Cleanup**: Configurable retention policies for execution artifacts

This architecture provides a solid foundation for a production test automation platform while maintaining flexibility for different deployment scenarios and scaling requirements.



modules = ["python-3.11"]

[nix]
channel = "stable-24_05"
packages = ["gitFull", "glibcLocales", "openssl", "playwright-driver", "postgresql"]

[deployment]
deploymentTarget = "autoscale"
run = ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]

[workflows]
runButton = "Project"

[[workflows.workflow]]
name = "Project"
mode = "parallel"
author = "agent"

[[workflows.workflow.tasks]]
task = "workflow.run"
args = "Start application"

[[workflows.workflow]]
name = "Start application"
author = "agent"

[[workflows.workflow.tasks]]
task = "shell.exec"
args = "gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app"
waitForPort = 5000

[[ports]]
localPort = 5000
externalPort = 80

