import React, { useState, useEffect } from 'react';
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
  Alert,
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
    custom_base_image: '',
    custom_dockerfile_commands: '',
  });

  const [dockerfileContent, setDockerfileContent] = useState(null);
  const [loadingDockerfile, setLoadingDockerfile] = useState(false);
  const [finalDockerfileContent, setFinalDockerfileContent] = useState(null);
  const [loadingFinalDockerfile, setLoadingFinalDockerfile] = useState(false);
  const [useCustomBaseImage, setUseCustomBaseImage] = useState(false);

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

  const fetchFinalDockerfilePreview = async () => {
    setLoadingFinalDockerfile(true);
    try {
      const requestData = {
        base_dockerfile_type: formData.base_dockerfile_type,
        custom_base_image: useCustomBaseImage ? formData.custom_base_image : null,
        custom_dockerfile_commands: formData.custom_dockerfile_commands,
        main_file: formData.main_file || 'streamlit_app.py',
        git_url: formData.git_url
      };

      const response = await axios.post('/api/dockerfiles/preview-final', requestData);
      if (response.data.success) {
        setFinalDockerfileContent(response.data);
      }
    } catch (error) {
      console.error('최종 Dockerfile 미리보기 조회 실패:', error);
      // 에러는 조용히 처리 (실시간 미리보기이므로)
    } finally {
      setLoadingFinalDockerfile(false);
    }
  };

  // 최종 Dockerfile 미리보기 업데이트
  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      fetchFinalDockerfilePreview();
    }, 1000); // 1초 디바운스

    return () => clearTimeout(debounceTimer);
  }, [
    formData.base_dockerfile_type,
    formData.custom_base_image,
    formData.custom_dockerfile_commands,
    formData.main_file,
    formData.git_url,
    useCustomBaseImage
  ]);

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

          {/* 베이스 이미지 선택 방식 */}
          <Box sx={{ mt: 3, mb: 2 }}>
            <Typography variant="h6" gutterBottom>
              베이스 이미지 선택
            </Typography>
            
            <Box sx={{ mb: 2 }}>
              <Button
                variant={!useCustomBaseImage ? "contained" : "outlined"}
                onClick={() => setUseCustomBaseImage(false)}
                sx={{ mr: 2 }}
              >
                📦 미리 구성된 이미지
              </Button>
              <Button
                variant={useCustomBaseImage ? "contained" : "outlined"}
                onClick={() => setUseCustomBaseImage(true)}
              >
                🐳 사용자 정의 Docker 이미지
              </Button>
            </Box>

            {!useCustomBaseImage ? (
              // 기존 베이스 Dockerfile 선택
              <FormControl fullWidth>
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
            ) : (
              // 사용자 정의 Docker 이미지 입력
              <Box>
                <TextField
                  fullWidth
                  id="custom_base_image"
                  label="Docker 베이스 이미지"
                  name="custom_base_image"
                  value={formData.custom_base_image}
                  onChange={handleChange}
                  placeholder="예: python:3.11-slim, ubuntu:22.04, node:18-alpine"
                  helperText="Docker Hub의 이미지명:태그 형식으로 입력하세요"
                  sx={{
                    '& .MuiInputBase-input': {
                      fontFamily: 'monospace',
                    },
                  }}
                />
                
                <Box sx={{ mt: 2, p: 2, backgroundColor: '#fff3e0', borderRadius: 1, border: '1px solid #ffcc02' }}>
                  <Typography variant="caption" color="warning.main" sx={{ fontWeight: 'bold' }}>
                    ⚠️ 주의사항:
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ ml: 1, display: 'block', mt: 0.5 }}>
                    • 선택한 베이스 이미지가 존재하고 접근 가능한지 확인하세요<br/>
                    • Streamlit 실행에 필요한 Python이 설치되어 있어야 합니다<br/>
                    • 아래 추가 명령어에서 필요한 패키지들을 설치하세요
                  </Typography>
                </Box>
              </Box>
            )}
          </Box>

          {/* 사용자 정의 Docker 명령어 입력 - 베이스 이미지 선택 바로 다음에 배치 */}
          <Box sx={{ mt: 3, mb: 2 }}>
            <Accordion>
              <AccordionSummary
                expandIcon={<ExpandMore />}
                aria-controls="docker-commands-content"
                id="docker-commands-header"
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Code color="primary" />
                  <Typography variant="h6">
                    {useCustomBaseImage ? '추가 Docker 명령어' : '추가 Docker 명령어 (선택사항)'}
                  </Typography>
                  {formData.custom_dockerfile_commands && formData.custom_dockerfile_commands.trim() && (
                    <Chip 
                      label="설정됨" 
                      size="small" 
                      color="primary" 
                      variant="outlined"
                    />
                  )}
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  {useCustomBaseImage 
                    ? `선택한 베이스 이미지 (${formData.custom_base_image || 'Docker 이미지'})에 추가로 실행할 명령어를 입력하세요.`
                    : '선택한 베이스 이미지에 추가로 실행할 Docker 명령어를 입력하세요.'
                  }
                </Typography>
            
            <TextField
              fullWidth
              id="custom_dockerfile_commands"
              name="custom_dockerfile_commands"
              multiline
              rows={useCustomBaseImage ? 10 : 8}
              value={formData.custom_dockerfile_commands}
              onChange={handleChange}
              placeholder={useCustomBaseImage ? 
                `# 베이스 이미지: ${formData.custom_base_image || 'your-base-image'}
FROM ${formData.custom_base_image || 'your-base-image'}

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \\
    python3 \\
    python3-pip \\
    curl \\
    wget \\
    git

# Python 패키지 설치
RUN pip3 install --no-cache-dir \\
    streamlit \\
    pandas \\
    numpy

# 작업 디렉토리 설정
WORKDIR /app

# 환경변수 설정
ENV PYTHONPATH=/app
ENV STREAMLIT_SERVER_PORT=8501` :
                `# 시스템 패키지 설치 예시:
RUN apt-get update && apt-get install -y \\
    curl \\
    wget \\
    vim \\
    git

# Python 패키지 추가 설치 예시:
RUN pip install --no-cache-dir \\
    pandas==2.0.0 \\
    numpy==1.24.0 \\
    scikit-learn==1.3.0

# 환경변수 설정 예시:
ENV MY_CUSTOM_VAR=production
ENV PYTHONPATH=/app/custom

# 작업 디렉토리 및 파일 복사 예시:
# COPY custom_config.json /app/config/
# RUN chmod +x /app/scripts/setup.sh`}
              sx={{
                '& .MuiInputBase-input': {
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  lineHeight: 1.4,
                },
                '& .MuiOutlinedInput-root': {
                  backgroundColor: useCustomBaseImage ? '#f8f9fa' : '#fafafa',
                },
              }}
            />
            
                <Box sx={{ mt: 1, p: 2, backgroundColor: useCustomBaseImage ? '#e8f5e8' : '#e3f2fd', borderRadius: 1, border: useCustomBaseImage ? '1px solid #4caf50' : '1px solid #bbdefb' }}>
                  <Typography variant="caption" color={useCustomBaseImage ? 'success.main' : 'primary'} sx={{ fontWeight: 'bold' }}>
                    {useCustomBaseImage ? '🐳 사용자 정의 이미지 모드:' : '💡 팁:'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                    {useCustomBaseImage 
                      ? '이 명령어들로 완전한 Dockerfile이 생성됩니다. Python, Streamlit 설치 등 모든 설정을 포함해야 합니다.'
                      : '이 명령어들은 베이스 이미지 설정 후, requirements.txt 설치 전에 실행됩니다. 시스템 패키지나 추가 Python 패키지 설치, 환경변수 설정 등에 활용하세요.'
                    }
                  </Typography>
                </Box>
              </AccordionDetails>
            </Accordion>
          </Box>

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

          {/* 최종 Dockerfile 미리보기 */}
          <Box sx={{ mt: 3 }}>
            <Accordion defaultExpanded>
              <AccordionSummary
                expandIcon={<ExpandMore />}
                aria-controls="final-dockerfile-content"
                id="final-dockerfile-header"
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Code color="success" />
                  <Typography variant="h6">
                    최종 Dockerfile 미리보기
                  </Typography>
                  {loadingFinalDockerfile && (
                    <CircularProgress size={20} />
                  )}
                  <Chip 
                    label="실시간" 
                    size="small" 
                    color="success" 
                    variant="outlined"
                  />
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                {finalDockerfileContent ? (
                  <Box>
                    {/* 최종 Dockerfile 정보 */}
                    <Card variant="outlined" sx={{ mb: 2 }}>
                      <CardContent>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Info color="success" />
                          <Typography variant="subtitle1" fontWeight="bold">
                            {finalDockerfileContent.info.name || '최종 Dockerfile'}
                          </Typography>
                        </Box>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          선택한 설정을 바탕으로 생성되는 최종 Dockerfile입니다.
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 2, mt: 1, flexWrap: 'wrap' }}>
                          <Chip 
                            label={`베이스 이미지: ${finalDockerfileContent.info.base_image || 'N/A'}`} 
                            size="small" 
                            variant="outlined" 
                          />
                          <Chip 
                            label={`${finalDockerfileContent.lines}줄`} 
                            size="small" 
                            color="primary" 
                          />
                          <Chip 
                            label={`${Math.round(finalDockerfileContent.size / 1024)}KB`} 
                            size="small" 
                            color="secondary" 
                          />
                        </Box>
                        
                        {/* 구성 요소 표시 */}
                        <Box sx={{ mt: 2 }}>
                          <Typography variant="caption" color="text.secondary" gutterBottom>
                            📋 구성 요소:
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
                            {finalDockerfileContent.sections?.has_base && (
                              <Chip
                                label="베이스 Dockerfile"
                                size="small"
                                color="info"
                                variant="outlined"
                              />
                            )}
                            {finalDockerfileContent.sections?.has_custom_commands && (
                              <Chip
                                label="사용자 정의 명령어"
                                size="small"
                                color="warning"
                                variant="outlined"
                              />
                            )}
                            {finalDockerfileContent.sections?.has_app_specific && (
                              <Chip
                                label="앱별 설정"
                                size="small"
                                color="success"
                                variant="outlined"
                              />
                            )}
                            {useCustomBaseImage && (
                              <Chip
                                label="사용자 정의 베이스 이미지"
                                size="small"
                                color="primary"
                                variant="outlined"
                              />
                            )}
                          </Box>
                        </Box>

                        {/* Features 리스트 (있는 경우) */}
                        {finalDockerfileContent.info.features && finalDockerfileContent.info.features.length > 0 && (
                          <Box sx={{ mt: 2 }}>
                            <Typography variant="caption" color="text.secondary" gutterBottom>
                              🔧 포함된 기능:
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
                              {finalDockerfileContent.info.features.map((feature, index) => (
                                <Chip
                                  key={index}
                                  label={feature}
                                  size="small"
                                  color="success"
                                  variant="outlined"
                                />
                              ))}
                            </Box>
                          </Box>
                        )}
                      </CardContent>
                    </Card>

                    <Divider sx={{ my: 2 }} />

                    {/* 최종 Dockerfile 내용 */}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="subtitle2">
                        📄 최종 Dockerfile
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        실제 배포 시 생성되는 Dockerfile
                      </Typography>
                    </Box>
                    <Box
                      component="pre"
                      sx={{
                        backgroundColor: '#f8f9fa',
                        padding: 2,
                        borderRadius: 1,
                        overflow: 'auto',
                        maxHeight: 500,
                        fontSize: '0.875rem',
                        fontFamily: 'monospace',
                        border: '2px solid #28a745',
                        borderLeft: '4px solid #28a745',
                      }}
                    >
                      {finalDockerfileContent.content}
                    </Box>

                    <Alert severity="info" sx={{ mt: 2 }}>
                      <Typography variant="body2">
                        💡 <strong>실시간 미리보기:</strong> 위 내용이나 설정을 변경하면 최종 Dockerfile이 자동으로 업데이트됩니다.
                        실제 배포 시에는 Git 저장소의 파일들과 함께 이 Dockerfile이 빌드됩니다.
                      </Typography>
                    </Alert>
                  </Box>
                ) : (
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <CircularProgress sx={{ mb: 2 }} />
                    <Typography variant="body2" color="text.secondary">
                      최종 Dockerfile을 생성하고 있습니다...
                    </Typography>
                  </Box>
                )}
              </AccordionDetails>
            </Accordion>
          </Box>

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