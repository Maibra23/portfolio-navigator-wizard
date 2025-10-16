# Portfolio Navigator Wizard 🚀

A modern web application that helps users create and optimize their investment portfolios through an interactive wizard interface.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [What This App Does](#what-this-app-does)
- [How to Run the App](#how-to-run-the-app)
- [Project Structure](#project-structure)
- [Adding New Features](#adding-new-features)
- [Troubleshooting](#troubleshooting)
- [Deployment](#deployment)

## 🚀 Quick Start

### Prerequisites
Before running the app, make sure you have:
- **Node.js** (version 18 or higher)
- **Python** (version 3.8 or higher)
- **Git** (for cloning the repository)

### One-Command Setup
```bash
# Clone the repository
git clone <YOUR_REPOSITORY_URL>
cd portfolio-navigator-wizard

# Install dependencies and start the app
make dev
```

That's it! Your app will be running at **http://localhost:8080**

## 🎯 What This App Does

The Portfolio Navigator Wizard is a step-by-step tool that helps users:

1. **Welcome & Introduction** - Learn about the portfolio creation process
2. **Risk Profiling** - Determine your investment risk tolerance (Very Conservative to Very Aggressive)
3. **Capital Input** - Specify how much money you want to invest
4. **Stock Selection** - Choose which stocks to include in your portfolio
5. **Portfolio Optimization** - Get optimized allocation recommendations
6. **Stress Testing** - Test how your portfolio performs under different market conditions

### Current Features
- ✅ Interactive wizard interface with progress tracking
- ✅ Advanced risk profile assessment with 5 categories
- ✅ Capital amount input with validation
- ✅ **Enhanced Portfolio Construction** with:
  - Professional portfolio recommendations based on risk profile
  - Custom portfolio builder with allocation sliders
  - Real-time portfolio analytics (Risk, Return, Diversification Score, Sharpe Ratio)
  - Efficient Frontier visualization chart
  - Sector diversification suggestions
  - Live allocation tracking with dollar amounts
- ✅ **Redis-First Data Architecture** with:
  - Instant cached data access (< 5ms response times)
  - S&P 500 + Nasdaq 100 ticker coverage (~600 stocks)
  - Automatic cache warming and background refresh
  - Strategy portfolio pre-generation and optimization
- ✅ **Advanced Portfolio Management** with:
  - Auto-regeneration service for portfolio freshness
  - Strategy portfolio buckets with TTL management
  - Portfolio analytics and performance metrics
  - Cache status monitoring and health checks
- ✅ Real-time data updates and responsive design

### Planned Features
- 🔄 Portfolio optimization algorithms
- 🔄 Stress testing scenarios
- 🔄 Historical performance analysis
- 🔄 Export portfolio reports

## 🖥️ How to Run the App

### Method 1: Easy Setup (Recommended)
```bash
make dev
```
This single command:
- Starts the backend server (FastAPI) on port 8000
- Starts the frontend server (React) on port 8080
- Sets up automatic reloading when you make changes

### Method 2: Manual Setup

#### Step 1: Start the Backend
```bash
# Navigate to backend directory
cd backend

# Activate Python virtual environment
source venv/bin/activate

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Step 2: Start the Frontend (in a new terminal)
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start the development server
npm run dev
```

### Access Your App
- **Frontend (Main App)**: http://localhost:8080
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Enhanced Portfolio Status**: http://localhost:8000/api/enhanced-portfolio/status
- **Cache Status**: http://localhost:8000/api/enhanced-portfolio/cache-status

## 📁 Project Structure

```
portfolio-navigator-wizard/
├── frontend/                 # React frontend application
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   │   ├── ui/          # Basic UI components (buttons, cards, etc.)
│   │   │   ├── wizard/      # Wizard-specific components
│   │   │   │   ├── StockSelection.tsx      # Enhanced portfolio construction
│   │   │   │   ├── EfficientFrontierChart.tsx  # Risk/Return visualization
│   │   │   │   └── ...      # Other wizard steps
│   │   │   └── PortfolioWizard.tsx  # Main wizard component
│   │   ├── pages/           # Page components
│   │   ├── hooks/           # Custom React hooks
│   │   └── lib/             # Utility functions
│   ├── package.json         # Frontend dependencies
│   └── vite.config.ts       # Frontend build configuration
├── backend/                  # FastAPI backend application
│   ├── routers/             # API route definitions
│   │   ├── portfolio.py     # Portfolio-related API endpoints
│   │   ├── cookie_demo.py   # Example API endpoints
│   │   └── strategy_buckets.py # Strategy portfolio endpoints
│   ├── models/              # Data models and schemas
│   ├── utils/               # Enhanced portfolio system utilities
│   │   ├── redis_portfolio_manager.py # Redis portfolio management
│   │   ├── portfolio_auto_regeneration_service.py # Auto-refresh service
│   │   ├── strategy_portfolio_optimizer.py # Strategy optimization
│   │   ├── redis_first_data_service.py # Redis-first data access
│   │   ├── enhanced_portfolio_generator.py # Portfolio generation
│   │   ├── port_analytics.py # Portfolio analytics
│   │   └── ...              # Other utility modules
│   ├── scripts/             # Scheduled tasks and maintenance
│   ├── main.py              # Enhanced backend application with lifespan management
│   └── requirements.txt     # Python dependencies
├── Makefile                 # Build and run commands
└── README.md               # This file
```

## 🛠️ Adding New Features

### Frontend Changes (React/TypeScript)

#### Adding a New Wizard Step

1. **Create the step component** in `frontend/src/components/wizard/`:
```typescript
// frontend/src/components/wizard/NewStep.tsx
import { Button } from '@/components/ui/button';

interface NewStepProps {
  onNext: () => void;
  onPrev: () => void;
  onDataUpdate: (data: any) => void;
  currentData: any;
}

export const NewStep = ({ onNext, onPrev, onDataUpdate, currentData }: NewStepProps) => {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Your New Step</h2>
      {/* Add your form elements here */}
      
      <div className="flex gap-4">
        <Button variant="outline" onClick={onPrev}>Previous</Button>
        <Button onClick={onNext}>Next</Button>
      </div>
    </div>
  );
};
```

2. **Add the step to the wizard** in `frontend/src/components/PortfolioWizard.tsx`:
```typescript
// Add to STEPS array
const STEPS = [
  // ... existing steps
  { id: 'new-step', title: 'New Step', icon: YourIcon },
];

// Add to renderStep function
case 'new-step':
  return (
    <NewStep
      onNext={nextStep}
      onPrev={prevStep}
      onDataUpdate={(data) => updateWizardData(data)}
      currentData={wizardData}
    />
  );
```

3. **Update the data interface**:
```typescript
export interface WizardData {
  // ... existing fields
  newField: string; // Add your new data field
}
```

#### Adding a New Page

1. **Create the page component** in `frontend/src/pages/`:
```typescript
// frontend/src/pages/NewPage.tsx
const NewPage = () => {
  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold">New Page</h1>
      {/* Your page content */}
    </div>
  );
};

export default NewPage;
```

2. **Add the route** in `frontend/src/App.tsx`:
```typescript
import NewPage from "./pages/NewPage";

// Add inside Routes
<Route path="/new-page" element={<NewPage />} />
```

### Backend Changes (FastAPI/Python)

#### Adding a New API Endpoint

1. **Create a new router** in `backend/routers/`:
```python
# backend/routers/new_feature.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/new-feature", tags=["new-feature"])

class NewFeatureRequest(BaseModel):
    data: str

class NewFeatureResponse(BaseModel):
    result: str

@router.post("", response_model=NewFeatureResponse)
def new_feature_endpoint(request: NewFeatureRequest):
    # Your logic here
    return NewFeatureResponse(result=f"Processed: {request.data}")
```

2. **Register the router** in `backend/main.py`:
```python
from routers import new_feature

# Add this line with other router includes
app.include_router(new_feature.router)
```

#### Adding a New Data Model

1. **Create the model** in `backend/models/`:
```python
# backend/models/new_model.py
from pydantic import BaseModel
from typing import List, Optional

class NewModel(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    tags: List[str] = []
```

### Styling Changes (Tailwind CSS)

The app uses Tailwind CSS for styling. You can:

1. **Add custom styles** in `frontend/src/index.css`
2. **Use Tailwind classes** directly in components
3. **Create custom components** in `frontend/src/components/ui/`

### Database Changes

Currently, the app uses in-memory storage. To add a database:

1. **Install database dependencies** in `backend/requirements.txt`
2. **Create database models** in `backend/models/`
3. **Add database connection** in `backend/main.py`

## 🔧 Troubleshooting

### Common Issues

#### "npm: command not found"
```bash
# Install Node.js using nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm install node
```

#### "uvicorn: command not found"
```bash
# Activate virtual environment and install dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

#### Port already in use
```bash
# Find and kill processes using the ports
lsof -ti:8000 | xargs kill -9
lsof -ti:8080 | xargs kill -9
```

#### Frontend not connecting to backend
- Check that both servers are running
- Verify the proxy configuration in `frontend/vite.config.ts`
- Check browser console for CORS errors

#### Redis connection issues
- Ensure Redis server is running (`redis-server`)
- Check Redis connection in backend logs
- Verify Redis health at `/health` endpoint

#### Portfolio generation issues
- Check portfolio cache status at `/api/enhanced-portfolio/cache-status`
- Verify strategy portfolios are generated at `/api/enhanced-portfolio/buckets`
- Use manual regeneration endpoint if needed: `POST /api/enhanced-portfolio/regenerate`

### Getting Help

1. **Check the logs** - Both frontend and backend show detailed error messages
2. **Restart the servers** - Stop and restart with `make dev`
3. **Clear browser cache** - Hard refresh (Ctrl+F5 or Cmd+Shift+R)
4. **Check file permissions** - Ensure you have read/write access to the project

## 🚀 Deployment

### Development Deployment
```bash
# Build the frontend
cd frontend
npm run build

# Copy to backend static directory
cp -r dist ../backend/static

# Start production server
cd ../backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Production Deployment
1. **Set up a production server** (AWS, DigitalOcean, Heroku, etc.)
2. **Install dependencies** on the server
3. **Build the frontend** and copy to backend static directory
4. **Configure environment variables**
5. **Set up a reverse proxy** (nginx) if needed
6. **Use a process manager** (PM2, systemd) for the backend

## 📚 Learning Resources

### Frontend (React/TypeScript)
- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)

### Backend (FastAPI/Python)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Python Documentation](https://docs.python.org/)

### General
- [Git Documentation](https://git-scm.com/doc)
- [Node.js Documentation](https://nodejs.org/docs/)

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Test your changes** (`make test`)
5. **Commit your changes** (`git commit -m 'Add amazing feature'`)
6. **Push to the branch** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request**

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Need help?** Check the troubleshooting section above or create an issue in the repository.
