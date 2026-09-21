# 独立 CR：llama.cpp backend 与进程生命周期

日期：2026-09-21。审阅者为独立研究/报告模块代理，未编写被审阅 backend。范围：`src/prismbench/backends/process.py`、`llama_cpp.py` 及对应进程/协议测试。此记录属于 GPU 实测前的模块审阅，不是最终发布审计。

## 结论

发现的 2 项 P1 均由 backend 作者修复，已独立复验。当前没有未解决的阻断项，可以进入真实模型验证。

| 编号 | 原问题与影响 | 修复与复验 |
| --- | --- | --- |
| B1 / P1 | `_runtime_info` 启动的 `--version` / `--help` 进程清理失败时，只抛出普通错误而丢弃清理结果；`backend.close()` 仍可能返回默认成功，导致队列在自有进程未确认回收时继续。 | 保留 `_preflight_cleanup_failure`，合并到 backend 清理状态，后续成功不能覆盖先前失败。注入 `remaining_pids` 的独立检查确认 `backend.close()` 为 false；`test_failed_runtime_preflight_cleanup_stays_failed` 覆盖了后续成功清理的情况。 |
| B2 / P1 | `OwnedProcess.__init__` 的部分初始化失败路径先执行 `kill()` / `wait()`，如果这一步也抛出异常，未进入 Job 关闭；Windows kill-on-close 所依赖的句柄会泄漏。 | 将 Job 关闭置于 `finally`。独立读取最终代码，并通过 `test_failed_assignment_closes_job_even_when_direct_kill_raises` 验证：即使分配失败后直接 kill 再失败，Job 仍被关闭。 |

## 验证

在本机 Windows 虚拟环境执行：

```text
python -m pytest tests/test_llama_cpp.py tests/test_process.py -q
25 passed in 11.20s
```

这组检查实际创建本地替身 HTTP server 和进程，不加载 LLM 或 GPU。覆盖正常流式请求和证据保存、OOM 与普通 HTTP 错误区分、启动失败、上下文不符、缺终止事件、持续慢流的总超时、终止事件文本不能冒充首块生成文本、质量探针缓存/截断拒绝、自有孙进程清理、无关进程保留、Windows 控制器崩溃自动回收，以及上述 2 项回归。

## 已检查的设计边界

- 仅绑定 loopback，临时 API key 验证 `/props`，降低端口竞争导致连接到其他服务的风险；HTTP client 不使用环境代理。
- 显式禁止 automatic fit、context shift、prompt cache、额外槽位；实际 context 必须匹配，已识别的 GPU layers/KV/Flash Attention 与请求不符时拒绝。日志不提供的配置保留 unknown 和 warning，不能改写成已经验证。
- OOM 需要分配失败证据，不将任意退出码、HTTP 500 或通用 CUDA 错误直接标记为 OOM。
- 请求具有单独的总耗时边界，超时会关闭自有服务。TTFT 字段按当前实现描述为首个非空生成文本块的客户端观察时间，不能等同底层第一个 token 的精确时间。
- Windows 使用暂停创建、分配 Job、恢复主线程；POSIX 使用独立进程组。POSIX 不承诺在控制器遭受不可捕获终止后自动回收，跨平台承诺应保持此限制。

## 后续验证仍需完成

真实 llama-server 的版本兼容性、实际上下文/token 工作量兑现、有效层数与资源样本、GPU 实测完整报告，以及 wheel 安装后的入口和资源文件加载仍由集成/最终审计负责。本次通过不能替代真实 benchmark。
