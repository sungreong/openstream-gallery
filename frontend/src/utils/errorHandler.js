/**
 * API 오류 응답을 안전하게 문자열로 변환하는 함수
 * FastAPI의 유효성 검사 오류 등을 처리
 */
export const formatErrorMessage = (error) => {
  // 기본 오류 메시지
  if (typeof error === 'string') {
    return error;
  }

  // HTTP 응답 오류
  if (error.response) {
    const { data, status } = error.response;
    
    // FastAPI 유효성 검사 오류 (422)
    if (status === 422 && data.detail && Array.isArray(data.detail)) {
      const validationErrors = data.detail.map(err => {
        if (typeof err === 'object' && err.msg) {
          const location = err.loc ? err.loc.join('.') : '';
          return location ? `${location}: ${err.msg}` : err.msg;
        }
        return String(err);
      });
      return `유효성 검사 오류: ${validationErrors.join(', ')}`;
    }
    
    // 일반적인 API 오류
    if (data.detail) {
      return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    }
    
    if (data.message) {
      return typeof data.message === 'string' ? data.message : JSON.stringify(data.message);
    }
    
    // HTTP 상태 코드 기반 메시지
    switch (status) {
      case 400:
        return '잘못된 요청입니다.';
      case 401:
        return '인증이 필요합니다.';
      case 403:
        return '권한이 없습니다.';
      case 404:
        return '요청한 리소스를 찾을 수 없습니다.';
      case 500:
        return '서버 내부 오류가 발생했습니다.';
      default:
        return `HTTP ${status} 오류가 발생했습니다.`;
    }
  }
  
  // 네트워크 오류
  if (error.message) {
    return error.message;
  }
  
  // 알 수 없는 오류
  if (typeof error === 'object') {
    try {
      return JSON.stringify(error);
    } catch {
      return '알 수 없는 오류가 발생했습니다.';
    }
  }
  
  return String(error);
};

/**
 * API 응답을 안전하게 처리하는 함수
 */
export const handleApiResponse = async (response) => {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(formatErrorMessage({ response: { status: response.status, data: errorData } }));
  }
  
  return response.json();
};

/**
 * fetch API를 사용한 안전한 API 호출
 */
export const safeFetch = async (url, options = {}) => {
  try {
    const response = await fetch(url, options);
    return await handleApiResponse(response);
  } catch (error) {
    throw new Error(formatErrorMessage(error));
  }
}; 