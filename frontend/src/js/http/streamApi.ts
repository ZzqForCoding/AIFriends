/*
 * 功能：在每个请求头里自动添加`access token`。
 * 然后拦截请求结果，如果返回结果是身份认证失败（401），
 * 则说明`access_token`过期了，那么调用api刷新token`，
 * 如果刷新成功，则重新发送原请求。
*/

import { fetchEventSource } from '@microsoft/fetch-event-source';
import {useUserStore} from "@/stores/user.ts";
import api from "./api.js";

const BASE_URL = 'http://127.0.0.1:8000/';

/**
 * 流式请求选项
 */
interface StreamApiOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: Record<string, any>;
  headers?: HeadersInit;
  onmessage?: (data: any, isDone: boolean) => void;
  onerror?: (err: Error) => void;
  onclose?: () => void;
}

/**
 * 通用的流式请求工具
 * @param {string} url 请求地址
 * @param {StreamApiOptions} options 配置项
 */
export default async function streamApi(
  url: string,
  options: StreamApiOptions = {}
): Promise<void> {
  const userStore = useUserStore();

  const startFetch = async (): Promise<void> => {
    await fetchEventSource(BASE_URL + url, {
      method: options.method || 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userStore.accessToken}`,
        ...options.headers,
      } as HeadersInit,
      body: JSON.stringify(options.body || {}),
      openWhenHidden: true,
      async onopen(response: Response): Promise<void> {
        // 处理 401 Token 过期
        if (response.status === 401) {
          try {
            await api.post('/api/user/account/refresh_token/', {});
            throw new Error("TOKEN_REFRESHED");
          } catch (err) {
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
        if (err.message === "TOKEN_REFRESHED") {
          return startFetch();
        }
        if (options.onerror) {
          options.onerror(err);
        }
        throw err;
      },
      onclose: options.onclose,
    });
  };

  return startFetch();
}