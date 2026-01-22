# Room Booking System - System Architecture

## 📐 Complete System Architecture

```mermaid
flowchart TB
    subgraph Client["🖥️ Client Layer"]
        Browser["Web Browser"]
        User["👤 User"]
    end
    
    subgraph Frontend["🎨 Frontend Layer"]
        Templates["Django Templates<br/>- UserPage<br/>- AdminPage<br/>- SignIn/Register"]
        Static["Static Assets<br/>- CSS<br/>- JavaScript"]
    end
    
    subgraph Django["🐍 Django Application Server"]
        direction TB
        
        subgraph Apps["Django Apps"]
            Accounts["👥 Accounts App<br/>- User Management<br/>- Google OAuth<br/>- Profile Management"]
            Booking["📅 Booking App<br/>- Room Management<br/>- Booking CRUD<br/>- Availability Check"]
            Chatbot["🤖 Chatbot App<br/>- Chat Endpoint<br/>- Session Management"]
        end
        
        subgraph Middleware["Middleware"]
            Auth["Authentication"]
            CSRF["CSRF Protection"]
            Session["Session Management"]
        end
        
        subgraph Utils["Utilities"]
            EmailUtil["Email Service"]
            CalendarUtil["Google Calendar API"]
            TelegramUtil["Telegram Bot API"]
        end
    end
    
    subgraph AI["🧠 AI Layer"]
        direction LR
        
        Kernel["Semantic Kernel"]
        
        subgraph AIServices["AI Services"]
            Groq["Groq API<br/>(Llama 3.1)"]
        end
        
        subgraph Plugins["Plugins"]
            RoomPlugin["Room Booking Plugin<br/>- find_available_rooms<br/>- get_room_info<br/>- prepare_booking<br/>- list_user_bookings"]
        end
        
        BookingAuto["Booking Automation<br/>- Score Rooms<br/>- Check Conflicts<br/>- Auto-Book"]
    end
    
    subgraph Database["💾 Database Layer"]
        MySQL[(MySQL Database)]
        
        subgraph Tables["Tables"]
            UserTable[("👤 User Table")]
            RoomTable[("🏢 Room Table")]
            BookingTable[("📝 Booking Table")]
            RuleTable[("📋 Rules Table")]
        end
    end
    
    subgraph External["🌐 External Services"]
        GoogleAuth["Google OAuth 2.0"]
        GoogleCal["Google Calendar"]
        TelegramAPI["Telegram Bot API"]
        EmailSMTP["Email SMTP<br/>(Gmail)"]
    end
    
    subgraph Cache["⚡ Cache Layer"]
        RedisCache["Cache<br/>- Session Data<br/>- Booking Preview"]
    end
    
    %% Client to Frontend
    User --> Browser
    Browser --> Templates
    Browser --> Static
    
    %% Frontend to Django
    Templates --> Accounts
    Templates --> Booking
    Templates --> Chatbot
    Static --> Templates
    
    %% Django Apps Flow
    Accounts --> Auth
    Booking --> Auth
    Chatbot --> Session
    
    Auth --> Middleware
    CSRF --> Middleware
    Session --> Middleware
    
    %% Django to External Services
    Accounts --> GoogleAuth
    Booking --> GoogleCal
    Booking --> EmailUtil
    Booking --> TelegramUtil
    
    EmailUtil --> EmailSMTP
    TelegramUtil --> TelegramAPI
    CalendarUtil --> GoogleCal
    
    %% Chatbot to AI
    Chatbot --> Kernel
    Kernel --> Groq
    Kernel --> RoomPlugin
    RoomPlugin --> BookingAuto
    
    %% AI to Database
    BookingAuto --> MySQL
    RoomPlugin --> MySQL
    
    %% Django Apps to Database
    Accounts --> UserTable
    Booking --> RoomTable
    Booking --> BookingTable
    Booking --> RuleTable
    
    UserTable --> MySQL
    RoomTable --> MySQL
    BookingTable --> MySQL
    RuleTable --> MySQL
    
    %% Cache Integration
    Chatbot --> RedisCache
    Session --> RedisCache
    
    style Client fill:#e1f5ff
    style Frontend fill:#fff4e6
    style Django fill:#f3e5f5
    style AI fill:#e8f5e9
    style Database fill:#fce4ec
    style External fill:#fff3e0
    style Cache fill:#e0f2f1
```

## 🔄 AI Chatbot Flow (Detailed)

```mermaid
flowchart LR
    User["👤 User Input"] --> Frontend["🌐 Frontend"]
    
    subgraph Server["Django Server"]
        Frontend --> ChatView["📥 /chatbot/chat/<br/>POST Endpoint"]
        
        subgraph ChatFlow["Chat Processing"]
            ChatView --> Agent["🤖 Chat Agent"]
            Agent --> Detect["🔍 Detect Intent<br/>(General vs Booking)"]
            
            Detect -->|"General Query"| DirectAI["🗣️ Direct AI Response<br/>(No Tools)"]
            Detect -->|"Booking Query"| ToolAI["🛠️ AI with Tools<br/>(Function Calling)"]
            
            ToolAI --> Groq["🧠 Groq API Call<br/>with Tools"]
            Groq --> CheckFunc{"Function<br/>Called?"}
            
            CheckFunc -->|"Yes"| ExecFunc["⚙️ Execute Plugin<br/>Function"]
            ExecFunc --> QueryDB["💾 Query Database"]
            QueryDB --> FuncResult["📊 Function Result"]
            FuncResult --> FinalAI["🗣️ AI Final Response<br/>(with DB data)"]
            
            CheckFunc -->|"No"| DirectResp["💬 Direct Response"]
            
            DirectAI --> Response["📤 JSON Response"]
            FinalAI --> Response
            DirectResp --> Response
        end
        
        Response --> Cache["⚡ Cache Result"]
        Cache --> Preview["👁️ Preview/Confirm"]
    end
    
    Preview --> Frontend
    Frontend --> User
    
    User -->|"Confirm"| ConfirmEndpoint["✅ /confirm<br/>POST Endpoint"]
    ConfirmEndpoint --> AuthUser["🔐 Resolve User"]
    AuthUser --> AutoBook["🎯 Auto Book"]
    AutoBook --> DB["💾 Save to DB"]
    DB --> Notify["📧 Send Notifications"]
    Notify --> Result["✅ Booking Complete"]
    Result --> User
    
    style Server fill:#f3e5f5
    style ChatFlow fill:#e8f5e9
```

## 📊 Database Schema

```mermaid
erDiagram
    User ||--o{ Booking : creates
    Room ||--o{ Booking : reserved_for
    BookingRule ||--o{ Booking : governed_by
    
    User {
        int id PK
        string email UK
        string username
        string first_name
        string last_name
        string phone_number
        string student_id
        string department
        string faculty
        boolean is_admin
        string profile_picture
        datetime date_joined
    }
    
    Room {
        int id PK
        string name
        string room_number UK
        int capacity
        string building_name
        string building_type
        string room_type
        boolean is_available
        boolean has_projector
        boolean has_whiteboard
        boolean has_computer
        boolean has_ac
        string image
    }
    
    Booking {
        int id PK
        int user_id FK
        int room_id FK
        datetime start_time
        datetime end_time
        string purpose
        string status
        string notes
        datetime created_at
        datetime updated_at
        string google_calendar_event_id
    }
    
    BookingRule {
        int id PK
        string name
        string description
        int max_duration_hours
        int advance_booking_days
        boolean requires_approval
        datetime created_at
    }
```

## 🔐 Authentication Flow

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Django
    participant GoogleOAuth
    participant Database
    
    User->>Frontend: Click "Sign in with Google"
    Frontend->>Django: Redirect to /accounts/login/
    Django->>GoogleOAuth: OAuth2 Authorization Request
    GoogleOAuth->>User: Google Login Page
    User->>GoogleOAuth: Enter Credentials
    GoogleOAuth->>Django: Authorization Code
    Django->>GoogleOAuth: Exchange Code for Token
    GoogleOAuth->>Django: Access Token + User Info
    Django->>Database: Create/Update User
    Database->>Django: User Object
    Django->>Frontend: Set Session + Redirect
    Frontend->>User: Dashboard
```

## 📥 Booking Creation Flow

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Django
    participant AI
    participant Database
    participant Calendar
    participant Email
    participant Telegram
    
    User->>Frontend: "I need a room tomorrow 2pm"
    Frontend->>Django: POST /chatbot/chat/
    Django->>AI: Process Message
    AI->>AI: Detect Booking Intent
    AI->>Database: find_available_rooms()
    Database->>AI: Available Rooms List
    AI->>Django: Preview Response with Room
    Django->>Frontend: Display Preview + Confirm Button
    Frontend->>User: Show Room Preview
    
    User->>Frontend: Click "Confirm Booking"
    Frontend->>Django: POST /confirm/
    Django->>Database: Check Availability
    Database->>Django: Confirmed Available
    Django->>Database: Create Booking
    Database->>Django: Booking Created
    Django->>Calendar: Add to Google Calendar
    Calendar->>Django: Event Created
    Django->>Email: Send Confirmation Email
    Django->>Telegram: Send Notification
    Django->>Frontend: Success Response
    Frontend->>User: "Booking Confirmed!"
```

## 🏗️ Technology Stack

### Backend
- **Framework**: Django 4.x
- **Language**: Python 3.13
- **Database**: MySQL
- **Cache**: Django Cache Framework
- **Async**: ASGI with async views

### AI/ML
- **AI Framework**: Semantic Kernel
- **LLM Provider**: Groq
- **Model**: Llama 3.1 8B Instant
- **Capabilities**: Function calling, natural language processing

### Frontend
- **Templates**: Django Templates
- **CSS**: Custom CSS + Bootstrap
- **JavaScript**: Vanilla JS + jQuery
- **Icons**: Font Awesome

### External APIs
- **Authentication**: Google OAuth 2.0
- **Calendar**: Google Calendar API
- **Notifications**: Telegram Bot API
- **Email**: SMTP (Gmail)

### DevOps
- **Deployment**: PythonAnywhere / Render
- **Container**: Docker (optional)
- **Version Control**: Git

## 📁 Project Structure

```
RoomBooking/
├── accounts/              # User management app
│   ├── models.py         # User model
│   ├── views.py          # Auth views
│   ├── forms.py          # User forms
│   └── adapters.py       # OAuth adapters
│
├── booking/              # Room booking app
│   ├── models.py         # Room, Booking, BookingRule
│   ├── views.py          # Booking CRUD
│   ├── api_views.py      # REST API
│   ├── admin_views.py    # Admin dashboard
│   ├── google_calendar.py # Calendar integration
│   ├── email_utils.py    # Email service
│   └── telegram_notifications.py
│
├── chatbot/              # AI chatbot app
│   ├── views.py          # Chat endpoint
│   └── apps.py           # Chat agent initialization
│
├── ai/                   # AI components
│   ├── kernel_config.py  # Semantic Kernel setup
│   ├── booking_automation.py # Booking logic
│   └── plugins/
│       └── room_booking_plugin.py # SK plugin
│
├── templates/            # HTML templates
│   ├── UserPage/
│   ├── AdminPage/
│   └── SignIn-RegisterPage/
│
├── static/               # Static assets
│   ├── css/
│   ├── js/
│   └── images/
│
└── room_booking_system/  # Main project
    ├── settings.py       # Django settings
    ├── urls.py           # URL routing
    └── wsgi.py           # WSGI config
```

## 🔒 Security Features

1. **Authentication**
   - Google OAuth 2.0 integration
   - Session-based authentication
   - CSRF protection

2. **Authorization**
   - Role-based access control (User/Admin)
   - Booking ownership validation
   - Admin-only endpoints

3. **Data Protection**
   - SQL injection prevention (Django ORM)
   - XSS protection (Django templates)
   - Secure password handling

4. **API Security**
   - CORS configuration
   - Rate limiting (via Groq)
   - Input validation

## 🚀 Deployment Architecture

```mermaid
flowchart TB
    subgraph Production["Production Environment"]
        LB["Load Balancer"]
        
        subgraph Servers["Application Servers"]
            App1["Django Server 1"]
            App2["Django Server 2"]
        end
        
        subgraph Data["Data Layer"]
            DB["MySQL Database<br/>(Primary)"]
            DBReplica["MySQL Database<br/>(Replica)"]
            Cache["Redis Cache"]
        end
        
        subgraph Static["Static Files"]
            CDN["CDN / S3"]
        end
    end
    
    Internet["🌐 Internet"] --> LB
    LB --> App1
    LB --> App2
    
    App1 --> DB
    App2 --> DB
    DB --> DBReplica
    
    App1 --> Cache
    App2 --> Cache
    
    App1 --> CDN
    App2 --> CDN
    
    style Production fill:#e1f5ff
    style Servers fill:#f3e5f5
    style Data fill:#fce4ec
    style Static fill:#fff4e6
```

## 📈 Scalability Considerations

1. **Horizontal Scaling**: Multiple Django servers behind load balancer
2. **Database Replication**: Master-slave MySQL setup
3. **Caching**: Redis for session and query caching
4. **CDN**: Static assets served via CDN
5. **Async Processing**: Background tasks for emails/notifications
6. **API Rate Limiting**: Prevent abuse of AI chatbot

## 🔧 Key Features

✅ **User Management**
- Google OAuth integration
- Profile management
- Department/Faculty organization

✅ **Room Booking**
- Real-time availability checking
- Conflict prevention
- Booking rules enforcement
- Google Calendar sync

✅ **AI Chatbot**
- Natural language booking
- Database query integration
- Function calling for room search
- Conversational interface

✅ **Admin Dashboard**
- Room management
- Booking oversight
- User management
- Analytics

✅ **Notifications**
- Email confirmations
- Telegram alerts
- Calendar invites

✅ **API**
- RESTful endpoints
- JSON responses
- CORS support

---

**Version**: 2.0  
**Last Updated**: January 17, 2026  
**Architecture Type**: Monolithic with Microservice AI Layer
