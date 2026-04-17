/*
 * 功能：在每个请求头里自动添加`access token`。
 * 然后拦截请求结果，如果返回结果是身份认证失败（401），
 * 则说明`access_token`过期了，那么调用api刷新token`，
 * 如果刷新成功，则重新发送原请求。
*/

import { fetchEventSource } from '@microsoft/fetch-event-source';
import { useUserStore } from "@/stores/user.js";
import api from "./api.js";
import CONFIG_API from '@/js/config/config.ts'

const BASE_URL = CONFIG_API.HTTP_URL

/**
 * 流式请求选项
 */
interface StreamApiOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: Record<string, any>;
  headers?: HeadersInit;
  signal?: AbortSignal;
  onmessage?: (data: any, isDone: boolean) => void;
  onerror?: (err: Error) => void;
  onclose?: () => void;
}

/**
 * 通用的流式请求工具
 * @param {string} url 请求地址
 * @param {StreamApiOptions} options 配置项 (method, body, onmessage, onerror等)
 */
export default async function streamApi(url: string, options: StreamApiOptions = {}): Promise<void> {
  const userStore = useUserStore();

  const buildHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${userStore.accessToken}`,
    };
    if (!options.headers) return headers;

    if (Array.isArray(options.headers)) {
      options.headers.forEach(([key, value]) => {
        headers[key] = value;
      });
    } else if (options.headers instanceof Headers) {
      options.headers.forEach((value, key) => {
        headers[key] = value;
      });
    } else {
      Object.assign(headers, options.headers);
    }
    return headers;
  };

  const startFetch = async (): Promise<void> => {
    await fetchEventSource(BASE_URL + url, {
      method: options.method || 'POST',
      headers: buildHeaders(),
      body: JSON.stringify(options.body || {}),
      signal: options.signal,
      openWhenHidden: true,  // 允许后台运行，防止浏览器因隐藏页面而强制关闭它
      async onopen(response: Response): Promise<void> {
        // 1. 处理 401 Token 过期
        if (response.status === 401) {
          try {
            // 触发 api.js 中的 Axios 拦截器进行静默刷新
            await api.post('/api/user/account/refresh_token/', {});
            // 抛出特定错误触发下面的 onerror 重试逻辑
            throw new Error("TOKEN_REFRESHED");
          } catch (err) {
            // 如果刷新失败（refresh_token也过期），直接报错由上层处理
            throw err;
          }
        }

        if (!response.ok || !response.headers.get('content-type')?.includes('text/event-stream')) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `请求失败: ${response.status}`);
        }
      },
      onmessage(msg): void {
        if (msg.data === '[DONE]') {
          if (options.onmessage) options.onmessage('', true);
          return;
        }
        try {
          const json = JSON.parse(msg.data);
          if (options.onmessage) options.onmessage(json, false);
        } catch (e) {
          console.error("流解析失败:", e);
        }
      },
      onerror(err: Error): void {
        // 2. 捕获重试信号并递归
        if (err.message === "TOKEN_REFRESHED") {
          startFetch();
          return
        }

        // 其他错误则按用户定义的 onerror 处理
        if (options.onerror) {
          options.onerror(err);
        }
        throw err; // 停止自动重试
      },
      onclose: options.onclose,
    });
  };

  return startFetch();
}