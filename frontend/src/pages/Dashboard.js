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
    deployMutation.mutate(appId);
  };

  const handleStop = (appId) => {
    stopMutation.mutate(appId);
  };

  const handleDelete = (appId) => {
    if (window.confirm('정말로 이 앱을 삭제하시겠습니까?')) {
      deleteMutation.mutate(appId);
    }
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
      <Typography variant="h4" gutterBottom>
        대시보드
      </Typography>

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
          {apps.map((app) => (
            <Grid item xs={12} sm={6} md={4} key={app.id}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                    <Typography variant="h6" component="h3">
                      {app.name}
                    </Typography>
                    <Chip
                      label={getStatusText(app.status)}
                      color={getStatusColor(app.status)}
                      size="small"
                    />
                  </Box>
                  <Typography variant="body2" color="text.secondary" mb={2}>
                    {app.description}
                  </Typography>
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
                  {app.status === 'running' && (
                    <Button
                      size="small"
                      startIcon={<OpenInNew />}
                      onClick={() => window.open(getAppUrl(app.subdomain), '_blank')}
                      color="primary"
                    >
                      열기
                    </Button>
                  )}
                  {app.status === 'stopped' && (
                    <Button
                      size="small"
                      startIcon={<PlayArrow />}
                      onClick={() => handleDeploy(app.id)}
                      disabled={deployMutation.isPending}
                    >
                      배포
                    </Button>
                  )}
                  {app.status === 'running' && (
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
                    onClick={() => handleDelete(app.id)}
                    disabled={deleteMutation.isPending}
                    color="error"
                  >
                    삭제
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
};

export default Dashboard; 