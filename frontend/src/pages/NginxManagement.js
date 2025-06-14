import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Divider,
  Paper,
  CircularProgress,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Stack
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  CleaningServices as CleanIcon,
  Settings as SettingsIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Warning as WarningIcon
} from '@mui/icons-material';
import { safeFetch, formatErrorMessage } from '../utils/errorHandler';
import { toast } from 'react-hot-toast';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

const NginxManagement = () => {
  const [dynamicConfigs, setDynamicConfigs] = useState(null);
  const [nginxStatus, setNginxStatus] = useState({ loading: false, valid: null });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [cleanupDialog, setCleanupDialog] = useState({ open: false, activeApps: '' });
  const [deleteDialog, setDeleteDialog] = useState({ open: false, subdomain: '' });
  const [appConfigsStatus, setAppConfigsStatus] = useState(null);

  // 데이터 로드
  const loadDynamicConfigs = async () => {
    setLoading(true);
    try {
      const data = await safeFetch(`${API_BASE_URL}/api/nginx/dynamic`);
      
      if (data.success) {
        setDynamicConfigs(data.data);
        setError('');
      } else {
        setError(data.message || '설정 파일 조회 실패');
      }
    } catch (err) {
      console.error('loadDynamicConfigs error:', err);
      setError(formatErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  // 앱 설정 상태 조회
  const loadAppConfigsStatus = async () => {
    try {
      const data = await safeFetch(`${API_BASE_URL}/api/nginx/configs/status`);
      if (data.success) {
        setAppConfigsStatus(data.data);
      }
    } catch (err) {
      console.error('loadAppConfigsStatus error:', err);
      setError(formatErrorMessage(err));
    }
  };

  // Nginx 설정 유효성 검사
  const testNginxConfig = async () => {
    setNginxStatus({ valid: null, loading: true });
    try {
      const data = await safeFetch(`${API_BASE_URL}/api/nginx/test`);
      
      setNginxStatus({ 
        valid: data.data?.is_valid || false, 
        loading: false 
      });
    } catch (err) {
      console.error('testNginxConfig error:', err);
      setNginxStatus({ valid: false, loading: false });
      setError(formatErrorMessage(err));
    }
  };

  // 자동 정리
  const handleAutoCleanup = async () => {
    try {
      setLoading(true);
      const data = await safeFetch(`${API_BASE_URL}/api/nginx/cleanup/auto`, {
        method: 'POST',
      });
      
      if (data.success) {
        toast.success(data.message);
        loadDynamicConfigs();
      } else {
        toast.error(data.message || '자동 정리에 실패했습니다.');
      }
    } catch (error) {
      console.error('자동 정리 실패:', error);
      toast.error('자동 정리에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleValidateAndCleanup = async () => {
    try {
      setLoading(true);
      const data = await safeFetch(`${API_BASE_URL}/api/nginx/cleanup/validate`, {
        method: 'POST',
      });
      
      if (data.success) {
        const result = data.data;
        const message = `검증 완료: ${result.total_checked}개 파일 검증, ${result.removed_files.length}개 문제 파일 삭제`;
        toast.success(message);
        
        // 상세 결과 로그
        if (result.removed_files.length > 0) {
          console.log('삭제된 파일들:', result.removed_files);
          console.log('검증 결과:', result.validation_results);
        }
        
        loadDynamicConfigs(); // 목록 새로고침
        loadAppConfigsStatus(); // 상태 새로고침
      } else {
        toast.error(data.message || '검증 및 정리에 실패했습니다.');
      }
    } catch (error) {
      console.error('검증 및 정리 실패:', error);
      toast.error('검증 및 정리에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveAppAndContainer = async (appName) => {
    if (!window.confirm(`정말로 앱 "${appName}"과 연결된 컨테이너를 모두 삭제하시겠습니까?`)) {
      return;
    }

    try {
      setLoading(true);
      const data = await safeFetch(`${API_BASE_URL}/api/nginx/apps/${appName}/complete`, {
        method: 'DELETE',
      });
      
      if (data.success) {
        toast.success(data.message);
        loadDynamicConfigs();
        loadAppConfigsStatus();
      } else {
        toast.error(data.message || '삭제에 실패했습니다.');
        console.log('삭제 상세 결과:', data.data);
      }
    } catch (error) {
      console.error('앱 및 컨테이너 삭제 실패:', error);
      toast.error('삭제에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveConfigOnly = async (appName) => {
    if (!window.confirm(`정말로 앱 "${appName}"의 설정 파일만 삭제하시겠습니까?`)) {
      return;
    }

    try {
      setLoading(true);
      const data = await safeFetch(`${API_BASE_URL}/api/nginx/remove/${appName}`, {
        method: 'DELETE',
      });
      
      if (data.success) {
        toast.success(data.message);
        loadDynamicConfigs();
        loadAppConfigsStatus();
      } else {
        toast.error(data.message || '설정 삭제에 실패했습니다.');
      }
    } catch (error) {
      console.error('설정 삭제 실패:', error);
      toast.error('설정 삭제에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusChip = (status) => {
    if (status.healthy) {
      return <Chip icon={<CheckIcon />} label="정상" color="success" size="small" />;
    } else if (status.exists && status.valid && status.container_exists && !status.container_running) {
      return <Chip icon={<WarningIcon />} label="컨테이너 중지됨" color="warning" size="small" />;
    } else if (status.exists && status.valid && !status.container_exists) {
      return <Chip icon={<ErrorIcon />} label="컨테이너 없음" color="error" size="small" />;
    } else if (status.exists && !status.valid) {
      return <Chip icon={<ErrorIcon />} label="설정 오류" color="error" size="small" />;
    } else if (!status.exists) {
      return <Chip icon={<ErrorIcon />} label="파일 없음" color="error" size="small" />;
    } else {
      return <Chip icon={<InfoIcon />} label="확인 필요" color="info" size="small" />;
    }
  };

  const getIssuesText = (issues) => {
    if (!issues || issues.length === 0) return '';
    
    if (issues.length <= 2) {
      return issues.join(', ');
    } else {
      return `${issues.slice(0, 2).join(', ')} 외 ${issues.length - 2}개 더`;
    }
  };

  const refreshAll = () => {
    loadDynamicConfigs();
    loadAppConfigsStatus();
    testNginxConfig();
  };

  // 수동 정리
  const handleManualCleanup = async () => {
    if (!cleanupDialog.activeApps.trim()) {
      setError('활성 앱 목록을 입력해주세요');
      return;
    }

    try {
      setLoading(true);
      const activeApps = cleanupDialog.activeApps.split(',').map(app => app.trim()).filter(app => app);
      
      const data = await safeFetch(`${API_BASE_URL}/api/nginx/cleanup/manual`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ active_apps: activeApps }),
      });
      
      if (data.success) {
        setSuccess(data.message);
        setCleanupDialog({ open: false, activeApps: '' });
        loadDynamicConfigs();
      } else {
        setError(data.message || '수동 정리에 실패했습니다.');
      }
    } catch (error) {
      console.error('수동 정리 실패:', error);
      setError('수동 정리에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 특정 설정 삭제
  const handleDeleteConfig = async () => {
    try {
      setLoading(true);
      const data = await safeFetch(`${API_BASE_URL}/api/nginx/remove/${deleteDialog.subdomain}`, {
        method: 'DELETE',
      });
      
      if (data.success) {
        setSuccess(data.message);
        setDeleteDialog({ open: false, subdomain: '' });
        loadDynamicConfigs();
      } else {
        setError(data.message || '설정 삭제에 실패했습니다.');
      }
    } catch (error) {
      console.error('설정 삭제 실패:', error);
      setError('설정 삭제에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // Nginx 리로드
  const handleReloadNginx = async () => {
    try {
      setLoading(true);
      const data = await safeFetch(`${API_BASE_URL}/api/nginx/reload`, {
        method: 'POST',
      });
      
      if (data.success) {
        setSuccess(data.message);
        testNginxConfig();
      } else {
        setError(data.message || 'Nginx 리로드에 실패했습니다.');
      }
    } catch (error) {
      console.error('Nginx 리로드 실패:', error);
      setError('Nginx 리로드에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshAll();
  }, []);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Nginx 관리
      </Typography>

      {/* 에러/성공 메시지 */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

      {/* 상단 액션 버튼들 */}
      <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
        <Button
          variant="contained"
          startIcon={<RefreshIcon />}
          onClick={refreshAll}
          disabled={loading}
        >
          새로고침
        </Button>
        
        <Button
          variant="outlined"
          startIcon={<CleanIcon />}
          onClick={handleAutoCleanup}
          disabled={loading}
        >
          자동 정리
        </Button>

        <Button
          variant="outlined"
          startIcon={<SettingsIcon />}
          onClick={handleValidateAndCleanup}
          disabled={loading}
        >
          검증 및 정리
        </Button>

        <Button
          variant="outlined"
          onClick={handleReloadNginx}
          disabled={loading}
        >
          Nginx 리로드
        </Button>
      </Stack>

      {/* Nginx 상태 */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Nginx 상태
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {nginxStatus.loading ? (
            <CircularProgress size={20} />
          ) : (
            <Chip
              icon={nginxStatus.valid ? <CheckIcon /> : <ErrorIcon />}
              label={nginxStatus.valid ? '정상' : '오류'}
              color={nginxStatus.valid ? 'success' : 'error'}
            />
          )}
          <Typography variant="body2">
            설정 파일 유효성: {nginxStatus.valid === null ? '확인 중...' : (nginxStatus.valid ? '정상' : '오류')}
          </Typography>
        </Box>
      </Paper>

      {/* 전체 상태 요약 */}
      {appConfigsStatus && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            앱 설정 상태 요약
          </Typography>
          <Stack direction="row" spacing={3}>
            <Typography variant="body2">
              전체: {appConfigsStatus.total_configs}개
            </Typography>
            <Typography variant="body2" color="success.main">
              정상: {appConfigsStatus.healthy_configs}개
            </Typography>
            <Typography variant="body2" color="error.main">
              문제: {appConfigsStatus.configs_with_issues}개
            </Typography>
          </Stack>
        </Paper>
      )}

      {/* 앱 설정 테이블 */}
      <Paper sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ p: 2, pb: 0 }}>
          앱 설정 목록
        </Typography>
        
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : appConfigsStatus && appConfigsStatus.statuses ? (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>앱 이름</TableCell>
                  <TableCell>상태</TableCell>
                  <TableCell>컨테이너</TableCell>
                  <TableCell>문제점</TableCell>
                  <TableCell align="right">액션</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {appConfigsStatus.statuses.map((status) => (
                  <TableRow key={status.app_name}>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {status.app_name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {status.config_file}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {getStatusChip(status)}
                    </TableCell>
                    <TableCell>
                      {status.container_name ? (
                        <Box>
                          <Typography variant="body2" fontWeight="medium">
                            {status.container_name}
                          </Typography>
                          <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
                            <Chip
                              label={status.container_exists ? '존재' : '없음'}
                              color={status.container_exists ? 'success' : 'error'}
                              size="small"
                              variant="outlined"
                            />
                            {status.container_exists && (
                              <Chip
                                label={status.container_running ? '실행중' : '중지됨'}
                                color={status.container_running ? 'success' : 'warning'}
                                size="small"
                                variant="outlined"
                              />
                            )}
                          </Stack>
                        </Box>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          컨테이너 정보 없음
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {status.issues && status.issues.length > 0 ? (
                        <Tooltip title={status.issues.join(', ')} arrow>
                          <Typography variant="body2" color="error.main">
                            {getIssuesText(status.issues)}
                          </Typography>
                        </Tooltip>
                      ) : (
                        <Typography variant="body2" color="success.main">
                          문제 없음
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        <Tooltip title="설정 파일만 삭제">
                          <IconButton
                            size="small"
                            color="warning"
                            onClick={() => handleRemoveConfigOnly(status.app_name)}
                            disabled={loading}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="설정 파일 + 컨테이너 삭제">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleRemoveAppAndContainer(status.app_name)}
                            disabled={loading}
                          >
                            <CleanIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography color="text.secondary">
              앱 설정 정보를 불러오는 중...
            </Typography>
          </Box>
        )}
      </Paper>

      {/* 수동 정리 다이얼로그 */}
      <Dialog open={cleanupDialog.open} onClose={() => setCleanupDialog({ open: false, activeApps: '' })}>
        <DialogTitle>수동 정리</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="활성 앱 목록 (쉼표로 구분)"
            fullWidth
            variant="outlined"
            value={cleanupDialog.activeApps}
            onChange={(e) => setCleanupDialog({ ...cleanupDialog, activeApps: e.target.value })}
            placeholder="app1, app2, app3"
            helperText="현재 활성화된 앱들의 서브도메인을 쉼표로 구분하여 입력하세요"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCleanupDialog({ open: false, activeApps: '' })}>
            취소
          </Button>
          <Button onClick={handleManualCleanup} variant="contained">
            정리 실행
          </Button>
        </DialogActions>
      </Dialog>

      {/* 삭제 확인 다이얼로그 */}
      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, subdomain: '' })}>
        <DialogTitle>설정 삭제 확인</DialogTitle>
        <DialogContent>
          <Typography>
            정말로 "{deleteDialog.subdomain}" 설정을 삭제하시겠습니까?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, subdomain: '' })}>
            취소
          </Button>
          <Button onClick={handleDeleteConfig} color="error" variant="contained">
            삭제
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default NginxManagement; 