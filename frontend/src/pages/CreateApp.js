import React, { useState } from 'react';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Card,
  CardContent,
  Divider,
} from '@mui/material';
import { ExpandMore, Code, Info } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import axios from 'axios';
import toast from 'react-hot-toast';
import { appsApi, gitCredentialsApi } from '../services/api';

const CreateApp = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    git_url: '',
    branch: 'main',
    main_file: 'streamlit_app.py',
    git_credential_id: '',
    base_dockerfile_type: 'auto',
  });

  const [dockerfileContent, setDockerfileContent] = useState(null);
  const [loadingDockerfile, setLoadingDockerfile] = useState(false);

  // Git 인증 정보 목록 조회
  const { data: gitCredentials = [] } = useQuery({
    queryKey: ['git-credentials'],
    queryFn: gitCredentialsApi.getAll
  });

  // 베이스 Dockerfile 목록 조회
  const { data: baseDockerfiles = [], isLoading: isLoadingDockerfiles, error: dockerfilesError } = useQuery({
    queryKey: ['base-dockerfiles'],
    queryFn: async () => {
      console.log('베이스 Dockerfile 목록 조회 시작...');
      const response = await axios.get('/api/dockerfiles/base-types');
      console.log('베이스 Dockerfile 목록 조회 성공:', response.data);
      return response.data.base_dockerfiles;
    },
    onError: (error) => {
      console.error('베이스 Dockerfile 목록 조회 실패:', error);
      toast.error('베이스 Dockerfile 목록을 가져오는데 실패했습니다.');
    }
  });

  const createAppMutation = useMutation({
    mutationFn: async (appData) => {
      const submitData = {
        ...appData,
        git_credential_id: appData.git_credential_id || null
      };
      return appsApi.create(submitData);
    },
    onSuccess: (data) => {
      toast.success('앱이 생성되었습니다.');
      navigate(`/apps/${data.id}`);
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || '앱 생성에 실패했습니다.');
    },
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value,
    });

    // 베이스 Dockerfile 타입이 변경되면 내용을 가져옴
    if (name === 'base_dockerfile_type' && value !== 'auto') {
      fetchDockerfileContent(value);
    } else if (name === 'base_dockerfile_type' && value === 'auto') {
      setDockerfileContent(null);
    }
  };

  const fetchDockerfileContent = async (dockerfileType) => {
    if (!dockerfileType || dockerfileType === 'auto') return;
    
    setLoadingDockerfile(true);
    try {
      const response = await axios.get(`/api/dockerfiles/base-content/${dockerfileType}`);
      if (response.data.success) {
        setDockerfileContent(response.data);
      }
    } catch (error) {
      console.error('Dockerfile 내용 조회 실패:', error);
      toast.error('Dockerfile 내용을 가져오는데 실패했습니다.');
    } finally {
      setLoadingDockerfile(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    createAppMutation.mutate(formData);
  };

  return (
    <Container maxWidth="md">
      <Paper elevation={3} sx={{ padding: 4, mt: 4 }}>
        <Typography variant="h4" gutterBottom>
          새 앱 만들기
        </Typography>
        <Typography variant="body1" color="text.secondary" gutterBottom>
          Git 저장소에서 Streamlit 앱을 배포하세요.
        </Typography>

        <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
          <TextField
            margin="normal"
            required
            fullWidth
            id="name"
            label="앱 이름"
            name="name"
            value={formData.name}
            onChange={handleChange}
            helperText="앱을 식별할 수 있는 이름을 입력하세요."
          />

          <TextField
            margin="normal"
            fullWidth
            id="description"
            label="설명"
            name="description"
            multiline
            rows={3}
            value={formData.description}
            onChange={handleChange}
            helperText="앱에 대한 간단한 설명을 입력하세요. (선택사항)"
          />

          <TextField
            margin="normal"
            required
            fullWidth
            id="git_url"
            label="Git 저장소 URL"
            name="git_url"
            value={formData.git_url}
            onChange={handleChange}
            helperText="예: https://github.com/username/repository"
          />

          <TextField
            margin="normal"
            fullWidth
            id="branch"
            label="브랜치"
            name="branch"
            value={formData.branch}
            onChange={handleChange}
            helperText="배포할 브랜치 이름 (기본값: main)"
          />

          <TextField
            margin="normal"
            fullWidth
            id="main_file"
            label="메인 파일"
            name="main_file"
            value={formData.main_file}
            onChange={handleChange}
            helperText="실행할 Streamlit 파일 이름 (기본값: streamlit_app.py)"
          />

          <FormControl fullWidth margin="normal">
            <InputLabel id="base-dockerfile-label">베이스 이미지 타입</InputLabel>
            <Select
              labelId="base-dockerfile-label"
              id="base_dockerfile_type"
              name="base_dockerfile_type"
              value={formData.base_dockerfile_type}
              label="베이스 이미지 타입"
              onChange={handleChange}
              disabled={isLoadingDockerfiles}
            >
              <MenuItem value="auto">
                <Box>
                  <Typography variant="body2" fontWeight="bold">
                    🤖 자동 선택
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    requirements.txt를 분석하여 최적의 베이스 이미지를 자동으로 선택
                  </Typography>
                </Box>
              </MenuItem>
              {isLoadingDockerfiles ? (
                <MenuItem disabled>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CircularProgress size={16} />
                    <Typography variant="body2">베이스 이미지 목록 로딩 중...</Typography>
                  </Box>
                </MenuItem>
              ) : dockerfilesError ? (
                <MenuItem disabled>
                  <Typography variant="body2" color="error">
                    베이스 이미지 목록을 불러올 수 없습니다.
                  </Typography>
                </MenuItem>
              ) : (
                baseDockerfiles.map((dockerfile) => (
                  <MenuItem key={dockerfile.type} value={dockerfile.type}>
                    <Box>
                      <Typography variant="body2" fontWeight="bold">
                        {dockerfile.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {dockerfile.description}
                      </Typography>
                      <Box sx={{ mt: 0.5 }}>
                        {dockerfile.recommended_for.map((item, index) => (
                          <Chip
                            key={index}
                            label={item}
                            size="small"
                            variant="outlined"
                            sx={{ mr: 0.5, mb: 0.5 }}
                          />
                        ))}
                      </Box>
                    </Box>
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>

          <FormControl fullWidth margin="normal">
            <InputLabel id="git-credential-label">Git 인증 정보 (선택사항)</InputLabel>
            <Select
              labelId="git-credential-label"
              id="git_credential_id"
              name="git_credential_id"
              value={formData.git_credential_id}
              label="Git 인증 정보 (선택사항)"
              onChange={handleChange}
            >
              <MenuItem value="">
                <em>없음 (공개 저장소)</em>
              </MenuItem>
              {gitCredentials.map((credential) => (
                <MenuItem key={credential.id} value={credential.id}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <span>{credential.name}</span>
                    <Chip 
                      label={credential.git_provider.toUpperCase()} 
                      size="small" 
                      variant="outlined"
                    />
                    <Chip 
                      label={credential.auth_type.toUpperCase()} 
                      size="small" 
                      color={credential.auth_type === 'token' ? 'primary' : 'secondary'}
                    />
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* 베이스 Dockerfile 내용 미리보기 */}
          {formData.base_dockerfile_type !== 'auto' && (
            <Box sx={{ mt: 3 }}>
              <Accordion>
                <AccordionSummary
                  expandIcon={<ExpandMore />}
                  aria-controls="dockerfile-content"
                  id="dockerfile-header"
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Code color="primary" />
                    <Typography variant="h6">
                      베이스 Dockerfile 미리보기
                    </Typography>
                    {loadingDockerfile && (
                      <CircularProgress size={20} />
                    )}
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  {dockerfileContent ? (
                    <Box>
                      {/* Dockerfile 정보 */}
                      <Card variant="outlined" sx={{ mb: 2 }}>
                        <CardContent>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <Info color="info" />
                            <Typography variant="subtitle1" fontWeight="bold">
                              {dockerfileContent.info.name}
                            </Typography>
                          </Box>
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            {dockerfileContent.info.description}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 2, mt: 1, flexWrap: 'wrap' }}>
                            <Chip 
                              label={`베이스 이미지: ${dockerfileContent.info.base_image}`} 
                              size="small" 
                              variant="outlined" 
                            />
                            <Chip 
                              label={`${dockerfileContent.lines}줄`} 
                              size="small" 
                              color="primary" 
                            />
                            <Chip 
                              label={`${Math.round(dockerfileContent.size / 1024)}KB`} 
                              size="small" 
                              color="secondary" 
                            />
                          </Box>
                          
                          {/* Features 리스트 */}
                          {dockerfileContent.info.features && dockerfileContent.info.features.length > 0 && (
                            <Box sx={{ mt: 2 }}>
                              <Typography variant="caption" color="text.secondary" gutterBottom>
                                📦 포함된 기능:
                              </Typography>
                              <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
                                {dockerfileContent.info.features.map((feature, index) => (
                                  <Chip
                                    key={index}
                                    label={feature}
                                    size="small"
                                    color="info"
                                    variant="outlined"
                                  />
                                ))}
                              </Box>
                            </Box>
                          )}
                        </CardContent>
                      </Card>

                      <Divider sx={{ my: 2 }} />

                      {/* Dockerfile 내용 */}
                      <Typography variant="subtitle2" gutterBottom>
                        📄 {dockerfileContent.filename}
                      </Typography>
                      <Box
                        component="pre"
                        sx={{
                          backgroundColor: '#f5f5f5',
                          padding: 2,
                          borderRadius: 1,
                          overflow: 'auto',
                          maxHeight: 400,
                          fontSize: '0.875rem',
                          fontFamily: 'monospace',
                          border: '1px solid #e0e0e0',
                        }}
                      >
                        {dockerfileContent.content}
                      </Box>

                      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                        💡 이 베이스 Dockerfile에 당신의 앱 설정이 추가되어 최종 Dockerfile이 생성됩니다.
                      </Typography>
                    </Box>
                  ) : (
                    <Box sx={{ textAlign: 'center', py: 3 }}>
                      <Typography variant="body2" color="text.secondary">
                        베이스 Dockerfile을 선택하면 내용을 미리볼 수 있습니다.
                      </Typography>
                    </Box>
                  )}
                </AccordionDetails>
              </Accordion>
            </Box>
          )}

          <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
            <Button
              type="submit"
              variant="contained"
              disabled={createAppMutation.isLoading}
              sx={{ minWidth: 120 }}
            >
              {createAppMutation.isLoading ? (
                <CircularProgress size={24} />
              ) : (
                '앱 생성'
              )}
            </Button>
            <Button
              variant="outlined"
              onClick={() => navigate('/dashboard')}
              disabled={createAppMutation.isLoading}
            >
              취소
            </Button>
          </Box>
        </Box>
      </Paper>
    </Container>
  );
};

export default CreateApp; 