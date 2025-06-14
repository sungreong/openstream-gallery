import React, { useState, useEffect } from 'react';
import {
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Box,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  Fab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Badge
} from '@mui/material';
import { 
  PlayArrow, 
  Stop, 
  Delete, 
  Visibility, 
  Edit, 
  Settings, 
  Add, 
  Refresh,
  CleaningServices,
  Widgets,
  Apps as AppsIcon,
  Storage,
  PlayCircle,
  PauseCircle,
  OpenInNew,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import toast from 'react-hot-toast';
import api from '../services/api';

// 앱 URL 생성 함수
const getAppUrl = (subdomain) => {
  const baseUrl = process.env.REACT_APP_BASE_URL || 'http://localhost:1234';
  return `${baseUrl}/${subdomain}/`;
};

const Dashboard = () => {
  const [apps, setApps] = useState([]);
  const [dockerApps, setDockerApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dockerLoading, setDockerLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [deleteDialog, setDeleteDialog] = useState({ open: false, app: null });
  const [envDialog, setEnvDialog] = useState({ open: false, appId: null, envVars: {} });
  const [realtimeStatus, setRealtimeStatus] = useState({});
  const [lastStatusCheck, setLastStatusCheck] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    fetchApps();
    fetchDockerApps();
  }, []);

  const fetchApps = async () => {
    try {
      const response = await api.get('/api/apps/');
      setApps(response.data);
    } catch (error) {
      console.error('앱 목록 조회 실패:', error);
      setError('앱 목록을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const fetchDockerApps = async () => {
    try {
      const response = await api.get('/api/apps/docker/running');
      setDockerApps(response.data.data || []);
    } catch (error) {
      console.error('Docker 앱 목록 조회 실패:', error);
    } finally {
      setDockerLoading(false);
    }
  };

  // 실시간 상태 체크
  const fetchRealtimeStatus = async () => {
    try {
      const response = await api.get('/api/apps/realtime-status/all');
      if (response.data.success) {
        const statusMap = {};
        response.data.data.forEach(status => {
          statusMap[status.app_id] = status;
        });
        setRealtimeStatus(statusMap);
        setLastStatusCheck(new Date());
      }
    } catch (error) {
      console.error('실시간 상태 조회 실패:', error);
    }
  };

  // 자동 새로고침 설정
  useEffect(() => {
    if (autoRefresh && apps.length > 0) {
      const interval = setInterval(() => {
        fetchRealtimeStatus();
      }, 15000); // 15초마다 실시간 상태 체크

      return () => clearInterval(interval);
    }
  }, [autoRefresh, apps.length]);

  // 초기 실시간 상태 로드
  useEffect(() => {
    if (apps.length > 0) {
      fetchRealtimeStatus();
    }
  }, [apps]);

  const handleCleanupOrphanedContainers = async () => {
    try {
      const response = await api.post('/api/apps/docker/cleanup');
      toast.success(response.data.message);
      fetchDockerApps(); // 목록 새로고침
    } catch (error) {
      console.error('고아 컨테이너 정리 실패:', error);
      toast.error('고아 컨테이너 정리에 실패했습니다.');
    }
  };

  const getStatusColor = (status) => {
    switch (status.toLowerCase()) {
      case 'running': return 'success';
      case 'stopped': return 'error';
      case 'building': return 'warning';
      case 'error': return 'error';
      case 'exited': return 'default';
      default: return 'default';
    }
  };

  const getStatusText = (status) => {
    switch (status.toLowerCase()) {
      case 'running': return '실행 중';
      case 'stopped': return '중지됨';
      case 'building': return '빌드 중';
      case 'error': return '오류';
      case 'exited': return '종료됨';
      default: return status;
    }
  };

  // 앱 배포 뮤테이션
  const deployMutation = useMutation({
    mutationFn: async (appId) => {
      const response = await axios.post(`/api/apps/${appId}/deploy`, {});
      return response.data;
    },
    onSuccess: (data) => {
      toast.success('배포가 시작되었습니다.');
      queryClient.invalidateQueries({ queryKey: ['apps'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || '배포에 실패했습니다.');
    },
  });

  // 앱 중지 뮤테이션
  const stopMutation = useMutation({
    mutationFn: async (appId) => {
      const response = await axios.post(`/api/apps/${appId}/stop`);
      return response.data;
    },
    onSuccess: () => {
      toast.success('앱이 중지되었습니다.');
      queryClient.invalidateQueries({ queryKey: ['apps'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || '앱 중지에 실패했습니다.');
    },
  });

  // 앱 삭제 뮤테이션
  const deleteMutation = useMutation({
    mutationFn: async (appId) => {
      const response = await axios.delete(`/api/apps/${appId}`);
      return response.data;
    },
    onSuccess: () => {
      toast.success('앱이 삭제되었습니다.');
      queryClient.invalidateQueries({ queryKey: ['apps'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || '앱 삭제에 실패했습니다.');
    },
  });

  const handleDeploy = (appId) => {
    setEnvDialog({ open: true, appId, envVars: {} });
  };

  const handleDeployConfirm = () => {
    deployMutation.mutate(envDialog.appId);
    setEnvDialog({ open: false, appId: null, envVars: {} });
  };

  const handleStop = (appId) => {
    stopMutation.mutate(appId);
  };

  const handleDelete = (app) => {
    setDeleteDialog({ open: true, app });
  };

  const handleDeleteConfirm = () => {
    if (deleteDialog.app) {
      deleteMutation.mutate(deleteDialog.app.id);
    }
  };

  const addEnvVar = () => {
    const key = prompt('환경변수 키를 입력하세요:');
    if (key) {
      const value = prompt('환경변수 값을 입력하세요:');
      if (value !== null) {
        setEnvDialog(prev => ({
          ...prev,
          envVars: { ...prev.envVars, [key]: value }
        }));
      }
    }
  };

  const removeEnvVar = (key) => {
    setEnvDialog(prev => ({
      ...prev,
      envVars: Object.fromEntries(
        Object.entries(prev.envVars).filter(([k]) => k !== key)
      )
    }));
  };

  // 실제 상태 기반 상태 텍스트 및 색상
  const getActualStatusInfo = (app) => {
    const realtimeInfo = realtimeStatus[app.id];
    
    if (!realtimeInfo) {
      return {
        text: getStatusText(app.status),
        color: getStatusColor(app.status),
        isRealtime: false
      };
    }

    const actualStatus = realtimeInfo.actual_status;
    
    switch (actualStatus) {
      case 'running':
        return { text: '실행중', color: 'success', isRealtime: true };
      case 'stopped':
        return { text: '중지됨', color: 'default', isRealtime: true };
      case 'not_deployed':
        return { text: '미배포', color: 'default', isRealtime: true };
      case 'nginx_error':
        return { text: 'Nginx 오류', color: 'warning', isRealtime: true };
      case 'app_error':
        return { text: '앱 오류', color: 'error', isRealtime: true };
      case 'error':
        return { text: '오류', color: 'error', isRealtime: true };
      default:
        return { text: '확인중', color: 'default', isRealtime: true };
    }
  };

  // 상태 아이콘 렌더링
  const renderStatusIcon = (app) => {
    const realtimeInfo = realtimeStatus[app.id];
    
    if (!realtimeInfo) {
      return null;
    }

    const issues = [];
    
    if (!realtimeInfo.container_running) {
      issues.push('컨테이너 중지됨');
    }
    
    if (!realtimeInfo.nginx_config_valid) {
      issues.push('Nginx 설정 오류');
    }

    if (issues.length === 0) {
      return (
        <Tooltip title="모든 상태 정상">
          <CheckCircleIcon color="success" fontSize="small" />
        </Tooltip>
      );
    } else {
      return (
        <Tooltip title={`문제: ${issues.join(', ')}`}>
          <WarningIcon color="warning" fontSize="small" />
        </Tooltip>
      );
    }
  };

  const handleRefresh = () => {
    fetchApps();
    fetchDockerApps();
    fetchRealtimeStatus();
    toast.success('상태를 새로고침했습니다.');
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" mt={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        앱 목록을 불러오는데 실패했습니다.
      </Alert>
    );
  }

  const runningContainers = dockerApps.filter(app => app.status.toLowerCase().includes('running')).length;
  const stoppedContainers = dockerApps.length - runningContainers;

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          대시보드
        </Typography>
        <Stack direction="row" spacing={2} alignItems="center">
          {lastStatusCheck && (
            <Typography variant="caption" color="text.secondary">
              마지막 상태 확인: {lastStatusCheck.toLocaleTimeString()}
            </Typography>
          )}
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleRefresh}
            size="small"
          >
            새로고침
          </Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => navigate('/apps/create')}
          >
            새 앱 만들기
          </Button>
        </Stack>
      </Box>

      {/* 통계 카드들 */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="h6">
                    총 앱 수
                  </Typography>
                  <Typography variant="h4">
                    {apps.length}
                  </Typography>
                </Box>
                <AppsIcon color="primary" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="h6">
                    실행 중인 컨테이너
                  </Typography>
                  <Typography variant="h4" color="success.main">
                    {runningContainers}
                  </Typography>
                </Box>
                <PlayCircle color="success" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="h6">
                    중지된 컨테이너
                  </Typography>
                  <Typography variant="h4" color="warning.main">
                    {stoppedContainers}
                  </Typography>
                </Box>
                <PauseCircle color="warning" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="h6">
                    총 Docker 앱
                  </Typography>
                  <Typography variant="h4" color="info.main">
                    {dockerApps.length}
                  </Typography>
                </Box>
                <Widgets color="info" sx={{ fontSize: 40 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Docker 컨테이너 관리 섹션 */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h5" component="h2">
              🐳 Docker 컨테이너 관리
            </Typography>
            <Box>
              <Tooltip title="새로고침">
                <IconButton onClick={fetchDockerApps} disabled={dockerLoading}>
                  <Refresh />
                </IconButton>
              </Tooltip>
              <Tooltip title="고아 컨테이너 정리">
                <IconButton onClick={handleCleanupOrphanedContainers} color="error">
                  <CleaningServices />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          {dockerLoading ? (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress />
            </Box>
          ) : dockerApps.length === 0 ? (
            <Box textAlign="center" py={4}>
              <Typography variant="body1" color="textSecondary">
                실행 중인 Streamlit 앱이 없습니다.
              </Typography>
            </Box>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>앱 정보</TableCell>
                    <TableCell>상태</TableCell>
                    <TableCell>이미지</TableCell>
                    <TableCell>생성일</TableCell>
                    <TableCell>컨테이너 ID</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {dockerApps.map((app) => (
                    <TableRow key={app.container_id} hover>
                      <TableCell>
                        <Box>
                          <Typography variant="subtitle2" fontWeight="bold">
                            {app.app_name || app.name}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            {app.app_id ? `App ID: ${app.app_id}` : '라벨 없음'}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip 
                          label={getStatusText(app.status)} 
                          color={getStatusColor(app.status)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Tooltip title={app.image}>
                          <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                            {app.image}
                          </Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {new Date(app.created_at).toLocaleString('ko-KR')}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace">
                          {app.container_id.substring(0, 12)}...
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* 관리 카드들 */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={4}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent sx={{ flexGrow: 1 }}>
              <Box display="flex" alignItems="center" mb={2}>
                <Add color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">새 앱 만들기</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Git 저장소에서 새로운 Streamlit 앱을 배포하세요.
              </Typography>
            </CardContent>
            <CardActions>
              <Button
                variant="contained"
                fullWidth
                onClick={() => navigate('/apps/new')}
              >
                앱 만들기
              </Button>
            </CardActions>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent sx={{ flexGrow: 1 }}>
              <Box display="flex" alignItems="center" mb={2}>
                <Settings color="secondary" sx={{ mr: 1 }} />
                <Typography variant="h6">Nginx 관리</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Nginx 설정을 관리하고 도메인을 설정하세요.
              </Typography>
            </CardContent>
            <CardActions>
              <Button
                variant="outlined"
                fullWidth
                onClick={() => navigate('/nginx')}
              >
                Nginx 관리
              </Button>
            </CardActions>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent sx={{ flexGrow: 1 }}>
              <Box display="flex" alignItems="center" mb={2}>
                <Storage color="info" sx={{ mr: 1 }} />
                <Typography variant="h6">Celery 모니터</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                백그라운드 작업 상태를 모니터링하세요.
              </Typography>
            </CardContent>
            <CardActions>
              <Button
                variant="outlined"
                fullWidth
                onClick={() => navigate('/celery-monitor')}
              >
                모니터 보기
              </Button>
            </CardActions>
          </Card>
        </Grid>
      </Grid>

      {/* 앱 목록 */}
      {apps.length === 0 ? (
        <Card>
          <CardContent>
            <Box textAlign="center" py={4}>
              <Typography variant="h6" gutterBottom>
                아직 등록된 앱이 없습니다
              </Typography>
              <Typography variant="body2" color="text.secondary" mb={3}>
                첫 번째 Streamlit 앱을 만들어보세요!
              </Typography>
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={() => navigate('/apps/new')}
              >
                첫 번째 앱 만들기
              </Button>
            </Box>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {apps.map((app) => {
            const statusInfo = getActualStatusInfo(app);
            const realtimeInfo = realtimeStatus[app.id];
            
            return (
              <Grid item xs={12} sm={6} md={4} key={app.id}>
                <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                      <Typography variant="h6" component="h3">
                        {app.name}
                      </Typography>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Badge
                          badgeContent={statusInfo.isRealtime ? '실시간' : ''}
                          color="primary"
                          variant="dot"
                          invisible={!statusInfo.isRealtime}
                        >
                          <Chip
                            label={statusInfo.text}
                            color={statusInfo.color}
                            size="small"
                          />
                        </Badge>
                        {renderStatusIcon(app)}
                      </Stack>
                    </Box>
                    
                    <Typography variant="body2" color="text.secondary" mb={2}>
                      {app.description}
                    </Typography>
                    
                    {/* 실시간 상태 정보 */}
                    {realtimeInfo && (
                      <Box mb={2}>
                        <Stack direction="row" spacing={1} mb={1}>
                          <Chip
                            label={realtimeInfo.container_running ? '컨테이너 실행중' : '컨테이너 중지됨'}
                            color={realtimeInfo.container_running ? 'success' : 'default'}
                            size="small"
                            variant="outlined"
                          />
                          <Chip
                            label={realtimeInfo.nginx_config_valid ? 'Nginx 정상' : 'Nginx 오류'}
                            color={realtimeInfo.nginx_config_valid ? 'success' : 'error'}
                            size="small"
                            variant="outlined"
                          />
                        </Stack>
                      </Box>
                    )}
                    
                    <Box>
                      <Typography variant="caption" display="block">
                        브랜치: {app.branch}
                      </Typography>
                      <Typography variant="caption" display="block">
                        메인 파일: {app.main_file}
                      </Typography>
                      <Typography variant="caption" display="block">
                        생성일: {new Date(app.created_at).toLocaleDateString('ko-KR')}
                      </Typography>
                    </Box>
                  </CardContent>
                  <CardActions>
                    <Button
                      size="small"
                      startIcon={<Visibility />}
                      onClick={() => navigate(`/apps/${app.id}`)}
                    >
                      상세보기
                    </Button>
                    {(statusInfo.text === '실행중' || realtimeInfo?.container_running) && (
                      <Button
                        size="small"
                        startIcon={<OpenInNew />}
                        onClick={() => window.open(getAppUrl(app.subdomain), '_blank')}
                        color="primary"
                      >
                        열기
                      </Button>
                    )}
                    {statusInfo.text === '중지됨' && (
                      <Button
                        size="small"
                        startIcon={<PlayArrow />}
                        onClick={() => handleDeploy(app.id)}
                        disabled={deployMutation.isPending}
                      >
                        배포
                      </Button>
                    )}
                    {(statusInfo.text === '실행중' || realtimeInfo?.container_running) && (
                      <Button
                        size="small"
                        startIcon={<Stop />}
                        onClick={() => handleStop(app.id)}
                        disabled={stopMutation.isPending}
                      >
                        중지
                      </Button>
                    )}
                    <Button
                      size="small"
                      startIcon={<Delete />}
                      onClick={() => handleDelete(app)}
                      disabled={deleteMutation.isPending}
                      color="error"
                    >
                      삭제
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}

      {/* 환경변수 설정 다이얼로그 */}
      <Dialog open={envDialog.open} onClose={() => setEnvDialog({ open: false, appId: null, envVars: {} })} maxWidth="md" fullWidth>
        <DialogTitle>배포 설정</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            앱 배포 시 사용할 환경변수를 설정하세요.
          </Typography>
          
          <Box mt={2}>
            <Typography variant="subtitle2" gutterBottom>
              환경변수
            </Typography>
            {Object.entries(envDialog.envVars).map(([key, value]) => (
              <Box key={key} display="flex" alignItems="center" gap={1} mb={1}>
                <TextField
                  size="small"
                  label="키"
                  value={key}
                  disabled
                  sx={{ flex: 1 }}
                />
                <TextField
                  size="small"
                  label="값"
                  value={value}
                  onChange={(e) => setEnvDialog(prev => ({
                    ...prev,
                    envVars: { ...prev.envVars, [key]: e.target.value }
                  }))}
                  sx={{ flex: 2 }}
                />
                <Button
                  size="small"
                  color="error"
                  onClick={() => removeEnvVar(key)}
                >
                  삭제
                </Button>
              </Box>
            ))}
            <Button
              size="small"
              onClick={addEnvVar}
              sx={{ mt: 1 }}
            >
              환경변수 추가
            </Button>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEnvDialog({ open: false, appId: null, envVars: {} })}>
            취소
          </Button>
          <Button onClick={handleDeployConfirm} variant="contained">
            배포 시작
          </Button>
        </DialogActions>
      </Dialog>

      {/* 삭제 확인 다이얼로그 */}
      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, app: null })}>
        <DialogTitle>앱 삭제 확인</DialogTitle>
        <DialogContent>
          <Typography>
            정말로 "{deleteDialog.app?.name}" 앱을 삭제하시겠습니까?
          </Typography>
          <Typography variant="body2" color="error" sx={{ mt: 1 }}>
            이 작업은 되돌릴 수 없습니다.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, app: null })}>
            취소
          </Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            삭제
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Dashboard; 