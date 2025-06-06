import React, { useState } from 'react';
import {
  Container,
  Typography,
  Box,
  Button,
  Card,
  CardContent,
  CardActions,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Chip,
  IconButton
} from '@mui/material';
import { Add, Edit, Delete, GitHub, Code } from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { gitCredentialsApi } from '../services/api';
import { formatErrorMessage } from '../utils/errorHandler';

const GitCredentials = () => {
  const [open, setOpen] = useState(false);
  const [editingCredential, setEditingCredential] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    git_provider: 'github',
    auth_type: 'token',
    username: '',
    token: '',
    ssh_key: ''
  });
  const [error, setError] = useState('');

  const queryClient = useQueryClient();

  // Git 인증 정보 목록 조회
  const { data: credentials = [], isLoading } = useQuery({
    queryKey: ['git-credentials'],
    queryFn: gitCredentialsApi.getAll
  });

  // Git 인증 정보 생성
  const createMutation = useMutation({
    mutationFn: gitCredentialsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries(['git-credentials']);
      handleClose();
    },
    onError: (error) => {
      setError(error.response?.data?.detail || '생성 중 오류가 발생했습니다.');
    }
  });

  // Git 인증 정보 수정
  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => gitCredentialsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['git-credentials']);
      handleClose();
    },
    onError: (error) => {
      setError(error.response?.data?.detail || '수정 중 오류가 발생했습니다.');
    }
  });

  // Git 인증 정보 삭제
  const deleteMutation = useMutation({
    mutationFn: gitCredentialsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries(['git-credentials']);
    }
  });

  const handleOpen = (credential = null) => {
    if (credential) {
      setEditingCredential(credential);
      setFormData({
        name: credential.name,
        git_provider: credential.git_provider,
        auth_type: credential.auth_type,
        username: credential.username || '',
        token: '',
        ssh_key: ''
      });
    } else {
      setEditingCredential(null);
      setFormData({
        name: '',
        git_provider: 'github',
        auth_type: 'token',
        username: '',
        token: '',
        ssh_key: ''
      });
    }
    setError('');
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setEditingCredential(null);
    setFormData({
      name: '',
      git_provider: 'github',
      auth_type: 'token',
      username: '',
      token: '',
      ssh_key: ''
    });
    setError('');
  };

  const handleSubmit = () => {
    if (!formData.name.trim()) {
      setError('이름을 입력해주세요.');
      return;
    }

    if (formData.auth_type === 'token' && !formData.token.trim()) {
      setError('토큰을 입력해주세요.');
      return;
    }

    if (formData.auth_type === 'ssh' && !formData.ssh_key.trim()) {
      setError('SSH 키를 입력해주세요.');
      return;
    }

    const submitData = {
      name: formData.name,
      git_provider: formData.git_provider,
      auth_type: formData.auth_type,
      username: formData.username || null,
      token: formData.auth_type === 'token' ? formData.token : null,
      ssh_key: formData.auth_type === 'ssh' ? formData.ssh_key : null
    };

    if (editingCredential) {
      updateMutation.mutate({ id: editingCredential.id, data: submitData });
    } else {
      createMutation.mutate(submitData);
    }
  };

  const handleDelete = (id) => {
    if (window.confirm('정말로 이 Git 인증 정보를 삭제하시겠습니까?')) {
      deleteMutation.mutate(id);
    }
  };

  const getProviderIcon = (provider) => {
    switch (provider) {
      case 'github':
        return <GitHub />;
      case 'gitlab':
        return <Code />;
      default:
        return <GitHub />;
    }
  };

  const getAuthTypeColor = (authType) => {
    return authType === 'token' ? 'primary' : 'secondary';
  };

  if (isLoading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Typography>로딩 중...</Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Git 인증 정보 관리
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => handleOpen()}
        >
          새 인증 정보 추가
        </Button>
      </Box>

      <Grid container spacing={3}>
        {credentials.map((credential) => (
          <Grid item xs={12} md={6} lg={4} key={credential.id}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  {getProviderIcon(credential.git_provider)}
                  <Typography variant="h6" sx={{ ml: 1 }}>
                    {credential.name}
                  </Typography>
                </Box>
                
                <Typography color="text.secondary" gutterBottom>
                  {credential.git_provider.toUpperCase()}
                </Typography>
                
                <Box sx={{ mb: 1 }}>
                  <Chip
                    label={credential.auth_type.toUpperCase()}
                    color={getAuthTypeColor(credential.auth_type)}
                    size="small"
                  />
                </Box>
                
                {credential.username && (
                  <Typography variant="body2" color="text.secondary">
                    사용자명: {credential.username}
                  </Typography>
                )}
                
                <Typography variant="body2" color="text.secondary">
                  생성일: {new Date(credential.created_at).toLocaleDateString()}
                </Typography>
              </CardContent>
              
              <CardActions>
                <IconButton
                  size="small"
                  onClick={() => handleOpen(credential)}
                  color="primary"
                >
                  <Edit />
                </IconButton>
                <IconButton
                  size="small"
                  onClick={() => handleDelete(credential.id)}
                  color="error"
                >
                  <Delete />
                </IconButton>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {credentials.length === 0 && (
        <Box sx={{ textAlign: 'center', mt: 4 }}>
          <Typography variant="h6" color="text.secondary">
            등록된 Git 인증 정보가 없습니다.
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Private 저장소에 접근하려면 Git 인증 정보를 추가해주세요.
          </Typography>
        </Box>
      )}

      {/* Git 인증 정보 추가/수정 다이얼로그 */}
      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingCredential ? 'Git 인증 정보 수정' : '새 Git 인증 정보 추가'}
        </DialogTitle>
        
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {typeof error === 'string' ? error : formatErrorMessage(error)}
            </Alert>
          )}
          
          <TextField
            autoFocus
            margin="dense"
            label="이름"
            fullWidth
            variant="outlined"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            sx={{ mb: 2 }}
          />
          
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Git 제공자</InputLabel>
            <Select
              value={formData.git_provider}
              label="Git 제공자"
              onChange={(e) => setFormData({ ...formData, git_provider: e.target.value })}
            >
              <MenuItem value="github">GitHub</MenuItem>
              <MenuItem value="gitlab">GitLab</MenuItem>
              <MenuItem value="bitbucket">Bitbucket</MenuItem>
              <MenuItem value="other">기타</MenuItem>
            </Select>
          </FormControl>
          
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>인증 방식</InputLabel>
            <Select
              value={formData.auth_type}
              label="인증 방식"
              onChange={(e) => setFormData({ ...formData, auth_type: e.target.value })}
            >
              <MenuItem value="token">Personal Access Token</MenuItem>
              <MenuItem value="ssh">SSH Key</MenuItem>
            </Select>
          </FormControl>
          
          {formData.auth_type === 'token' && (
            <>
              <TextField
                margin="dense"
                label="사용자명 (선택사항)"
                fullWidth
                variant="outlined"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                sx={{ mb: 2 }}
                helperText="GitHub의 경우 보통 'token' 또는 사용자명을 입력"
              />
              
              <TextField
                margin="dense"
                label="Personal Access Token"
                fullWidth
                variant="outlined"
                type="password"
                value={formData.token}
                onChange={(e) => setFormData({ ...formData, token: e.target.value })}
                sx={{ mb: 2 }}
                helperText="GitHub Settings > Developer settings > Personal access tokens에서 생성"
              />
            </>
          )}
          
          {formData.auth_type === 'ssh' && (
            <TextField
              margin="dense"
              label="SSH Private Key"
              fullWidth
              variant="outlined"
              multiline
              rows={6}
              value={formData.ssh_key}
              onChange={(e) => setFormData({ ...formData, ssh_key: e.target.value })}
              sx={{ mb: 2 }}
              helperText="-----BEGIN OPENSSH PRIVATE KEY-----로 시작하는 전체 SSH 개인 키"
            />
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={handleClose}>취소</Button>
          <Button 
            onClick={handleSubmit}
            variant="contained"
            disabled={createMutation.isLoading || updateMutation.isLoading}
          >
            {editingCredential ? '수정' : '추가'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default GitCredentials; 