import React, { useState, useEffect } from 'react';
import {
  Typography,
  Grid,
  Card,
  CardContent,
  Box,
  CircularProgress,
  Alert,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  ExpandMore,
  Refresh,
  Cancel,
  CheckCircle,
  Error,
  Schedule,
  PlayArrow,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import toast from 'react-hot-toast';

const CeleryMonitor = () => {
  const queryClient = useQueryClient();
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Celery 워커 상태 조회
  const { data: workers, isLoading: workersLoading } = useQuery({
    queryKey: ['celery-workers'],
    queryFn: async () => {
      const response = await axios.get('/api/celery/workers');
      return response.data;
    },
    refetchInterval: autoRefresh ? 5000 : false,
  });

  // Celery 큐 상태 조회
  const { data: queues, isLoading: queuesLoading } = useQuery({
    queryKey: ['celery-queues'],
    queryFn: async () => {
      const response = await axios.get('/api/celery/queues');
      return response.data;
    },
    refetchInterval: autoRefresh ? 5000 : false,
  });

  // 활성 태스크 조회
  const { data: activeTasks, isLoading: tasksLoading } = useQuery({
    queryKey: ['celery-active-tasks'],
    queryFn: async () => {
      const response = await axios.get('/api/celery/tasks/active');
      return response.data;
    },
    refetchInterval: autoRefresh ? 3000 : false,
  });

  // 태스크 취소 뮤테이션
  const cancelTaskMutation = useMutation({
    mutationFn: async (taskId) => {
      const response = await axios.post(`/api/celery/tasks/${taskId}/revoke`);
      return response.data;
    },
    onSuccess: () => {
      toast.success('태스크가 취소되었습니다.');
      queryClient.invalidateQueries({ queryKey: ['celery-active-tasks'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || '태스크 취소에 실패했습니다.');
    },
  });

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['celery-workers'] });
    queryClient.invalidateQueries({ queryKey: ['celery-queues'] });
    queryClient.invalidateQueries({ queryKey: ['celery-active-tasks'] });
  };

  const handleCancelTask = (taskId) => {
    if (window.confirm('정말로 이 태스크를 취소하시겠습니까?')) {
      cancelTaskMutation.mutate(taskId);
    }
  };

  const getTaskStatusIcon = (status) => {
    switch (status) {
      case 'SUCCESS':
        return <CheckCircle color="success" />;
      case 'FAILURE':
        return <Error color="error" />;
      case 'PENDING':
        return <Schedule color="warning" />;
      case 'PROGRESS':
        return <PlayArrow color="info" />;
      default:
        return <Schedule color="default" />;
    }
  };

  const getTaskStatusColor = (status) => {
    switch (status) {
      case 'SUCCESS':
        return 'success';
      case 'FAILURE':
        return 'error';
      case 'PENDING':
        return 'warning';
      case 'PROGRESS':
        return 'info';
      default:
        return 'default';
    }
  };

  const formatTaskName = (taskName) => {
    if (!taskName) return 'Unknown Task';
    const parts = taskName.split('.');
    return parts[parts.length - 1] || taskName;
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0초';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}시간 ${minutes}분 ${secs}초`;
    } else if (minutes > 0) {
      return `${minutes}분 ${secs}초`;
    } else {
      return `${secs}초`;
    }
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" gutterBottom>
          Celery 모니터링
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleRefresh}
            sx={{ mr: 2 }}
          >
            새로고침
          </Button>
          <Button
            variant={autoRefresh ? 'contained' : 'outlined'}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            자동 새로고침 {autoRefresh ? 'ON' : 'OFF'}
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* 워커 상태 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Celery 워커 상태
              </Typography>
              {workersLoading ? (
                <CircularProgress size={24} />
              ) : workers && workers.workers && workers.workers.length > 0 ? (
                <Box>
                  {workers.workers.map((worker, index) => (
                    <Box key={index} mb={2}>
                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography variant="subtitle2">{worker.name}</Typography>
                        <Chip
                          label={worker.status}
                          color={worker.status === 'online' ? 'success' : 'error'}
                          size="small"
                        />
                      </Box>
                                              <Typography variant="body2" color="text.secondary">
                          활성 태스크: {worker.active_tasks || 0}개
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          예약된 태스크: {worker.scheduled_tasks || 0}개
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          대기 태스크: {worker.reserved_tasks || 0}개
                        </Typography>
                    </Box>
                  ))}
                </Box>
              ) : (
                <Alert severity="warning">활성 워커가 없습니다.</Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 큐 상태 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                큐 상태
              </Typography>
              {queuesLoading ? (
                <CircularProgress size={24} />
              ) : queues && queues.queues && queues.queues.length > 0 ? (
                <Box>
                  {queues.queues.map((queue, index) => (
                    <Box key={index} mb={2}>
                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography variant="subtitle2">{queue.name}</Typography>
                        <Chip
                          label={`${queue.total_tasks || 0}개 대기`}
                          color={queue.total_tasks > 0 ? 'warning' : 'success'}
                          size="small"
                        />
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        워커: {queue.workers ? queue.workers.length : 0}개
                      </Typography>
                    </Box>
                  ))}
                </Box>
              ) : (
                <Alert severity="info">큐 정보를 불러올 수 없습니다.</Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 활성 태스크 */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                활성 태스크
              </Typography>
              {tasksLoading ? (
                <CircularProgress size={24} />
              ) : activeTasks && activeTasks.active_tasks && activeTasks.active_tasks.length > 0 ? (
                <TableContainer component={Paper} variant="outlined">
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>태스크 ID</TableCell>
                        <TableCell>태스크 이름</TableCell>
                        <TableCell>상태</TableCell>
                        <TableCell>진행률</TableCell>
                        <TableCell>실행 시간</TableCell>
                        <TableCell>워커</TableCell>
                        <TableCell>작업</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {activeTasks.active_tasks.map((task) => (
                        <TableRow key={task.id}>
                          <TableCell>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                              {task.id.substring(0, 8)}...
                            </Typography>
                          </TableCell>
                          <TableCell>{formatTaskName(task.name)}</TableCell>
                          <TableCell>
                            <Box display="flex" alignItems="center">
                              {getTaskStatusIcon(task.state)}
                              <Chip
                                label={task.state}
                                color={getTaskStatusColor(task.state)}
                                size="small"
                                sx={{ ml: 1 }}
                              />
                            </Box>
                          </TableCell>
                          <TableCell>
                            {task.result && task.result.current !== undefined ? (
                              <Box>
                                <LinearProgress
                                  variant="determinate"
                                  value={(task.result.current / task.result.total) * 100}
                                  sx={{ mb: 1 }}
                                />
                                <Typography variant="body2">
                                  {task.result.current}/{task.result.total} ({Math.round((task.result.current / task.result.total) * 100)}%)
                                </Typography>
                                {task.result.status && (
                                  <Typography variant="caption" color="text.secondary">
                                    {task.result.status}
                                  </Typography>
                                )}
                              </Box>
                            ) : (
                              <Typography variant="body2" color="text.secondary">
                                -
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell>
                            {task.runtime ? formatDuration(task.runtime) : '-'}
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                              {task.worker || '-'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Button
                              size="small"
                              variant="outlined"
                              color="error"
                              startIcon={<Cancel />}
                              onClick={() => handleCancelTask(task.id)}
                              disabled={cancelTaskMutation.isLoading}
                            >
                              취소
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Alert severity="info">현재 실행 중인 태스크가 없습니다.</Alert>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default CeleryMonitor; 