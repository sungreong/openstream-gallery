import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel,
  Chip,
  Alert,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  Tooltip,
  Snackbar
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  People as PeopleIcon,
  Storage as DockerIcon,
  Settings as SettingsIcon,
  CleaningServices as CleaningServicesIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '';

// 간단한 에러 메시지 추출 함수
const getErrorMessage = (error) => {
  if (error?.response?.data?.detail) {
    return error.response.data.detail;
  }
  if (error?.message) {
    return error.message;
  }
  return '알 수 없는 오류가 발생했습니다';
};

// API 함수들
const adminAPI = {
  // 통계 정보
  getStats: async () => {
    const response = await fetch(`${API_BASE_URL}/api/admin/stats`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    if (!response.ok) throw new Error('통계 정보를 가져올 수 없습니다');
    return response.json();
  },

  // 사용자 관리
  getUsers: async () => {
    const response = await fetch(`${API_BASE_URL}/api/admin/users`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    if (!response.ok) throw new Error('사용자 목록을 가져올 수 없습니다');
    return response.json();
  },

  updateUser: async ({ userId, userData }) => {
    const response = await fetch(`${API_BASE_URL}/api/admin/users/${userId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify(userData)
    });
    if (!response.ok) throw new Error('사용자 정보를 업데이트할 수 없습니다');
    return response.json();
  },

  deleteUser: async (userId) => {
    const response = await fetch(`${API_BASE_URL}/api/admin/users/${userId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    if (!response.ok) throw new Error('사용자를 삭제할 수 없습니다');
    return response.json();
  },

  // Dockerfile 관리
  getDockerfiles: async () => {
    const response = await fetch(`${API_BASE_URL}/api/admin/dockerfiles`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    if (!response.ok) throw new Error('Dockerfile 목록을 가져올 수 없습니다');
    return response.json();
  },

  getDockerfileContent: async (type) => {
    const response = await fetch(`${API_BASE_URL}/api/admin/dockerfiles/${type}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    if (!response.ok) throw new Error('Dockerfile 내용을 가져올 수 없습니다');
    return response.json();
  },

  updateDockerfile: async ({ type, content }) => {
    const response = await fetch(`${API_BASE_URL}/api/admin/dockerfiles/${type}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ content })
    });
    if (!response.ok) throw new Error('Dockerfile을 업데이트할 수 없습니다');
    return response.json();
  },

  createDockerfile: async ({ type, content }) => {
    const response = await fetch(`${API_BASE_URL}/api/admin/dockerfiles/${type}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ content })
    });
    if (!response.ok) throw new Error('Dockerfile을 생성할 수 없습니다');
    return response.json();
  },

  deleteDockerfile: async (type) => {
    const response = await fetch(`${API_BASE_URL}/api/admin/dockerfiles/${type}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    if (!response.ok) throw new Error('Dockerfile을 삭제할 수 없습니다');
    return response.json();
  },

  // 시스템 관리
  systemCleanup: async () => {
    const response = await fetch(`${API_BASE_URL}/api/admin/system/cleanup`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    });
    if (!response.ok) throw new Error('시스템 정리를 실행할 수 없습니다');
    return response.json();
  }
};

function TabPanel({ children, value, index, ...other }) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`admin-tabpanel-${index}`}
      aria-labelledby={`admin-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

// 사용자 관리 컴포넌트
function UserManagement() {
  const [editingUser, setEditingUser] = useState(null);
  const [editForm, setEditForm] = useState({});
  const queryClient = useQueryClient();

  const { data: users, isLoading, error } = useQuery({
    queryKey: ['admin-users'],
    queryFn: adminAPI.getUsers
  });

  const updateUserMutation = useMutation({
    mutationFn: adminAPI.updateUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setEditingUser(null);
      setEditForm({});
    }
  });

  const deleteUserMutation = useMutation({
    mutationFn: adminAPI.deleteUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    }
  });

  const handleEdit = (user) => {
    setEditingUser(user.id);
    setEditForm({
      username: user.username,
      email: user.email,
      is_admin: user.is_admin
    });
  };

  const handleSave = () => {
    updateUserMutation.mutate({
      userId: editingUser,
      userData: editForm
    });
  };

  const handleDelete = (userId) => {
    if (window.confirm('정말로 이 사용자를 삭제하시겠습니까?')) {
      deleteUserMutation.mutate(userId);
    }
  };

  if (isLoading) return <Typography>로딩 중...</Typography>;
  if (error) return <Alert severity="error">{getErrorMessage(error)}</Alert>;

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>사용자명</TableCell>
            <TableCell>이메일</TableCell>
            <TableCell>관리자</TableCell>
            <TableCell>생성일</TableCell>
            <TableCell>작업</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {users?.map((user) => (
            <TableRow key={user.id}>
              <TableCell>{user.id}</TableCell>
              <TableCell>
                {editingUser === user.id ? (
                  <TextField
                    size="small"
                    value={editForm.username}
                    onChange={(e) => setEditForm({ ...editForm, username: e.target.value })}
                  />
                ) : (
                  user.username
                )}
              </TableCell>
              <TableCell>
                {editingUser === user.id ? (
                  <TextField
                    size="small"
                    type="email"
                    value={editForm.email}
                    onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                  />
                ) : (
                  user.email
                )}
              </TableCell>
              <TableCell>
                {editingUser === user.id ? (
                  <FormControlLabel
                    control={
                      <Switch
                        checked={editForm.is_admin}
                        onChange={(e) => setEditForm({ ...editForm, is_admin: e.target.checked })}
                      />
                    }
                    label="관리자"
                  />
                ) : (
                  <Chip
                    label={user.is_admin ? '관리자' : '일반'}
                    color={user.is_admin ? 'primary' : 'default'}
                    size="small"
                  />
                )}
              </TableCell>
              <TableCell>{new Date(user.created_at).toLocaleDateString()}</TableCell>
              <TableCell>
                {editingUser === user.id ? (
                  <>
                    <IconButton onClick={handleSave} color="primary">
                      <SaveIcon />
                    </IconButton>
                    <IconButton onClick={() => setEditingUser(null)}>
                      <CancelIcon />
                    </IconButton>
                  </>
                ) : (
                  <>
                    <IconButton onClick={() => handleEdit(user)} color="primary">
                      <EditIcon />
                    </IconButton>
                    <IconButton onClick={() => handleDelete(user.id)} color="error">
                      <DeleteIcon />
                    </IconButton>
                  </>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

// Dockerfile 관리 컴포넌트
function DockerfileManagement() {
  const [selectedDockerfile, setSelectedDockerfile] = useState(null);
  const [editingContent, setEditingContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [newDockerfileType, setNewDockerfileType] = useState('');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const queryClient = useQueryClient();

  const { data: dockerfiles, isLoading, error } = useQuery({
    queryKey: ['admin-dockerfiles'],
    queryFn: adminAPI.getDockerfiles
  });

  const { data: dockerfileContent } = useQuery({
    queryKey: ['admin-dockerfile-content', selectedDockerfile],
    queryFn: () => adminAPI.getDockerfileContent(selectedDockerfile),
    enabled: !!selectedDockerfile
  });

  const updateDockerfileMutation = useMutation({
    mutationFn: adminAPI.updateDockerfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-dockerfiles'] });
      queryClient.invalidateQueries({ queryKey: ['admin-dockerfile-content'] });
      setIsEditing(false);
    }
  });

  const createDockerfileMutation = useMutation({
    mutationFn: adminAPI.createDockerfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-dockerfiles'] });
      setShowCreateDialog(false);
      setNewDockerfileType('');
      setEditingContent('');
    }
  });

  const deleteDockerfileMutation = useMutation({
    mutationFn: adminAPI.deleteDockerfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-dockerfiles'] });
      setSelectedDockerfile(null);
    }
  });

  useEffect(() => {
    if (dockerfileContent) {
      setEditingContent(dockerfileContent.content);
    }
  }, [dockerfileContent]);

  const handleSave = () => {
    updateDockerfileMutation.mutate({
      type: selectedDockerfile,
      content: editingContent
    });
  };

  const handleCreate = () => {
    createDockerfileMutation.mutate({
      type: newDockerfileType,
      content: editingContent
    });
  };

  const handleDelete = () => {
    if (window.confirm('정말로 이 Dockerfile을 삭제하시겠습니까?')) {
      deleteDockerfileMutation.mutate(selectedDockerfile);
    }
  };

  if (isLoading) return <Typography>로딩 중...</Typography>;
  if (error) return <Alert severity="error">{getErrorMessage(error)}</Alert>;

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={4}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Dockerfile 목록
            </Typography>
            {dockerfiles?.dockerfiles?.map((dockerfile) => (
              <Box key={dockerfile.type} sx={{ mb: 1 }}>
                <Button
                  variant={selectedDockerfile === dockerfile.type ? 'contained' : 'outlined'}
                  fullWidth
                  onClick={() => setSelectedDockerfile(dockerfile.type)}
                  sx={{ justifyContent: 'flex-start' }}
                >
                  {dockerfile.type}
                  {dockerfile.error && (
                    <Chip label="오류" color="error" size="small" sx={{ ml: 1 }} />
                  )}
                </Button>
              </Box>
            ))}
            <Button
              variant="outlined"
              fullWidth
              startIcon={<AddIcon />}
              onClick={() => setShowCreateDialog(true)}
              sx={{ mt: 2 }}
            >
              새 Dockerfile 생성
            </Button>
          </CardContent>
        </Card>
      </Grid>
      
      <Grid item xs={12} md={8}>
        {selectedDockerfile && (
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Dockerfile.{selectedDockerfile}
                </Typography>
                <Box>
                  {isEditing ? (
                    <>
                      <Button onClick={handleSave} color="primary" sx={{ mr: 1 }}>
                        저장
                      </Button>
                      <Button onClick={() => setIsEditing(false)}>
                        취소
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button onClick={() => setIsEditing(true)} color="primary" sx={{ mr: 1 }}>
                        편집
                      </Button>
                      <Button onClick={handleDelete} color="error">
                        삭제
                      </Button>
                    </>
                  )}
                </Box>
              </Box>
              
              <TextField
                multiline
                rows={20}
                fullWidth
                value={isEditing ? editingContent : dockerfileContent?.content || ''}
                onChange={(e) => setEditingContent(e.target.value)}
                disabled={!isEditing}
                variant="outlined"
                sx={{ fontFamily: 'monospace' }}
              />
            </CardContent>
          </Card>
        )}
      </Grid>

      {/* 새 Dockerfile 생성 다이얼로그 */}
      <Dialog open={showCreateDialog} onClose={() => setShowCreateDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>새 Dockerfile 생성</DialogTitle>
        <DialogContent>
          <TextField
            label="Dockerfile 타입"
            value={newDockerfileType}
            onChange={(e) => setNewDockerfileType(e.target.value)}
            fullWidth
            margin="normal"
            placeholder="예: custom, nodejs, python39 등"
          />
          <TextField
            label="Dockerfile 내용"
            multiline
            rows={15}
            value={editingContent}
            onChange={(e) => setEditingContent(e.target.value)}
            fullWidth
            margin="normal"
            variant="outlined"
            sx={{ fontFamily: 'monospace' }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCreateDialog(false)}>취소</Button>
          <Button onClick={handleCreate} color="primary" disabled={!newDockerfileType.trim()}>
            생성
          </Button>
        </DialogActions>
      </Dialog>
    </Grid>
  );
}

// 시스템 관리 컴포넌트
function SystemManagement() {
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const queryClient = useQueryClient();

  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: adminAPI.getStats
  });

  const cleanupMutation = useMutation({
    mutationFn: adminAPI.systemCleanup,
    onSuccess: (data) => {
      setSnackbar({
        open: true,
        message: '시스템 정리가 완료되었습니다',
        severity: 'success'
      });
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
    },
    onError: (error) => {
      setSnackbar({
        open: true,
        message: getErrorMessage(error),
        severity: 'error'
      });
    }
  });

  const handleCleanup = () => {
    if (window.confirm('시스템 정리를 실행하시겠습니까? 사용하지 않는 Docker 리소스들이 삭제됩니다.')) {
      cleanupMutation.mutate();
    }
  };

  if (isLoading) return <Typography>로딩 중...</Typography>;
  if (error) return <Alert severity="error">{getErrorMessage(error)}</Alert>;

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              시스템 통계
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="textSecondary">
                총 사용자: {stats?.total_users}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                총 앱: {stats?.total_apps}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                실행 중인 앱: {stats?.running_apps}
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Docker 정보
            </Typography>
            {stats?.docker_info?.error ? (
              <Alert severity="error">{stats.docker_info.error}</Alert>
            ) : (
              <Box>
                <Typography variant="body2" color="textSecondary">
                  실행 중인 컨테이너: {stats?.docker_info?.stats?.running_containers}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  총 컨테이너: {stats?.docker_info?.stats?.total_containers}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  총 이미지: {stats?.docker_info?.stats?.total_images}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  네트워크: {stats?.docker_info?.stats?.network}
                </Typography>
              </Box>
            )}
          </CardContent>
          <CardActions>
            <Button
              variant="contained"
              color="warning"
              startIcon={<CleaningServicesIcon />}
              onClick={handleCleanup}
              disabled={cleanupMutation.isLoading}
            >
              {cleanupMutation.isLoading ? '정리 중...' : '시스템 정리'}
            </Button>
          </CardActions>
        </Card>
      </Grid>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Grid>
  );
}

export default function AdminPanel() {
  const [tabValue, setTabValue] = useState(0);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          관리자 패널
        </Typography>
        <Typography variant="body1" color="textSecondary">
          시스템 관리 및 설정을 위한 관리자 전용 페이지입니다.
        </Typography>
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab icon={<PeopleIcon />} label="사용자 관리" />
          <Tab icon={<DockerIcon />} label="Dockerfile 관리" />
          <Tab icon={<SettingsIcon />} label="시스템 관리" />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        <UserManagement />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <DockerfileManagement />
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <SystemManagement />
      </TabPanel>
    </Container>
  );
} 