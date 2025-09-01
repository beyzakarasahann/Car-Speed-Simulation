# 🚗 Car Speed Simulation

🌐 **Live Demo**: [speedsimulator.tech](https://13.51.157.65)

## 📖 Project Overview

**Car Speed Simulation** is a comprehensive vehicle simulation platform that combines real-world routing, physics-based speed modeling, and advanced GPS fusion techniques. The system simulates realistic vehicle behavior on actual road networks, taking into account elevation changes, road grades, traffic conditions, and vehicle dynamics.

### ✨ Key Features

- **🗺️ Real-World Route Planning**: Integration with HERE Maps and OpenRouteService APIs
- **🎯 Intelligent Speed Planning**: Elevation-aware target speed calculation based on road type and conditions
- **🧮 Physics Engine**: C++ based realistic vehicle dynamics with acceleration, braking, and gear modeling
- **📊 Extended Kalman Filter (EKF)**: GPS and motion sensor fusion for smooth position tracking
- **🌐 Interactive Web Interface**: Real-time 3D visualization with React Three Fiber and Leaflet maps
- **📱 Responsive Design**: Modern UI with Tailwind CSS and Framer Motion animations
- **🔄 Real-time Telemetry**: Live vehicle data including speed, acceleration, heading, and road conditions

### 🎮 Demo

The application provides an interactive web interface where users can:
- Select start and end points on a map
- Watch real-time vehicle simulation with physics-based movement
- Monitor telemetry data including speed, acceleration, elevation, and road grade
- View 3D vehicle models with realistic motion

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │  C++ Physics    │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   Engine        │
│                 │    │                 │    │                 │
│ • React 3D      │    │ • Route Planning│    │ • Vehicle Dynamics
│ • Interactive   │    │ • GPS Fusion    │    │ • Gear Modeling │
│   Maps          │    │ • Elevation API │    │ • Realistic     │
│ • Real-time UI  │    │ • Physics Bridge│    │   Physics       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Technology Stack

### Frontend
- **Framework**: Next.js 15.4.5 with TypeScript
- **3D Graphics**: React Three Fiber & Three.js
- **Maps**: React Leaflet & Leaflet.js
- **UI/UX**: Tailwind CSS 4.0 & Framer Motion
- **Build Tool**: Modern ES modules with optimized bundling

### Backend
- **Framework**: FastAPI (high-performance async Python API)
- **Language**: Python 3.12+
- **Physics**: C++ engine with CMake build system
- **APIs**: HERE Maps, OpenRouteService
- **Data Processing**: NumPy, SciPy for scientific computing

### Core Services
- **Route Planning**: HERE Maps API integration
- **Elevation Data**: Multi-source elevation APIs
- **GPS Fusion**: Extended Kalman Filter implementation
- **Physics Simulation**: Custom C++ vehicle dynamics engine
- **Real-time Communication**: WebSocket support for live updates

## 📦 Installation

### Prerequisites

Ensure you have the following installed:
- **Python 3.12+** - [Download Python](https://python.org/downloads/)
- **Node.js 18+** - [Download Node.js](https://nodejs.org/)
- **CMake** - [Install CMake](https://cmake.org/install/) (for C++ physics engine)
- **Git** - [Install Git](https://git-scm.com/downloads)

### Quick Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/username/car-speed-simulation.git
   cd car-speed-simulation
   ```

2. **Run the automated setup script**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

   This script will:
   - Create Python virtual environment
   - Install all Python dependencies
   - Install Node.js dependencies
   - Build the C++ physics engine
   - Verify all components

### Manual Installation

If you prefer manual installation:

#### Backend Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Build C++ physics engine
cd backend/cpp
mkdir -p build && cd build
cmake ..
make
cd ../../..
```

#### Frontend Setup
```bash
# Install Node.js dependencies
cd frontend
npm install
cd ..
```

## 🚀 Running the Application

### Development Mode

1. **Start the backend server**
   ```bash
   source venv/bin/activate
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the frontend development server** (in a new terminal)
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Production Deployment

```bash
# Build frontend for production
cd frontend
npm run build
npm start

# Run backend in production mode
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# API Keys (required for full functionality)
HERE_API_KEY=your_here_maps_api_key
ORS_API_KEY=your_openrouteservice_api_key

# Physics Engine Settings
USE_CPP_PHYSICS=true
PHYSICS_ENGINE_PATH=./cpp/build/physics_engine

# Logging
LOG_LEVEL=INFO

# CORS Settings (for production)
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Getting API Keys

1. **HERE Maps API**: [HERE Developer Portal](https://developer.here.com/)
2. **OpenRouteService**: [ORS API Dashboard](https://openrouteservice.org/dev/#/signup)

## 📚 API Documentation

### Core Endpoints

#### Route Planning
```http
POST /snap-to-road
Content-Type: application/json

{
  "coordinates": [[lat1, lon1], [lat2, lon2]]
}
```

#### Speed Simulation
```http
POST /calculate-route-speed
Content-Type: application/json

{
  "start": [lat, lon],
  "end": [lat, lon],
  "vehicle_type": "car"
}
```

#### Elevation Data
```http
GET /elevation?lat={lat}&lon={lon}
```

### Response Examples

**Route Response:**
```json
{
  "route": {
    "coordinates": [[lat, lon], ...],
    "distance_km": 15.2,
    "duration_minutes": 18.5,
    "elevation_profile": [...]
  },
  "simulation": {
    "speed_profile": [...],
    "physics_data": [...],
    "waypoints": [...]
  }
}
```

## 🎛️ Advanced Features

### Physics Engine Parameters

The C++ physics engine simulates realistic vehicle behavior:

```cpp
struct VehicleParams {
    double mass_kg = 1400.0;           // Vehicle mass
    double frontal_area_m2 = 2.1;      // Frontal area
    double drag_coefficient = 0.28;    // Aerodynamic drag
    double rolling_resistance = 0.012; // Rolling resistance
    double max_engine_power_kw = 125.0; // Engine power
    double max_torque_nm = 220.0;       // Maximum torque
};
```

### EKF Sensor Fusion

The Extended Kalman Filter combines:
- GPS position data
- IMU acceleration and gyroscope readings
- Vehicle odometry
- Map matching corrections

### Smart Speed Planning

The system calculates target speeds based on:
- Road functional class (highway, arterial, local)
- Elevation changes and road grade
- Curve analysis and geometry
- Traffic conditions (when available)
- Vehicle capabilities

## 🧪 Development

### Project Structure

```
car-speed-simulation/
├── frontend/                 # Next.js React application
│   ├── app/                 # App router pages
│   ├── components/          # React components
│   ├── hooks/              # Custom React hooks
│   └── utils/              # Frontend utilities
├── backend/                 # FastAPI Python backend
│   ├── app/
│   │   ├── api/            # API route handlers
│   │   ├── core/           # Core configuration
│   │   ├── services/       # Business logic services
│   │   └── utils/          # Backend utilities
│   └── cpp/                # C++ physics engine
├── requirements.txt        # Python dependencies
├── setup.sh               # Automated setup script
└── README.md              # This file
```

### Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# Physics engine tests
cd backend/cpp/build
./physics_engine --test
```

### Code Quality

The project includes:
- ESLint configuration for TypeScript
- Black and isort for Python formatting
- Type hints throughout Python code
- Comprehensive error handling

## 🐛 Troubleshooting

### Common Issues

**1. Physics engine build fails**
```bash
# Install CMake and build tools
sudo apt-get install cmake build-essential  # Ubuntu/Debian
brew install cmake                          # macOS
```

**2. Frontend build errors**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**3. Backend import errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

**4. API key errors**
- Verify API keys are correctly set in `.env`
- Check API key quotas and permissions
- Ensure CORS settings allow your domain

### Performance Optimization

- Use production builds for deployment
- Enable compression in web server
- Optimize map tile caching
- Consider CDN for static assets

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines

- Follow TypeScript/Python type hints
- Add tests for new features
- Update documentation for API changes
- Use meaningful commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Credits

**Developed by Beyza Karaşahan**

### Acknowledgments

- HERE Maps for routing and geocoding services
- OpenRouteService for additional routing capabilities
- React Three Fiber community for 3D rendering insights
- FastAPI team for the excellent Python framework

## 📞 Support

- **Email**: beyza590beyza@gmail.com

---

<div align="center">
  <sub>Built with ❤️ by Beyza Karaşahan</sub>
</div>
