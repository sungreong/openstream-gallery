import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Menu,
  MenuItem,
} from '@mui/material';
import { AccountCircle, Add, VpnKey, Settings, MonitorHeart, AdminPanelSettings } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const Navbar = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [anchorEl, setAnchorEl] = React.useState(null);

  const handleMenu = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
    handleClose();
    navigate('/login');
  };

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography
          variant="h6"
          component="div"
          sx={{ flexGrow: 1, cursor: 'pointer' }}
          onClick={() => navigate('/dashboard')}
        >
          Streamlit Platform
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button
            color="inherit"
            startIcon={<Add />}
            onClick={() => navigate('/apps/new')}
          >
            새 앱 만들기
          </Button>
          
          <Button
            color="inherit"
            startIcon={<VpnKey />}
            onClick={() => navigate('/git-credentials')}
          >
            Git 인증
          </Button>

          <Button
            color="inherit"
            startIcon={<Settings />}
            onClick={() => navigate('/nginx-management')}
          >
            Nginx 관리
          </Button>

          <Button
            color="inherit"
            startIcon={<MonitorHeart />}
            onClick={() => navigate('/celery-monitor')}
          >
            Celery 모니터
          </Button>

          {user?.is_admin && (
            <Button
              color="inherit"
              startIcon={<AdminPanelSettings />}
              onClick={() => navigate('/admin')}
              sx={{ 
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.2)'
                }
              }}
            >
              관리자 패널
            </Button>
          )}

          <div>
            <IconButton
              size="large"
              aria-label="account of current user"
              aria-controls="menu-appbar"
              aria-haspopup="true"
              onClick={handleMenu}
              color="inherit"
            >
              <AccountCircle />
            </IconButton>
            <Menu
              id="menu-appbar"
              anchorEl={anchorEl}
              anchorOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              keepMounted
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              open={Boolean(anchorEl)}
              onClose={handleClose}
            >
              <MenuItem disabled>
                <Typography variant="body2">
                  {user?.username} {user?.is_admin && '(관리자)'}
                </Typography>
              </MenuItem>
              <MenuItem onClick={handleLogout}>로그아웃</MenuItem>
            </Menu>
          </div>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar; 