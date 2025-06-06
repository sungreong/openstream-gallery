import React from 'react';
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
} from '@mui/material';
import { PlayArrow, Stop, Delete, Visibility, Edit, Settings, Add } from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import toast from 'react-hot-toast';

const Dashboard = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // 앱 목록 조회
  const { data: apps, isLoading, error } = useQuery({
    queryKey: ['apps'],
    queryFn: async () => {
      const response = await axios.get('/api/apps/');
      return response.data;
    }
  });

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

  const getStatusColor = (status) => {
    switch (status) {
      case 'running':
        return 'success';
      case 'building':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'running':
        return '실행 중';
      case 'building':
        return '빌드 중';
      case 'stopped':
        return '중지됨';
      case 'error':
        return '오류';
      default:
        return status;
    }
  };

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

  if (isLoading) {
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

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        대시보드
      </Typography>

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
                Nginx 설정 파일을 관리하고 사용하지 않는 설정을 정리하세요.
              </Typography>
            </CardContent>
            <CardActions>
              <Button
                variant="outlined"
                fullWidth
                onClick={() => navigate('/nginx-management')}
              >
                관리하기
              </Button>
            </CardActions>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent sx={{ flexGrow: 1 }}>
              <Box display="flex" alignItems="center" mb={2}>
                <Edit color="info" sx={{ mr: 1 }} />
                <Typography variant="h6">Git 인증</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Git 저장소 접근을 위한 인증 정보를 관리하세요.
              </Typography>
            </CardContent>
            <CardActions>
              <Button
                variant="outlined"
                fullWidth
                onClick={() => navigate('/git-credentials')}
              >
                설정하기
              </Button>
            </CardActions>
          </Card>
        </Grid>
      </Grid>

      <Typography variant="h5" gutterBottom>
        내 앱들 ({apps?.length || 0}개)
      </Typography>

      {apps?.length === 0 ? (
        <Box textAlign="center" mt={4}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            아직 생성된 앱이 없습니다.
          </Typography>
          <Button
            variant="contained"
            onClick={() => navigate('/apps/new')}
            sx={{ mt: 2 }}
          >
            첫 번째 앱 만들기
          </Button>
        </Box>
      ) : (
        <Grid container spacing={3}>
          {apps?.map((app) => (
            <Grid item xs={12} sm={6} md={4} key={app.id}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    {app.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {app.description || '설명 없음'}
                  </Typography>
                  <Box mt={2} mb={1}>
                    <Chip
                      label={getStatusText(app.status)}
                      color={getStatusColor(app.status)}
                      size="small"
                    />
                  </Box>
                  {app.status === 'running' && (
                    <Typography variant="body2" color="primary">
                      <a 
                        href={`/${app.subdomain}/`} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        style={{ textDecoration: 'none', color: 'inherit' }}
                      >
                        URL: /{app.subdomain}/
                      </a>
                    </Typography>
                  )}
                </CardContent>
                <CardActions>
                  <Button
                    size="small"
                    startIcon={<Visibility />}
                    onClick={() => navigate(`/apps/${app.id}`)}
                  >
                    상세
                  </Button>
                  {app.status === 'running' ? (
                    <Button
                      size="small"
                      startIcon={<Stop />}
                      onClick={() => handleStop(app.id)}
                      disabled={stopMutation.isLoading}
                    >
                      중지
                    </Button>
                  ) : (
                    <Button
                      size="small"
                      startIcon={<PlayArrow />}
                      onClick={() => handleDeploy(app.id)}
                      disabled={deployMutation.isLoading || app.status === 'building'}
                    >
                      배포
                    </Button>
                  )}
                  <Button
                    size="small"
                    startIcon={<Delete />}
                    color="error"
                    onClick={() => handleDelete(app.id)}
                    disabled={deleteMutation.isLoading}
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