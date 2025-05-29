# SGAY Sikkim - AI-Powered Housing Portal 🏠🤖

**🏆 Finalist Project - Team 01 GT | codesummit@sikkim'50 Hackathon**

An innovative, AI-powered Flask web application for the **Sikkim Garib Awas Yojana (SGAY)** housing scheme by the Government of Sikkim. This platform revolutionizes the housing assistance process through intelligent automation, modern web technologies, and a well-architected, modular design.

## 👥 Team Credits

**Team 01 GT - Finalists at codesummit@sikkim'50**
- **Debopriyo Das** [@dragon4926](https://github.com/dragon4926) - Lead Developer & AI Integration
- **Golam Tausif** [@thegolamtausif](https://github.com/thegolamtausif) - Backend Architecture & Database Design  
- **Asim Halder** - Documentation

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)
![Status](https://img.shields.io/badge/status-hackathon_finalist-success.svg)
![AI](https://img.shields.io/badge/AI-Gemini_Powered-orange.svg)

## 🎯 Hackathon Innovation

This project was developed for **codesummit@sikkim'50** hackathon, where our team reached the **finals** by creating a comprehensive solution that addresses real-world government digitization challenges in Sikkim. Our innovation lies in combining traditional government processes with cutting-edge AI technology.

### 🌟 Project Highlights

- **🤖 AI-First Approach**: Google Gemini integration for intelligent house design generation
- **🏗️ Real-World Impact**: Actual solution for Sikkim's housing scheme digitization
- **⚡ Production-Ready**: Complete deployment pipeline with Docker & Vercel
- **🎨 Modern UX**: Beautiful, responsive interface built with Tailwind CSS
- **🔒 Enterprise Security**: Role-based access control with comprehensive security measures

## 🚀 Key Features

### 🤖 AI-Powered Innovation
- **🏡 Intelligent House Design Generator**: Upload plot images → Get 4 AI-generated house designs
- **💬 Smart Chat Assistant**: Gemini-powered support for beneficiaries
- **📋 Automated Eligibility Assessment**: AI-driven qualification checking
- **📄 Document Processing**: Intelligent document verification and processing
- **🎯 Personalized Recommendations**: Smart guidance based on user profiles

### 🏗️ Robust Architecture
- **🏭 Application Factory Pattern**: Scalable, modular Flask architecture
- **📦 Blueprint Organization**: Clean separation of admin, beneficiary, and auth modules
- **🌍 Multi-Environment Config**: Development, testing, and production configurations
- **⚠️ Comprehensive Error Handling**: Robust error management with logging
- **🔌 API-First Design**: RESTful APIs for all operations

### 👥 Multi-Role Management
- **👨‍💼 Admin Dashboard**: Real-time analytics, project management, fund tracking
- **🏠 Beneficiary Portal**: Application submission, progress tracking, AI assistance
- **👮‍♂️ Nodal Officer Interface**: Application processing and verification
- **🔐 Secure Authentication**: bcrypt-based password hashing with session management

### 📊 Advanced Dashboard Features
- **📈 Real-time Analytics**: Live project statistics and progress tracking
- **🗺️ Interactive Maps**: Leaflet.js integration for geographic visualization
- **📱 Responsive Design**: Mobile-first approach with Tailwind CSS
- **📊 Data Visualization**: Chart.js integration for comprehensive reporting

## 🛠️ Technology Stack

### Backend Excellence
```yaml
Framework: Flask 3.0+ (Application Factory Pattern)
Database: SQLAlchemy ORM + Flask-Migrate
Authentication: Flask-Login + bcrypt
AI Integration: Google Gemini API (2.0-flash-preview)
APIs: RESTful design with JSON responses
Security: CSRF protection, input validation, secure sessions
```

### Frontend Innovation
```yaml
Styling: Tailwind CSS (modern, responsive)
JavaScript: ES6+ with modern browser APIs
Maps: Leaflet.js for interactive mapping
Charts: Chart.js for data visualization
Templates: Jinja2 with inheritance and macros
```

### Database & Storage
```yaml
Development: SQLite (local development)
Production: PostgreSQL (recommended) / MySQL
Migrations: Alembic for version control
File Storage: Secure upload handling with validation
```

### DevOps & Deployment
```yaml
Containerization: Docker + Docker Compose
Deployment: Vercel, Heroku, traditional hosting
Process Manager: Gunicorn WSGI server
Environment: python-dotenv configuration
Monitoring: Structured logging with configurable levels
```

## 🏗️ Project Architecture

```
sgay-sikkim/
├── app/                          # Main application package
│   ├── __init__.py              # Application factory
│   ├── core/                    # Core application modules
│   ├── main/                    # Main blueprint (public routes)
│   ├── api/                     # RESTful API endpoints
│   └── utils/                   # Utility functions
├── admin/                       # Admin management system
├── auth/                        # Authentication & authorization
├── beneficiary/                 # Beneficiary portal
│   └── ai_architect.py          # 🤖 AI house design generator
├── static/                      # Static assets & uploads
├── templates/                   # Jinja2 templates
├── migrations/                  # Database migrations
├── tests/                       # Comprehensive test suite
├── docker-compose.yml           # 🐳 Multi-container setup
├── Dockerfile                   # 🐳 Production container
├── vercel.json                  # ⚡ Vercel deployment config
├── requirements.txt             # Python dependencies
└── config.py                    # Environment configurations
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package installer
- Git for version control
- Docker (optional, for containerized deployment)

### 🔧 Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/dragon4926/sgay-sikkim.git
   cd sgay-sikkim
   ```

2. **Create virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment configuration**
   ```bash
   # Create environment file
   cp .env.example .env
   
   # Edit .env with your configuration:
   # SECRET_KEY=your-secret-key-here
   # GEMINI_API_KEY=your-gemini-api-key
   # DATABASE_URL=sqlite:///sgay_dev.db
   ```

5. **Initialize database**
   ```bash
   flask init-db
   ```

6. **Create admin user**
   ```bash
   flask create-admin
   ```

7. **Run the application**
   ```bash
   # Development mode
   python run.py
   
   # Or using Flask CLI
   flask run --debug
   ```

8. **Access the application**
   - Open browser: `http://localhost:5000`
   - Login with admin credentials
   - Explore the AI-powered features!

### 🐳 Docker Deployment

#### Option 1: Docker Compose (Recommended)
```bash
# Start all services (web app + PostgreSQL + Redis)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

#### Option 2: Docker Build
```bash
# Build image
docker build -t sgay-sikkim .

# Run container
docker run -d -p 5000:5000 \
  -e SECRET_KEY=your-secret-key \
  -e GEMINI_API_KEY=your-api-key \
  sgay-sikkim
```

### ⚡ Vercel Deployment

1. **Install Vercel CLI**
   ```bash
   npm i -g vercel
   ```

2. **Deploy to Vercel**
   ```bash
   vercel --prod
   ```

3. **Environment Variables**
   Set in Vercel dashboard:
   - `SECRET_KEY`: Your application secret
   - `GEMINI_API_KEY`: Google Gemini API key
   - `DATABASE_URL`: Production database URL

## 🤖 AI Features Deep Dive

### House Design Generator
Our flagship AI feature uses Google Gemini to generate personalized house designs:

```python
# Example AI integration
from beneficiary.ai_architect import AIArchitectService

ai_service = AIArchitectService()
designs = ai_service.generate_designs(
    plot_image_path="path/to/plot.jpg",
    beneficiary=beneficiary_obj,
    fund_allocation=1500000,
    additional_info="Family of 4, needs study room"
)
```

**Features:**
- 📸 Plot image analysis
- 🏗️ 4 different architectural styles
- 💰 Budget-aware cost estimation
- 🌿 Climate-appropriate recommendations
- 📐 Detailed blueprints and views

### Smart Chat Assistant
Integrated Gemini-powered chat for user support:
- Real-time assistance
- Application guidance
- Eligibility checking
- Document requirements
- Status updates

## 📚 API Documentation

### Authentication
```http
POST /api/login
POST /api/register
POST /api/send-otp
POST /api/verify-otp
```

### Beneficiaries
```http
GET  /api/beneficiaries      # List with pagination
POST /api/beneficiaries      # Create application
GET  /api/beneficiaries/{id} # Get details
```

### AI Services
```http
POST /api/eligibility        # AI eligibility check
POST /api/chat              # Smart assistant
```

### Projects & Analytics
```http
GET /api/projects           # List projects
GET /api/stats             # Dashboard statistics
```

## 🔒 Security Features

- **🔐 Authentication**: Secure password hashing with bcrypt
- **🛡️ Authorization**: Role-based access control (RBAC)
- **🍪 Session Security**: Secure cookies with CSRF protection
- **📤 File Upload Security**: Type validation and size restrictions
- **🔍 Input Validation**: SQL injection prevention via ORM
- **🔒 Environment Secrets**: Secure configuration management

## 🧪 Testing

```bash
# Run test suite
pytest

# With coverage report
pytest --cov=app --cov-report=html

# Run specific tests
pytest tests/test_ai_features.py -v
```

## 📊 Performance & Monitoring

### Health Check
```bash
curl http://localhost:5000/health
```

### Logging
```python
# Structured logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## 🚀 Deployment Environments

### Development
- Debug enabled
- SQLite database
- Hot reload
- Detailed logging

### Production
- Optimized performance
- PostgreSQL database
- Security headers
- Error tracking

## 🛠️ Development Practices & Code Standards

This project was developed adhering to robust software engineering practices:

- **Version Control**: Git was utilized for version control, following a feature-branch workflow to manage development and collaboration effectively.
- **Testing**: A comprehensive test suite was implemented using `pytest`, including unit and integration tests. Coverage reports (e.g., `pytest --cov=app --cov-report=html`) were utilized to ensure code quality and reliability.
- **Code Standards Adhered To**:
  - Strict adherence to PEP 8 style guidelines for Python.
  - Extensive use of type hints for improved code clarity, maintainability, and early error detection.
  - Comprehensive docstrings for all modules, classes, and functions, enhancing code readability.
  - A consistent focus on maintaining high test coverage (targeted >80%).

## 🏆 Hackathon Achievements

**codesummit@sikkim'50 Highlights:**
- 🥇 **Finalist Team** - Advanced to final round
- 🤖 **Most Innovative Use of AI** - Gemini integration
- 🎯 **Real-World Impact** - Government digitization solution
- 🏗️ **Technical Excellence** - Production-ready architecture
- 🎨 **Best User Experience** - Modern, intuitive interface
- ✅ Production-ready deployment

## 💡 Future Vision & Potential Scalability

### Phase 1: Core Implementation (Hackathon Scope - Completed)
- ✅ AI-powered house design generation leveraging Google Gemini.
- ✅ Robust multi-role (Admin, Beneficiary, Nodal Officer) authentication and authorization system.
- ✅ Interactive data visualization dashboard and GIS mapping features (Leaflet.js, Chart.js).
- ✅ Production-ready deployment architecture demonstrated (Docker, Vercel).

### Phase 2: Potential Enhancements & Broader Impact
- 📱 Native mobile application development (iOS/Android) to improve accessibility and user engagement.
- 🔗 Exploration of blockchain technology for immutable record-keeping and enhanced transparency in fund allocation and project milestones.
- 📊 Advanced predictive analytics using Machine Learning insights for scheme optimization, demand forecasting, and resource management.
- 🌐 Comprehensive multi-language support (including local dialects like Hindi, Nepali, Lepcha) to ensure inclusivity.

### Phase 3: Long-term Scalability & Ecosystem Integration
- 🏛️ Seamless integration capabilities with other government welfare schemes and databases for a unified citizen service platform.
- 🔐 Implementation of advanced digital identity verification mechanisms (e.g., biometric, national ID linkage) for secure and fraud-resistant processes.
- 💳 Secure and compliant payment gateway integration for direct benefit transfers or other financial transactions related to the scheme.
- 📈 Architectural design for state-wide deployment, considering high availability, fault tolerance, and data sovereignty.

## 🎉 Acknowledgments

**Special Thanks:**
- **Government of Sikkim** - For the opportunity and support
- **codesummit@sikkim'50** - For hosting an amazing hackathon
- **Google AI** - For Gemini API access and AI capabilities
- **Flask Community** - For the excellent framework
- **Open Source Contributors** - For the amazing libraries

## 📞 Contact & Support

**Team 01 GT:**
- **Email**: debopriyo.das0401@gmail.com
- **GitHub**: [Project Repository](https://github.com/dragon4926/sgay)
- **Issues**: [GitHub Issues](https://github.com/dragon4926/sgay/issues)

**Individual Team Members:**
- **Debopriyo Das**: [@dragon4926](https://github.com/dragon4926)
- **Golam Tausif**: [@thegolamtausif](https://github.com/thegolamtausif)
- **Asim Halder**: Contact via team email

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**🏆 Made with ❤️ by Team 01 GT for codesummit@sikkim'50**

**Empowering Sikkim's Digital Future - One House at a Time** 🏠🤖

[![Hackathon](https://img.shields.io/badge/Hackathon-Finalist-gold.svg)](https://codesummit.sikkim.gov.in)
[![AI](https://img.shields.io/badge/AI-Powered-blue.svg)](https://ai.google.dev/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)

</div> 