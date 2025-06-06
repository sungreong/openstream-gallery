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
  Snackbar
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  CleaningServices as CleanIcon,
  Settings as SettingsIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import { safeFetch, formatErrorMessage } from '../utils/errorHandler';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

const NginxManagement = () => {
  const [dynamicConfigs, setDynamicConfigs] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [deleteDialog, setDeleteDialog] = useState({ open: false, subdomain: '' });
  const [cleanupDialog, setCleanupDialog] = useState({ open: false, activeApps: '' });
  const [nginxStatus, setNginxStatus] = useState({ valid: null, loading: false });

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
    setLoading(true);
    try {
      const data = await safeFetch(`${API_BASE_URL}/api/nginx/cleanup/auto`, {
        method: 'POST'
      });
      
      if (data.success) {
        setSuccess(data.message || '자동 정리가 완료되었습니다.');
        loadDynamicConfigs();
      } else {
        setError(data.message || '자동 정리 실패');
      }
    } catch (err) {
      console.error('handleAutoCleanup error:', err);
      setError(formatErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  // 수동 정리
  const handleManualCleanup = async () => {
    if (!cleanupDialog.activeApps.trim()) {
      setError('활성 앱 목록을 입력해주세요');
      return;
    }

    setLoading(true);
    try {
      const activeApps = cleanupDialog.activeApps
        .split(',')
        .map(app => app.trim())
        .filter(app => app);

      const data = await safeFetch(`${API_BASE_URL}/api/nginx/cleanup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ active_apps: activeApps })
      });
      
      if (data.success) {
        setSuccess(data.message || '수동 정리가 완료되었습니다.');
        loadDynamicConfigs();
        setCleanupDialog({ open: false, activeApps: '' });
      } else {
        setError(data.message || '수동 정리 실패');
      }
    } catch (err) {
      console.error('handleManualCleanup error:', err);
      setError(formatErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  // 특정 설정 파일 삭제
  const handleDeleteConfig = async () => {
    if (!deleteDialog.subdomain) return;

    setLoading(true);
    try {
      const data = await safeFetch(`${API_BASE_URL}/api/nginx/config/${deleteDialog.subdomain}`, {
        method: 'DELETE'
      });
      
      if (data.success) {
        setSuccess(data.message || '설정 파일이 삭제되었습니다.');
        loadDynamicConfigs();
        setDeleteDialog({ open: false, subdomain: '' });
      } else {
        setError(data.message || '설정 파일 삭제 실패');
      }
    } catch (err) {
      console.error('handleDeleteConfig error:', err);
      setError(formatErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  // Nginx 리로드
  const handleReloadNginx = async () => {
    setLoading(true);
    try {
      const data = await safeFetch(`${API_BASE_URL}/api/nginx/reload`, {
        method: 'POST'
      });
      
      if (data.success) {
        setSuccess(data.message || 'Nginx가 성공적으로 리로드되었습니다.');
        testNginxConfig();
      } else {
        setError(data.message || 'Nginx 리로드 실패');
      }
    } catch (err) {
      console.error('handleReloadNginx error:', err);
      setError(formatErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDynamicConfigs();
    testNginxConfig();
  }, []);

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        🔧 Nginx 설정 관리
      </Typography>

      {/* 상태 표시 */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Typography variant="h6">Nginx 상태</Typography>
                <Button
                  size="small"
                  onClick={testNginxConfig}
                  disabled={nginxStatus.loading}
                  startIcon={nginxStatus.loading ? <CircularProgress size={16} /> : <CheckIcon />}
                >
                  상태 확인
                </Button>
              </Box>
              <Box display="flex" alignItems="center" mt={1}>
                {nginxStatus.loading ? (
                  <CircularProgress size={20} />
                ) : nginxStatus.valid === true ? (
                  <Chip icon={<CheckIcon />} label="정상" color="success" />
                ) : nginxStatus.valid === false ? (
                  <Chip icon={<ErrorIcon />} label="오류" color="error" />
                ) : (
                  <Chip icon={<InfoIcon />} label="확인 필요" color="default" />
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>설정 파일 현황</Typography>
              {dynamicConfigs && (
                <Box>
                  <Typography variant="body2" color="textSecondary">
                    총 {dynamicConfigs.total_count}개 파일
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    앱: {dynamicConfigs.app_count}개, 시스템: {dynamicConfigs.system_files.length}개
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* 액션 버튼들 */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>관리 작업</Typography>
        <Grid container spacing={2}>
          <Grid item>
            <Button
              variant="contained"
              startIcon={<RefreshIcon />}
              onClick={loadDynamicConfigs}
              disabled={loading}
            >
              새로고침
            </Button>
          </Grid>
          <Grid item>
            <Button
              variant="contained"
              color="warning"
              startIcon={<CleanIcon />}
              onClick={handleAutoCleanup}
              disabled={loading}
            >
              자동 정리
            </Button>
          </Grid>
          <Grid item>
            <Button
              variant="outlined"
              startIcon={<CleanIcon />}
              onClick={() => setCleanupDialog({ open: true, activeApps: '' })}
              disabled={loading}
            >
              수동 정리
            </Button>
          </Grid>
          <Grid item>
            <Button
              variant="contained"
              color="secondary"
              startIcon={<SettingsIcon />}
              onClick={handleReloadNginx}
              disabled={loading}
            >
              Nginx 리로드
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* 설정 파일 목록 */}
      <Grid container spacing={3}>
        {/* 앱 설정 파일들 */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                앱 설정 파일 ({dynamicConfigs?.app_count || 0}개)
              </Typography>
              {loading ? (
                <Box display="flex" justifyContent="center" p={2}>
                  <CircularProgress />
                </Box>
              ) : dynamicConfigs?.app_configs.length > 0 ? (
                <List>
                  {dynamicConfigs.app_configs.map((app, index) => (
                    <React.Fragment key={app}>
                      <ListItem>
                        <ListItemText
                          primary={`${app}.conf`}
                          secondary={`앱: ${app}`}
                        />
                        <ListItemSecondaryAction>
                          <IconButton
                            edge="end"
                            color="error"
                            onClick={() => setDeleteDialog({ open: true, subdomain: app })}
                            disabled={loading}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </ListItemSecondaryAction>
                      </ListItem>
                      {index < dynamicConfigs.app_configs.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Typography color="textSecondary" align="center" sx={{ py: 2 }}>
                  앱 설정 파일이 없습니다.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 시스템 설정 파일들 */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                시스템 파일 ({dynamicConfigs?.system_files.length || 0}개)
              </Typography>
              {dynamicConfigs?.system_files.length > 0 ? (
                <List dense>
                  {dynamicConfigs.system_files.map((file) => (
                    <ListItem key={file}>
                      <ListItemText
                        primary={file}
                        secondary="보호됨"
                      />
                      <Chip size="small" label="시스템" color="default" />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography color="textSecondary" align="center" sx={{ py: 2 }}>
                  시스템 파일이 없습니다.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* 삭제 확인 다이얼로그 */}
      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, subdomain: '' })}>
        <DialogTitle>설정 파일 삭제</DialogTitle>
        <DialogContent>
          <Typography>
            정말로 <strong>{deleteDialog.subdomain}.conf</strong> 파일을 삭제하시겠습니까?
          </Typography>
          <Alert severity="warning" sx={{ mt: 2 }}>
            이 작업은 되돌릴 수 없으며, 해당 앱의 Nginx 설정이 제거됩니다.
          </Alert>
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

      {/* 수동 정리 다이얼로그 */}
      <Dialog open={cleanupDialog.open} onClose={() => setCleanupDialog({ open: false, activeApps: '' })}>
        <DialogTitle>수동 설정 정리</DialogTitle>
        <DialogContent>
          <Typography gutterBottom>
            유지할 활성 앱들의 이름을 쉼표로 구분하여 입력하세요:
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={3}
            value={cleanupDialog.activeApps}
            onChange={(e) => setCleanupDialog({ ...cleanupDialog, activeApps: e.target.value })}
            placeholder="예: app1, app2, app3"
            sx={{ mt: 2 }}
          />
          <Alert severity="info" sx={{ mt: 2 }}>
            입력하지 않은 앱들의 설정 파일은 모두 삭제됩니다.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCleanupDialog({ open: false, activeApps: '' })}>
            취소
          </Button>
          <Button onClick={handleManualCleanup} color="warning" variant="contained">
            정리 실행
          </Button>
        </DialogActions>
      </Dialog>

      {/* 성공/오류 메시지 */}
      <Snackbar
        open={!!success}
        autoHideDuration={6000}
        onClose={() => setSuccess('')}
      >
        <Alert onClose={() => setSuccess('')} severity="success">
          {success}
        </Alert>
      </Snackbar>

      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError('')}
      >
        <Alert onClose={() => setError('')} severity="error">
          {typeof error === 'string' ? error : formatErrorMessage(error)}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default NginxManagement; 