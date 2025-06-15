import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Container } from '@mui/material';

import { useAuth } from './contexts/AuthContext';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import AppDetail from './pages/AppDetail';
import CreateApp from './pages/CreateApp';
import GitCredentials from './pages/GitCredentials';
import NginxManagement from './pages/NginxManagement';
import CeleryMonitor from './pages/CeleryMonitor';
import AdminPanel from './pages/AdminPanel';

function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>로딩 중...</div>;
  }

  return (
    <div className="App">
      {user && <Navbar />}
      <Container maxWidth="lg" sx={{ mt: user ? 4 : 0, mb: 4 }}>
        <Routes>
          <Route 
            path="/login" 
            element={user ? <Navigate to="/dashboard" /> : <Login />} 
          />
          <Route 
            path="/register" 
            element={user ? <Navigate to="/dashboard" /> : <Register />} 
          />
          <Route 
            path="/dashboard" 
            element={user ? <Dashboard /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/apps/new" 
            element={user ? <CreateApp /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/apps/:id" 
            element={user ? <AppDetail /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/git-credentials" 
            element={user ? <GitCredentials /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/nginx-management" 
            element={user ? <NginxManagement /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/celery-monitor" 
            element={user ? <CeleryMonitor /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/admin" 
            element={user?.is_admin ? <AdminPanel /> : <Navigate to="/dashboard" />} 
          />
          <Route 
            path="/" 
            element={<Navigate to={user ? "/dashboard" : "/login"} />} 
          />
        </Routes>
      </Container>
    </div>
  );
}

export default App;