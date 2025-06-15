import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  Chip,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Switch,
  FormControlLabel,
  LinearProgress,
  Stepper,
  Step,
  StepLabel,
  StepContent,
} from '@mui/material';
import { PlayArrow, Stop, Delete, Refresh, Settings, OpenInNew, Edit, Save, Cancel } from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import toast from 'react-hot-toast';

// 앱 URL 생성 함수
const getAppUrl = (subdomain) => {
  const baseUrl = process.env.REACT_APP_BASE_URL || 'http://localhost:1234';
  return `${baseUrl}/${subdomain}/`;
};

const AppDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  // 편집 모드 상태
  const [isEditing, setIsEditing] = useState(false);
  const [editFormData, setEditFormData] = useState({
    name: '',
    description: '',
    git_url: '',
    branch: '',
    main_file: '',
    base_dockerfile_type: '',
    custom_base_image: '',
    custom_dockerfile_commands: '',
    git_credential_id: '',
    is_public: false,
  });

  // 자동 새로고침 상태
  const [lastTaskState, setLastTaskState] = useState(null);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);

  // 앱 정보 조회
  const { data: app, isLoading, error } = useQuery({
    queryKey: ['app', id],
    queryFn: async () => {
      const response = await axios.get(`/api/apps/${id}`);
      return response.data;
    }
  });

  // 앱 로그 조회
  const { data: logs, isLoading: logsLoading } = useQuery({
    queryKey: ['app-logs', id],
    queryFn: async () => {
      const response = await axios.get(`/api/apps/${id}/logs`);
      return response.data;
    },
    enabled: !!app,
    refetchInterval: app?.status === 'running' ? 10000 : false, // 실행 중일 때만 10초마다
  });

  // 컨테이너 상태 조회
  const { data: containerStatus, isLoading: containerLoading } = useQuery({
    queryKey: ['container-status', id],
    queryFn: async () => {
      const response = await axios.get(`/api/apps/${id}/container-status`);
      return response.data;
    },
    enabled: !!app,
    refetchInterval: 15000, // 15초마다 갱신
  });

  // Celery 태스크 상태 조회
  const { data: celeryStatus, isLoading: celeryLoading } = useQuery({
    queryKey: ['celery-status', id],
    queryFn: async () => {
      const response = await axios.get(`/api/apps/${id}/celery-status`);
      return response.data;
    },
    enabled: !!app && autoRefreshEnabled,
    refetchInterval: (data) => {
      // 활성 태스크가 있을 때만 자주 갱신
      const hasActiveTasks = data?.tasks && Object.values(data.tasks).some(
        task => task.state === 'PROGRESS' || task.state === 'PENDING'
      );
      return hasActiveTasks ? 3000 : 10000; // 활성 태스크 있으면 3초, 없으면 10초
    },
  });

  // 태스크 상태 변화 감지 및 자동 갱신
  useEffect(() => {
    if (celeryStatus?.tasks) {
      const currentTaskState = JSON.stringify(celeryStatus.tasks);
      if (lastTaskState && lastTaskState !== currentTaskState) {
        // 태스크 상태가 변경되면 앱 정보와 컨테이너 정보도 갱신
        queryClient.invalidateQueries({ queryKey: ['app', id] });
        queryClient.invalidateQueries({ queryKey: ['container-status', id] });
      }
      setLastTaskState(currentTaskState);
    }
  }, [celeryStatus, lastTaskState, queryClient, id]);

  // Git 인증 정보 목록 조회 (편집 시 사용)
  const { data: gitCredentials = [] } = useQuery({
    queryKey: ['git-credentials'],
    queryFn: async () => {
      const response = await axios.get('/api/git-credentials/');
      return response.data;
    },
    enabled: isEditing,
  });

  // 베이스 Dockerfile 목록 조회 (편집 시 사용)
  const { data: baseDockerfiles = [] } = useQuery({
    queryKey: ['base-dockerfiles'],
    queryFn: async () => {
      const response = await axios.get('/api/dockerfiles/base-types');
      return response.data.base_dockerfiles;
    },
    enabled: isEditing,
  });

  // 앱 배포 뮤테이션
  const deployMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.post(`/api/apps/${id}/deploy`, {});
      return response.data;
    },
    onSuccess: () => {
      toast.success('배포가 시작되었습니다.');
      queryClient.invalidateQueries({ queryKey: ['app', id] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || '배포에 실패했습니다.');
    },
  });

  // 앱 중지 뮤테이션
  const stopMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.post(`/api/apps/${id}/stop`);
      return response.data;
    },
    onSuccess: () => {
      toast.success('앱이 중지되었습니다.');
      queryClient.invalidateQueries({ queryKey: ['app', id] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || '앱 중지에 실패했습니다.');
    },
  });

  // 앱 삭제 뮤테이션
  const deleteMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.delete(`/api/apps/${id}`);
      return response.data;
    },
    onSuccess: () => {
      toast.success('앱이 삭제되었습니다.');
      navigate('/dashboard');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || '앱 삭제에 실패했습니다.');
    },
  });

  // 앱 업데이트 뮤테이션
  const updateMutation = useMutation({
    mutationFn: async (updateData) => {
      const response = await axios.put(`/api/apps/${id}`, updateData);
      return response.data;
    },
    onSuccess: () => {
      toast.success('앱 정보가 업데이트되었습니다.');
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ['app', id] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || '앱 업데이트에 실패했습니다.');
    },
  });

  // 공개 설정 토글 뮤테이션
  const togglePublicMutation = useMutation({
    mutationFn: async (isPublic) => {
      const response = await axios.put(`/api/apps/${id}`, { is_public: isPublic });
      return response.data;
    },
    onSuccess: (data) => {
      toast.success(data.is_public ? '앱이 공개되었습니다.' : '앱이 비공개로 설정되었습니다.');
      queryClient.invalidateQueries({ queryKey: ['app', id] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || '공개 설정 변경에 실패했습니다.');
    },
  });

  // 태스크 취소 뮤테이션
  const cancelTaskMutation = useMutation({
    mutationFn: async (taskType) => {
      const response = await axios.post(`/api/apps/${id}/cancel-task/${taskType}`);
      return response.data;
    },
    onSuccess: (data) => {
      toast.success(data.message);
      queryClient.invalidateQueries({ queryKey: ['app', id] });
      queryClient.invalidateQueries({ queryKey: ['celery-status', id] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || '태스크 취소에 실패했습니다.');
    },
  });

  // Nginx 리로드 뮤테이션
  const nginxReloadMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.post('/api/nginx/reload');
      return response.data;
    },
    onSuccess: () => {
      toast.success('Nginx가 성공적으로 리로드되었습니다.');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Nginx 리로드에 실패했습니다.');
    },
  });

  const getStatusColor = (status) => {
    switch (status) {
      case 'running':
        return 'success';
      case 'building':
      case 'deploying':
        return 'warning';
      case 'stopping':
        return 'info';
      case 'error':
      case 'failed':
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
      case 'deploying':
        return '배포 중';
      case 'stopping':
        return '중지 중';
      case 'stopped':
        return '중지됨';
      case 'error':
      case 'failed':
        return '오류';
      default:
        return status;
    }
  };

  const getTaskStatusColor = (state) => {
    switch (state) {
      case 'SUCCESS':
        return 'success';
      case 'PROGRESS':
        return 'warning';
      case 'FAILURE':
        return 'error';
      case 'PENDING':
        return 'info';
      default:
        return 'default';
    }
  };

  const getTaskStatusText = (state) => {
    switch (state) {
      case 'SUCCESS':
        return '완료';
      case 'PROGRESS':
        return '진행 중';
      case 'FAILURE':
        return '실패';
      case 'PENDING':
        return '대기 중';
      case 'RETRY':
        return '재시도';
      case 'REVOKED':
        return '취소됨';
      default:
        return state || '알 수 없음';
    }
  };

  const handleDeploy = () => {
    deployMutation.mutate();
  };

  const handleStop = () => {
    stopMutation.mutate();
  };

  const handleDelete = () => {
    if (window.confirm('정말로 이 앱을 삭제하시겠습니까?')) {
      deleteMutation.mutate();
    }
  };

  const handleEdit = () => {
    setEditFormData({
      name: app.name,
      description: app.description || '',
      git_url: app.git_url,
      branch: app.branch,
      main_file: app.main_file,
      base_dockerfile_type: app.base_dockerfile_type,
      custom_base_image: app.custom_base_image || '',
      custom_dockerfile_commands: app.custom_dockerfile_commands || '',
      git_credential_id: app.git_credential_id || '',
      is_public: app.is_public || false,
    });
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditFormData({
      name: '',
      description: '',
      git_url: '',
      branch: '',
      main_file: '',
      base_dockerfile_type: '',
      custom_base_image: '',
      custom_dockerfile_commands: '',
      git_credential_id: '',
      is_public: false,
    });
  };

  const handleSaveEdit = () => {
    // 빈 값 제거 및 변경된 값만 전송
    const updateData = {};
    Object.keys(editFormData).forEach(key => {
      if (editFormData[key] !== app[key]) {
        updateData[key] = editFormData[key] === '' ? null : editFormData[key];
      }
    });

    if (Object.keys(updateData).length === 0) {
      toast.info('변경된 내용이 없습니다.');
      setIsEditing(false);
      return;
    }

    updateMutation.mutate(updateData);
  };

  const handleEditFormChange = (field, value) => {
    setEditFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleCancelTask = (taskType) => {
    if (window.confirm(`정말로 ${taskType} 태스크를 취소하시겠습니까?`)) {
      cancelTaskMutation.mutate(taskType);
    }
  };

  const handleTogglePublic = () => {
    const newPublicState = !app.is_public;
    const message = newPublicState 
      ? '이 앱을 공개하시겠습니까? 다른 사용자들이 이 앱을 볼 수 있게 됩니다.'
      : '이 앱을 비공개로 설정하시겠습니까?';
    
    if (window.confirm(message)) {
      togglePublicMutation.mutate(newPublicState);
    }
  };

  // 태스크 진행 단계 정보
  const getTaskSteps = () => {
    if (!celeryStatus?.tasks) return [];
    
    const tasks = Object.values(celeryStatus.tasks);
    const buildTask = tasks.find(task => task.task_type === 'build');
    const deployTask = tasks.find(task => task.task_type === 'deploy');
    
    return [
      {
        label: '빌드',
        task: buildTask,
        completed: buildTask?.state === 'SUCCESS',
        active: buildTask?.state === 'PROGRESS' || buildTask?.state === 'PENDING',
        error: buildTask?.state === 'FAILURE',
      },
      {
        label: '배포',
        task: deployTask,
        completed: deployTask?.state === 'SUCCESS',
        active: deployTask?.state === 'PROGRESS' || deployTask?.state === 'PENDING',
        error: deployTask?.state === 'FAILURE',
      },
    ];
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
        앱 정보를 불러오는데 실패했습니다.
      </Alert>
    );
  }

  const taskSteps = getTaskSteps();
  const hasActiveTasks = taskSteps.some(step => step.active);

  return (
    <Container maxWidth="xl">
      <Box sx={{ mt: 2, mb: 4 }}>
        <Button onClick={() => navigate('/dashboard')}>
          ← 대시보드로 돌아가기
        </Button>
      </Box>

      <Grid container spacing={3}>
        {/* 앱 정보 */}
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="start" mb={2}>
              <Box>
                <Typography variant="h4" gutterBottom>
                  {app.name}
                </Typography>
                <Box display="flex" gap={1} mb={2}>
                  <Chip
                    label={getStatusText(app.status)}
                    color={getStatusColor(app.status)}
                  />
                  <Chip
                    label={app.is_public ? '공개 앱' : '비공개 앱'}
                    color={app.is_public ? 'success' : 'default'}
                    variant={app.is_public ? 'filled' : 'outlined'}
                    onClick={handleTogglePublic}
                    disabled={togglePublicMutation.isLoading}
                    sx={{ 
                      cursor: 'pointer',
                      '&:hover': {
                        backgroundColor: app.is_public ? 'success.dark' : 'action.hover'
                      }
                    }}
                  />
                </Box>
              </Box>
              <Box display="flex" gap={1}>
                {app.status === 'running' ? (
                  <Button
                    variant="outlined"
                    startIcon={<Stop />}
                    onClick={handleStop}
                    disabled={stopMutation.isLoading}
                  >
                    중지
                  </Button>
                ) : (
                  <Button
                    variant="contained"
                    startIcon={<PlayArrow />}
                    onClick={handleDeploy}
                    disabled={deployMutation.isLoading || app.status === 'building'}
                  >
                    배포
                  </Button>
                )}
                {(app.status === 'stopped' || app.status === 'error') && (
                  <Button
                    variant="outlined"
                    startIcon={<Edit />}
                    onClick={handleEdit}
                    disabled={isEditing}
                  >
                    편집
                  </Button>
                )}
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<Delete />}
                  onClick={handleDelete}
                  disabled={deleteMutation.isLoading}
                >
                  삭제
                </Button>
              </Box>
            </Box>

            <Typography variant="body1" paragraph>
              {app.description || '설명이 없습니다.'}
            </Typography>

            {app.is_public && (
              <Alert severity="info" sx={{ mb: 2 }}>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography variant="body2" fontWeight="bold">
                      🌍 이 앱은 공개 앱입니다
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      다른 사용자들도 대시보드에서 이 앱을 볼 수 있습니다.
                    </Typography>
                  </Box>
                  <Button
                    size="small"
                    onClick={handleTogglePublic}
                    disabled={togglePublicMutation.isLoading}
                    color="warning"
                    variant="outlined"
                  >
                    비공개로 설정
                  </Button>
                </Box>
              </Alert>
            )}

            {app.status === 'running' && (
              <Alert severity="success" sx={{ mb: 2 }}>
                앱이 실행 중입니다: 
                <a 
                  href={getAppUrl(app.subdomain)} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  style={{ marginLeft: 8 }}
                >
                  {getAppUrl(app.subdomain)}
                </a>
              </Alert>
            )}

            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Git 저장소"
                  value={app.git_url}
                  fullWidth
                  InputProps={{ readOnly: true }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="브랜치"
                  value={app.branch}
                  fullWidth
                  InputProps={{ readOnly: true }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="메인 파일"
                  value={app.main_file}
                  fullWidth
                  InputProps={{ readOnly: true }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="서브도메인"
                  value={app.subdomain}
                  fullWidth
                  InputProps={{ readOnly: true }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    공개 설정
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Switch
                      checked={app.is_public || false}
                      onChange={handleTogglePublic}
                      disabled={togglePublicMutation.isLoading}
                      color="success"
                    />
                    <Typography variant="body2" color="text.secondary">
                      {app.is_public ? '공개됨' : '비공개'}
                    </Typography>
                    {togglePublicMutation.isLoading && (
                      <CircularProgress size={16} />
                    )}
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    공개 앱은 다른 사용자들도 볼 수 있습니다
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </Paper>

          {/* 배포 프로세스 상태 - 가로 배치 */}
          {(hasActiveTasks || app.status === 'building' || app.status === 'deploying') && (
            <Paper sx={{ p: 3, mt: 3 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h6">
                  배포 프로세스
                </Typography>
                <FormControlLabel
                  control={
                    <Switch
                      checked={autoRefreshEnabled}
                      onChange={(e) => setAutoRefreshEnabled(e.target.checked)}
                      size="small"
                    />
                  }
                  label="자동 새로고침"
                />
              </Box>

              <Grid container spacing={3}>
                {taskSteps.map((step, index) => (
                  <Grid item xs={12} md={6} key={step.label}>
                    <Card sx={{ 
                      height: '100%',
                      backgroundColor: step.active ? '#fff3e0' : step.completed ? '#e8f5e8' : step.error ? '#ffebee' : '#fafafa',
                      border: step.active ? '2px solid #ff9800' : 'none'
                    }}>
                      <CardContent>
                        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                          <Typography variant="h6" fontWeight="bold">
                            {step.label}
                          </Typography>
                          <Chip
                            label={
                              step.completed ? '완료' :
                              step.active ? '진행 중' :
                              step.error ? '실패' : '대기'
                            }
                            color={
                              step.completed ? 'success' :
                              step.active ? 'warning' :
                              step.error ? 'error' : 'default'
                            }
                            size="small"
                          />
                        </Box>

                        {step.task && (
                          <>
                            <Typography variant="body2" color="text.secondary" gutterBottom>
                              태스크 ID: {step.task.task_id}
                            </Typography>

                            {step.task.state === 'PROGRESS' && step.task.meta && (
                              <Box>
                                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                                  <Typography variant="body2" color="text.secondary">
                                    진행률: {step.task.meta.current}/{step.task.meta.total}
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    {Math.round((step.task.meta.current / step.task.meta.total) * 100)}%
                                  </Typography>
                                </Box>
                                <LinearProgress 
                                  variant="determinate" 
                                  value={(step.task.meta.current / step.task.meta.total) * 100}
                                  sx={{ mb: 1 }}
                                />
                                <Typography variant="body2" color="text.secondary">
                                  상태: {step.task.meta.status}
                                </Typography>
                              </Box>
                            )}

                            {step.task.state === 'FAILURE' && step.task.error && (
                              <Typography variant="body2" color="error">
                                오류: {step.task.error}
                              </Typography>
                            )}

                            {(step.task.state === 'PROGRESS' || step.task.state === 'PENDING') && (
                              <Button
                                size="small"
                                color="error"
                                onClick={() => handleCancelTask(step.task.task_type)}
                                disabled={cancelTaskMutation.isLoading}
                                sx={{ mt: 2 }}
                                fullWidth
                              >
                                취소
                              </Button>
                            )}
                          </>
                        )}
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Paper>
          )}

          {/* 로그 - 가로 화면에서 더 넓게 표시 */}
          <Paper sx={{ p: 3, mt: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">
                로그
              </Typography>
              <Button
                size="small"
                startIcon={<Refresh />}
                onClick={() => queryClient.invalidateQueries({ queryKey: ['app-logs', id] })}
                disabled={logsLoading}
              >
                새로고침
              </Button>
            </Box>
            
            <Box
              sx={{
                height: 500,
                overflow: 'auto',
                backgroundColor: '#f5f5f5',
                p: 2,
                borderRadius: 1,
                fontFamily: 'monospace',
                fontSize: '0.875rem',
              }}
            >
              {logsLoading ? (
                <CircularProgress size={20} />
              ) : (
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                  {logs?.logs || '로그가 없습니다.'}
                </pre>
              )}
            </Box>
          </Paper>
        </Grid>

        {/* 사이드바 */}
        <Grid item xs={12} lg={4}>
          {/* 컨테이너 상태 */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">
                컨테이너 상태
              </Typography>
              <Button
                size="small"
                startIcon={<Refresh />}
                onClick={() => queryClient.invalidateQueries({ queryKey: ['container-status', id] })}
                disabled={containerLoading}
              >
                새로고침
              </Button>
            </Box>
            
            {containerLoading ? (
              <CircularProgress size={20} />
            ) : containerStatus ? (
              <Box>
                <Box display="flex" alignItems="center" gap={1} mb={1}>
                  <Typography variant="body2" color="text.secondary">
                    상태:
                  </Typography>
                  <Chip
                    label={containerStatus.container_status}
                    color={containerStatus.container_info?.running ? 'success' : 'default'}
                    size="small"
                  />
                </Box>
                
                {containerStatus.container_id && (
                  <Box mb={1}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      컨테이너 ID:
                    </Typography>
                    <Typography 
                      variant="body2" 
                      sx={{ 
                        fontFamily: 'monospace', 
                        fontSize: '0.75rem',
                        wordBreak: 'break-all',
                        backgroundColor: 'grey.100',
                        padding: '2px 4px',
                        borderRadius: '4px'
                      }}
                    >
                      {containerStatus.container_id}
                    </Typography>
                  </Box>
                )}
                
                {containerStatus.image_name && (
                  <Box mb={1}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      이미지:
                    </Typography>
                    <Typography 
                      variant="body2" 
                      sx={{ 
                        fontFamily: 'monospace', 
                        fontSize: '0.8rem',
                        wordBreak: 'break-all'
                      }}
                    >
                      {containerStatus.image_name}
                    </Typography>
                  </Box>
                )}
                
                {containerStatus.container_info?.networks && (
                  <Box mb={1}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      네트워크:
                    </Typography>
                    <Typography 
                      variant="body2" 
                      sx={{ 
                        fontFamily: 'monospace', 
                        fontSize: '0.8rem',
                        wordBreak: 'break-all'
                      }}
                    >
                      {containerStatus.container_info.networks.join(', ')}
                    </Typography>
                  </Box>
                )}
                
                {containerStatus.container_info?.started_at && (
                  <Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      시작 시간:
                    </Typography>
                    <Typography variant="body2">
                      {new Date(containerStatus.container_info.started_at).toLocaleString()}
                    </Typography>
                  </Box>
                )}
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                컨테이너 정보를 불러올 수 없습니다.
              </Typography>
            )}
          </Paper>

          {/* Nginx 설정 정보 */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">
                Nginx 설정
              </Typography>
              <Box display="flex" gap={1}>
                <Button
                  size="small"
                  startIcon={<Refresh />}
                  onClick={() => nginxReloadMutation.mutate()}
                  disabled={nginxReloadMutation.isLoading}
                  color="primary"
                  variant="outlined"
                >
                  {nginxReloadMutation.isLoading ? '리로드 중...' : '리로드'}
                </Button>
                <Button
                  size="small"
                  startIcon={<Settings />}
                  onClick={() => navigate('/nginx-management')}
                  variant="outlined"
                >
                  관리
                </Button>
              </Box>
            </Box>
            
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                설정 파일: <strong>{app.subdomain}.conf</strong>
              </Typography>
              
              {app.status === 'running' && (
                <Box mt={2}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    접근 URL:
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {getAppUrl(app.subdomain)}
                    </Typography>
                    <Button
                      size="small"
                      startIcon={<OpenInNew />}
                      onClick={() => window.open(getAppUrl(app.subdomain), '_blank')}
                    >
                      열기
                    </Button>
                  </Box>
                </Box>
              )}
              
              <Box mt={2}>
                <Typography variant="body2" color="text.secondary">
                  프록시 대상: <strong>{app.subdomain}:8501</strong>
                </Typography>
              </Box>
            </Box>
          </Paper>

          {/* 기타 태스크 상태 */}
          {celeryStatus?.tasks && Object.values(celeryStatus.tasks).some(task => task.task_type !== 'build' && task.task_type !== 'deploy') && (
            <Paper sx={{ p: 3, mb: 3 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">
                  기타 태스크
                </Typography>
                <Button
                  size="small"
                  startIcon={<Refresh />}
                  onClick={() => queryClient.invalidateQueries({ queryKey: ['celery-status', id] })}
                  disabled={celeryLoading}
                >
                  새로고침
                </Button>
              </Box>
              
              {celeryLoading ? (
                <CircularProgress size={20} />
              ) : (
                <Box>
                  {Object.entries(celeryStatus.tasks)
                    .filter(([_, taskData]) => taskData.task_type !== 'build' && taskData.task_type !== 'deploy')
                    .map(([taskKey, taskData]) => (
                    <Box key={taskKey} mb={2} p={2} sx={{ backgroundColor: '#f5f5f5', borderRadius: 1 }}>
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                        <Typography variant="body2" fontWeight="bold">
                          {taskData.task_type === 'stop' ? '중지' : taskData.task_type}
                        </Typography>
                        <Chip
                          label={getTaskStatusText(taskData.state)}
                          color={getTaskStatusColor(taskData.state)}
                          size="small"
                        />
                      </Box>
                      
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        ID: {taskData.task_id}
                      </Typography>
                      
                      {taskData.state === 'PROGRESS' && taskData.meta && (
                        <Box>
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            진행률: {taskData.meta.current}/{taskData.meta.total}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            상태: {taskData.meta.status}
                          </Typography>
                        </Box>
                      )}
                      
                      {taskData.state === 'FAILURE' && taskData.error && (
                        <Typography variant="body2" color="error" gutterBottom>
                          오류: {taskData.error}
                        </Typography>
                      )}
                      
                      {(taskData.state === 'PROGRESS' || taskData.state === 'PENDING') && (
                        <Button
                          size="small"
                          color="error"
                          onClick={() => handleCancelTask(taskData.task_type)}
                          disabled={cancelTaskMutation.isLoading}
                          sx={{ mt: 1 }}
                        >
                          취소
                        </Button>
                      )}
                    </Box>
                  ))}
                </Box>
              )}
            </Paper>
          )}
        </Grid>
      </Grid>

      {/* 편집 다이얼로그 */}
      <Dialog open={isEditing} onClose={handleCancelEdit} maxWidth="md" fullWidth>
        <DialogTitle>앱 정보 편집</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  label="앱 이름"
                  value={editFormData.name}
                  onChange={(e) => handleEditFormChange('name', e.target.value)}
                  fullWidth
                  required
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="설명"
                  value={editFormData.description}
                  onChange={(e) => handleEditFormChange('description', e.target.value)}
                  fullWidth
                  multiline
                  rows={3}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Git 저장소 URL"
                  value={editFormData.git_url}
                  onChange={(e) => handleEditFormChange('git_url', e.target.value)}
                  fullWidth
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="브랜치"
                  value={editFormData.branch}
                  onChange={(e) => handleEditFormChange('branch', e.target.value)}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="메인 파일"
                  value={editFormData.main_file}
                  onChange={(e) => handleEditFormChange('main_file', e.target.value)}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>베이스 이미지 타입</InputLabel>
                  <Select
                    value={editFormData.base_dockerfile_type}
                    label="베이스 이미지 타입"
                    onChange={(e) => handleEditFormChange('base_dockerfile_type', e.target.value)}
                  >
                    <MenuItem value="auto">자동 선택</MenuItem>
                    {baseDockerfiles.map((dockerfile) => (
                      <MenuItem key={dockerfile.type} value={dockerfile.type}>
                        {dockerfile.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="사용자 정의 베이스 이미지 (선택사항)"
                  value={editFormData.custom_base_image}
                  onChange={(e) => handleEditFormChange('custom_base_image', e.target.value)}
                  fullWidth
                  placeholder="예: python:3.11-slim, ubuntu:22.04"
                  helperText="Docker Hub의 이미지명:태그 형식"
                  sx={{
                    '& .MuiInputBase-input': {
                      fontFamily: 'monospace',
                      fontSize: '0.875rem',
                    },
                  }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Git 인증 정보</InputLabel>
                  <Select
                    value={editFormData.git_credential_id}
                    label="Git 인증 정보"
                    onChange={(e) => handleEditFormChange('git_credential_id', e.target.value)}
                  >
                    <MenuItem value="">없음 (공개 저장소)</MenuItem>
                    {gitCredentials.map((credential) => (
                      <MenuItem key={credential.id} value={credential.id}>
                        {credential.name} ({credential.git_provider})
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={editFormData.is_public || false}
                      onChange={(e) => handleEditFormChange('is_public', e.target.checked)}
                    />
                  }
                  label="공개 앱으로 설정"
                />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  공개 앱으로 설정하면 다른 사용자들도 이 앱을 볼 수 있습니다.
                </Typography>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="사용자 정의 Docker 명령어 (선택사항)"
                  value={editFormData.custom_dockerfile_commands}
                  onChange={(e) => handleEditFormChange('custom_dockerfile_commands', e.target.value)}
                  fullWidth
                  multiline
                  rows={6}
                  helperText="베이스 이미지에 추가로 실행할 Docker 명령어를 입력하세요."
                  placeholder={`# 예시:
RUN apt-get update && apt-get install -y curl
RUN pip install --no-cache-dir pandas numpy
ENV MY_CUSTOM_VAR=value`}
                  sx={{
                    '& .MuiInputBase-input': {
                      fontFamily: 'monospace',
                      fontSize: '0.875rem',
                    },
                  }}
                />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelEdit} startIcon={<Cancel />}>
            취소
          </Button>
          <Button 
            onClick={handleSaveEdit} 
            variant="contained" 
            startIcon={<Save />}
            disabled={updateMutation.isLoading}
          >
            {updateMutation.isLoading ? '저장 중...' : '저장'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default AppDetail; 