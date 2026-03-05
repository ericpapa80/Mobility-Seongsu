/**
 * Backend Adapter for Framework Integration (Node.js)
 * Framework 프로젝트의 backend API와 통신하는 어댑터 (Node.js 버전)
 * 
 * Python 수집기를 Node.js에서 호출하거나 직접 사용할 수 있습니다.
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const execAsync = promisify(exec);
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export class BackendAdapter {
  constructor(backendUrl = null) {
    this.backendUrl = backendUrl || process.env.BACKEND_API_URL || 'http://localhost:3000';
    this.apiEndpoint = `${this.backendUrl}/api/collectors/raw`;
  }

  /**
   * Python 수집기 실행
   * @param {string} collectorType - 수집기 타입 (예: 'sgis', 'sbiz')
   * @param {object} params - 실행 파라미터
   * @returns {Promise<object>} 실행 결과
   */
  async executePythonCollector(collectorType, params = {}) {
    try {
      const collectorPath = join(__dirname, '..', 'core', 'runner.py');
      const paramsJson = JSON.stringify(params);
      
      const { stdout, stderr } = await execAsync(
        `python -m core.runner run ${collectorType} --params '${paramsJson}'`,
        { cwd: join(__dirname, '..') }
      );

      if (stderr) {
        console.warn(`Python collector stderr: ${stderr}`);
      }

      return JSON.parse(stdout || '{}');
    } catch (error) {
      console.error(`Failed to execute Python collector ${collectorType}:`, error);
      throw error;
    }
  }

  /**
   * 수집된 데이터를 backend API로 전송
   * @param {string} collectorType - 수집기 타입
   * @param {any} rawData - 원시 데이터
   * @param {object} metadata - 메타데이터
   * @returns {Promise<object>} API 응답
   */
  async sendRawData(collectorType, rawData, metadata = {}) {
    try {
      const payload = {
        collector_type: collectorType,
        data: rawData,
        timestamp: new Date().toISOString(),
        metadata: metadata
      };

      console.log(`Sending data to backend: ${collectorType}`, {
        endpoint: this.apiEndpoint,
        dataSize: JSON.stringify(rawData).length
      });

      const response = await fetch(this.apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Backend API error: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      console.log(`Successfully sent data to backend: ${collectorType}`, {
        status: result.status,
        message: result.message
      });

      return result;
    } catch (error) {
      console.error(`Failed to send data to backend: ${collectorType}`, {
        error: error.message,
        endpoint: this.apiEndpoint
      });
      throw error;
    }
  }

  /**
   * Backend API 상태 확인
   * @returns {Promise<object>} 상태 정보
   */
  async checkBackendStatus() {
    try {
      const healthEndpoint = `${this.backendUrl}/api/health`;
      const response = await fetch(healthEndpoint, { timeout: 5000 });
      
      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.warn(`Backend health check failed: ${error.message}`);
      return { status: 'unavailable', error: error.message };
    }
  }

  /**
   * 수집 결과를 backend로 전송
   * @param {string} collectorType - 수집기 타입
   * @param {object} result - 수집 결과
   * @returns {Promise<object>} API 응답
   */
  async sendCollectionResult(collectorType, result) {
    const metadata = {
      records_collected: result.records_collected || 0,
      errors: result.errors || [],
      start_time: result.start_time,
      end_time: result.end_time
    };

    return this.sendRawData(
      collectorType,
      result.data || {},
      metadata
    );
  }
}

// 싱글톤 인스턴스
let _backendAdapter = null;

/**
 * BackendAdapter 싱글톤 인스턴스 반환
 * @returns {BackendAdapter} 인스턴스
 */
export function getBackendAdapter() {
  if (!_backendAdapter) {
    _backendAdapter = new BackendAdapter();
  }
  return _backendAdapter;
}

