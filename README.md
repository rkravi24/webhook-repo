# GitHub Webhook Monitor

A Flask-based application that receives GitHub webhooks and displays real-time repository activity with a clean, modern UI.

## Features

- **Real-time Monitoring**: Automatically receives GitHub webhook events
- **Live Updates**: UI polls for new events every 15 seconds
- **Clean Display**: Formatted messages for push, pull request, and merge actions
- **Responsive Design**: Modern, mobile-friendly interface
- **MongoDB Integration**: Persistent storage of all events
- **Health Monitoring**: Built-in health checks and status indicators
- **Docker Support**: Easy deployment with Docker and Docker Compose

## Repository Structure

```
webhook-repo/
├── app.py                 # Main Flask application
├── templates/
│   └── index.html        # Web UI template
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Docker Compose setup
├── .env.example        # Environment variables template
└── README.md           # This file
```

## Quick Start

### Option 1: Docker Compose (Recommended)

1. **Clone the repository**
   ```bash
   git clone <your-webhook-repo-url>
   cd webhook-repo
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your webhook secret
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Web UI: http://localhost:5000
   - Webhook endpoint: http://localhost:5000/webhook

### Option 2: Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start MongoDB**
   ```bash
   # Using Docker
   docker run -d -p 27017:27017 --name mongodb mongo:7.0
   
   # Or install MongoDB locally
   ```

3