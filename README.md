🏛️ DAO Cafe Backend
DAO Cafe is a decentralized platform that helps users create, register, and manage DAOs built on createdao.org. Testers are invited to join the platform, connect their wallets, and interact with DAO governance features like proposal creation, token staking, and community voting. Active participants earn token airdrops and early access to platform features.
🚀 Features
🏗️ DAO Management Create and register DAOs with comprehensive backend APIs
🔗 Ethereum Authentication Web3 wallet authentication and signature verification
🗳️ Governance System Proposal creation, voting, and DIP (DAO Improvement Proposal) management
💰 Staking & Treasury Token staking mechanisms and treasury balance tracking
🎯 Presale System Token presale functionality with transaction tracking
📊 Forum Integration Discussion threads, replies, and community engagement
🔒 Security Features Rate limiting, custom permissions, and blockchain validation
🛠 Tech Stack
🔧 Backend Technologies

Python 3.11+ with Django REST Framework
PostgreSQL for primary data storage
Redis + Celery for background task processing
Web3.py for Ethereum blockchain interactions
Custom Ethereum authentication system
JWT tokens for API authentication

🚀 DevOps & Infrastructure

Docker containerization with multi-environment support
Nginx reverse proxy with SSL configuration
Custom management commands for database operations
Comprehensive test suite with Django TestCase
Rate limiting and throttling middleware

📦 Quick Start
Prerequisites

Docker & Docker Compose
Python 3.11+
PostgreSQL
Redis

🐳 Docker Setup (Recommended)
bash# Clone the repository
git clone git@github.com:jamwujustyle/dao-cafe-server.git
cd dao-cafe-server

# Start development environment
docker-compose up --build

# Or start production environment
docker-compose -f docker-compose.prod.yml up --build
🔧 Local Development Setup
Backend Setup
bashcp examle.env .env  # Configure your environment variables
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic
python manage.py runserver
📂 Project Structure
daocafe-server/
├── 📁 app/                      # Django project configuration
│   ├── settings.py              # Main settings
│   ├── celery_config.py         # Celery configuration
│   └── urls.py                  # URL routing
├── 📁 core/                     # Core application
│   ├── models.py                # User and base models
│   ├── helpers/                 # Utility functions
│   ├── validators/              # Custom validators
│   └── management/commands/     # Custom Django commands
├── 📁 dao/                      # DAO management
│   ├── models.py                # DAO, Stake, Presale models
│   ├── views.py                 # API endpoints
│   ├── serializers.py           # DRF serializers
│   └── packages/services/       # Business logic services
├── 📁 forum/                    # Forum system
│   ├── models.py                # DIP, Thread, Vote models
│   ├── views.py                 # Forum API endpoints
│   ├── tasks.py                 # Celery tasks
│   └── packages/services/       # Forum services
├── 📁 eth_auth/                 # Ethereum authentication
│   ├── eth_authentication.py    # Web3 auth logic
│   ├── views.py                 # Auth endpoints
│   └── serializers.py           # Auth serializers
├── 📁 user/                     # User management
│   ├── views.py                 # User API endpoints
│   └── serializers.py           # User serializers
├── 📁 services/                 # Shared services
│   ├── blockchain/              # Blockchain interactions
│   └── utils/                   # Common utilities
├── 📁 nginx/                    # Nginx configuration
├── 📁 scripts/                  # Deployment scripts
├── 🐳 docker-compose.yml        # Docker configuration
├── 🐳 docker-compose.prod.yml   # Production Docker config
└── 📋 requirements.txt          # Python dependencies
🌍 Environment Variables
Backend (.env)
env# Database Configuration
DATABASE_NAME=dao_cafe
DATABASE_USER=postgres
DATABASE_PASSWORD=your_password
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Django Settings
SECRET_KEY=your-super-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Ethereum/Blockchain
ETH_NODE_URL=https://mainnet.infura.io/v3/your-project-id
WEB3_PROVIDER_URI=https://mainnet.infura.io/v3/your-project-id

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# API Configuration
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://dao.cafe
🔥 Key Features
🔐 Ethereum Authentication

Custom Web3 signature verification
Wallet-based user registration and login
Secure message signing with nonce validation

🏛️ DAO Operations

Create and manage DAO instances
Stake tokens with voting power calculation
Treasury balance tracking and management
Presale functionality with transaction monitoring

🗳️ Governance System

DIP (DAO Improvement Proposal) creation
Community voting with weighted power
Thread-based discussions and replies
Automated proposal status updates

⚡ Performance & Security

Custom rate limiting and throttling
Comprehensive input validation
Background task processing with Celery