# 竞品与需求分析

调研日期：2026-09-21。来源为项目官方仓库、源码与文档；功能表表示来源中可确认的覆盖范围，不能据此保证每项功能在本机可用。主分支会变化，发布基准必须另行固定具体版本。

## 结论

**有条件继续。** 消费级 GPU 的模型适配建议、显存估算、推理测速和参数寻优已经有相当多的工具，不能以“没人做过”作为立项依据。若目标只是告诉用户哪个模型能跑、自动找最快的 llama.cpp 参数，应优先使用或贡献给 llmfit / llama-autotune，另造通用工具的价值不足。

值得验证的小范围产品是：**把本地部署试验做成可以审阅、重跑和解释失败的证据包**。输入固定模型文件、运行器和候选配置，输出每次实际运行的上下文、资源、速度、失败与恢复记录。先做好单机、单请求、llama-server 的完整生命周期，再考虑其他后端。这是产品取舍和待验证假设，不是已证明的独占市场缺口。

## 直接与相邻工具

| 项目与一手来源 | 已解决的核心问题 | 本项目的取舍 |
| --- | --- | --- |
| [llmfit](https://github.com/AlexsJones/llmfit)、[benchmark guide](https://github.com/AlexsJones/llmfit/blob/main/docs/benchmarking.md)、[scoring model](https://github.com/AlexsJones/llmfit/blob/main/docs/how-it-works.md) | 硬件识别，模型/量化/上下文适配与速度估计；Windows 等多平台；多种本地服务；真实 TTFT/TPS 测量、结果本地保存及可选社区分享。质量适配评分包含启发式与已有基准信息。 | **广义产品定位最强重叠。** 不做模型目录、综合推荐分、社区榜单和下载管理。其基准指南面向已启动 provider；本项目侧重自己启动、验证、关闭每次部署并保留失败轨迹。不能把估计评分当作本机量化质量实测。 |
| [llama-autotune](https://github.com/Najafu/llama-autotune)、[benchmark source](https://github.com/Najafu/llama-autotune/blob/main/src/llama_autotune/benchmark.py)、[constraints source](https://github.com/Najafu/llama-autotune/blob/main/src/llama_autotune/constraints.py) | Windows/Linux/macOS 硬件与 GGUF 检查、VRAM 估计、OOM 识别、启发式/网格/Optuna 搜索、上下文/吞吐/效率目标、导出 profile 和启动服务器。 | **llama.cpp 自动调参最强重叠。** 不做新的优化器。当前测速源码包装 llama-bench，memory 回退到 RSS，startup_time 记录整个 benchmark 进程耗时；本项目需要明确区分 GPU 显存、RSS、模型就绪和请求延迟。 |
| [llama.cpp / llama-bench](https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md) | pp/tg/pg、上下文 depth、GPU layers/KV 等参数组合、预热、重复测量、标准差、JSON/CSV/Markdown；已提供 fit-target。测量不包含 tokenization 和 sampling。 | 不复制推理引擎或底层吞吐基准。服务器客户端观察到的首个 token 延迟需要单独测量，不能从 pp/tg 反推。 |
| [llama.cpp SPEED-Bench client](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/bench/speed-bench/README.md) | 对运行中的 llama-server 做任务分类测速，记录引擎 prefill/decode、请求延迟及 speculative acceptance，并比较 baseline。 | “真实文本 + HTTP 性能报告”也已有上游实现。我们的剩余范围是部署生命周期、配置兑现检查、资源与失败恢复证据。 |
| [vLLM bench](https://docs.vllm.ai/en/latest/cli/bench/) | 单批 latency、在线 serving throughput、offline throughput、startup、参数 sweep。 | vLLM 用户的服务压测直接使用上游；v0.1 不增加 vLLM 依赖。未来接入时复用它的能力和指标定义。 |
| [Optimum-Benchmark](https://github.com/huggingface/optimum-benchmark) | Transformers/PyTorch、llama-cpp-python、vLLM 等后端；量化/优化比较；隔离进程、资源与模型加载测量、warmup、配置扫描、JSON/Markdown 与环境记录。 | 不建设通用 Transformers 性能框架。它与整个工程需求有较大重叠，可成为未来适配来源。README 自述仍在开发中，不能简单称为“生产级全面解决方案”。 |
| [NVIDIA GenAI-Perf](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/perf_benchmark/genai-perf-README.html)、[AIPerf](https://github.com/ai-dynamo/aiperf) | 服务流式 TTFT、ITL、请求延迟、输入/输出长度、吞吐、负载和报告；AIPerf 官方示例也能测本地 Ollama。 | 不做并发压测平台。流式计时与客户端/服务端吞吐必须分开定义，不能声称 TTFT 报表本身具有差异化。 |
| [GPUStack GGUF Parser](https://github.com/gpustack/gguf-parser-go) | 远程读取 GGUF 元数据，无需完整下载；估算 CPU/GPU 内存、context、offload、KV 等影响；基于设备指标估计最大 TPS。 | 不再写“参数量 × 位宽”的万能适配计算器。估算可筛选候选，实际运行与观测才支持本机结论；该项目精度描述是作者声明，不是本次验证。 |
| [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)、[llama.cpp perplexity](https://github.com/ggml-org/llama.cpp/blob/master/tools/perplexity/README.md) | 成熟任务评估框架；HF/vLLM/GGUF 等接入；上游 PPL、与参考权重对比的 KL 等。 | 不造模型能力评测平台。轻量结果接入或受控小样本回归检查即可。 |

## 真实问题与可验证价值

1. **“4K 能跑”不等于真的测了 4K 工作负载。** 报告需区分分配上下文、实际输入、生成量、缓存复用、截断、上下文滑动和并发槽数。最大上下文只能报告“已测最大成功值”，不能把模型标称窗口或未测估算写成验证值。
2. **失败后换配置会改变问题。** 降低 GPU layers、上下文、KV 精度或量化文件必须生成新的 attempt，保留原失败、触发原因和实际配置，不能把降级成功冒充原配置成功。
3. **指标名称常相同，口径未必相同。** 整卡采样 VRAM、进程 RSS、引擎 decode TPS、端到端输出 TPS、客户端 TTFT、启动到 ready 时间需显式分列，未知保留 null。采样峰值不是瞬时真实峰值。
4. **本机结果需要可复查的身份。** 保存模型和二进制 SHA256、版本、驱动/硬件、配置、工作负载 hash、原始响应与日志、重复试验分布；测试替身与真实 GPU 结果必须明确标记。

以上是从工具的公开工作流和本地已有实验记录归纳出的工程取向。没有发现一个已核实的工具完全包办本次严格的证据契约，但本次调研也没有证明其他项目绝无这些能力。代码存在缺陷更应考虑上游贡献，不能把修复常见 bug 当作长期产品壁垒。

## 建议的 v0.1 最小范围

- Python CLI + 本地 JSON 配置；一个真实 llama-server backend；另一个显式标记的模拟 backend 仅用于无 GPU demo 和测试。
- 用户提供本地 GGUF 与已安装运行器，先验证现有 Qwen 小模型路径；不在首版捆绑权重或承诺所有模型族。
- 单机单 GPU、单并发；候选 context 为 1K/2K/4K/8K/16K，按配置选择；GPU layers 与 KV 参数显式配置。只汇报执行过的组合。
- 分离加载/预热/测量/清理；精确工作负载、流式 TTFT、引擎 PP/decode、总延迟、整卡 VRAM 采样、系统 RAM 与进程 RSS。
- OOM、超时、协议错误、退出和清理失败的分类；有限、显式配置的 fallback，失败记录不可覆盖。
- versioned JSON 结果、CSV、Markdown、测试与真实 benchmark 示例、安装验证、CI。跨后端抽象保持小而具体。

**暂不包含：** 自研推理、量化转换、全模型推荐器、自动下载海量候选、贝叶斯寻优、排行榜、能耗价格综合评分、并发服务 SLA、分布式执行、Web 平台。FP16/BF16、INT8/INT4、GPTQ/AWQ 的全矩阵属于后续 backend 议题；GGUF 是容器格式，不能作为一种量化精度与它们平级比较。

## 轻量质量评估建议

先提供固定输入和确定性评分的回归检查，报告逐项结果与样本量，明确其只能排除明显损坏。**几道算术/问答题通过不能得出“量化损失为 0%”。** 无同源参考模型、同样本和同一评分契约时，质量差值应为未测。

更可靠但仍有限的扩展是：复用上游 llama-perplexity，在固定、公开许可、哈希锁定的短语料上比较同源模型不同量化的 PPL；或使用 lm-eval 固定任务子集、数据版本、样本 ID、seed、模板和后端版本，保存逐项配对结果与不确定性。PPL 不等于用户感知质量，不能跨 tokenizer 直接比较；KL 需要参考 logits，磁盘代价可能很高。12GB 无法容纳参考权重时可顺序 CPU offload，但必须公开时间成本和基线限制。上述约束见 [llama.cpp perplexity 官方说明](https://github.com/ggml-org/llama.cpp/blob/master/tools/perplexity/README.md)。

## 投入门槛与停止条件

首版价值验收应是：新开发者从 README 安装后，能对自己的 GGUF 跑出一次成功部署或一份可诊断的失败报告，并看清降级后牺牲了什么；另一台机器能够按同一契约重跑。现有 4070 SUPER 实验可作为方法来源，但不能直接改名充作新软件真实验证。

发布后优先争取至少 2 位外部开发者在其他消费级 GPU 上复跑，收集安装/证据缺口。如果结果只是 llama-bench 的格式转换，或上游工具通过一份配置即可达到同一证据契约，则收缩为上游适配器、文档或贡献补丁。开源申请与项目曝光不能替代这个验收。
