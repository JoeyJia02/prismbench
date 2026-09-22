# Community post drafts

**Status: not posted.** These are editable drafts for the maintainer. Verify the
links after merging, check the destination's current rules and review the text
before publishing. Do not paste the whole document into a community. The
[first-user plan](community-launch.md) records intended outcomes and remaining
steps. No users, endorsements or external reproductions are claimed here.

The table values below were checked against the public
[machine-readable summary](https://github.com/JoeyJia02/prismbench/blob/63df69ab4512be258670ca51bbf23adfca95a006/benchmarks/rtx4070-super/quantization-quality-20260922/summary.json).

## English: llama.cpp Show and tell

**Suggested title:** PrismBench alpha: inspectable llama.cpp deployment reports,
with a Qwen3-1.7B F16/Q8/Q4 pilot on a 12 GB GPU

I'm maintaining [PrismBench](https://github.com/JoeyJia02/prismbench), a small
Python CLI for measuring a local llama.cpp deployment. It starts and stops its
own server, checks the input/output tokens that actually ran, and saves latency,
sampled memory, configuration, hashes, raw logs and failed attempts in JSON,
CSV and Markdown. Confirmed OOM can advance through explicitly configured
fallbacks; cleanup and failures remain in the record.

Here is one measurement from an RTX 4070 SUPER 12 GB, Windows, llama.cpp b10964.
Qwen3-1.7B Q8_0 and Q4_K_M were both derived from the same F16 file. Performance
is three separate server lifetimes per variant with 1,792 fresh input tokens,
128 output tokens and 2K context.

| Format | File GB | Mean first-text latency, s | Mean generation token/s | Sampled device peak, MiB | Prefix PPL |
|---|---:|---:|---:|---:|---:|
| F16 reference | 4.070 | 0.2050 | 104.14 | 5,197 | 15.0861 |
| Q8_0 | 2.165 | 0.1767 | 167.33 | 3,645 | 15.1083 |
| Q4_K_M | 1.282 | 0.1791 | 233.20 | 2,953 | 16.3602 |

GB is decimal. Peak memory covers the whole selected GPU, including desktop
applications. Background GPU activity was not controlled, and this is one
machine, not an independent hardware replication or universal format ranking.

PPL was measured separately with upstream `llama-perplexity`, on 32 preselected
2K chunks from the WikiText-2 raw test prefix: 32,736 scored targets. The F16
reference was converted from a pinned community BF16 artifact; equivalence to
the official checkpoint was not independently established. Q8/Q4 PPL changes
were +0.147%/+8.446%. **Those percentages are not general capability losses.**
The pilot does not measure chat/reasoning accuracy. Its recipe uses optional
source-checkout helpers, separate from the installed CLI and its smoke probes.

[Full method, limitations and evidence](https://github.com/JoeyJia02/prismbench/blob/main/docs/validation-quantization-20260922.md)
include hashes, failed pilots and the paired likelihood analysis.

The tool is an **experimental alpha**, available as a
[GitHub Release](https://github.com/JoeyJia02/prismbench/releases/tag/v0.1.0a1),
not on PyPI. Its offline demo is synthetic. If you already have llama.cpp and a
GGUF, the [first-run guide](https://github.com/JoeyJia02/prismbench/blob/main/docs/first-run.md)
shows how to generate a real report for your own machine.

I'm looking for the first 3–5 external users, especially on 8/16/24 GB NVIDIA
GPUs or Linux. The current GPU memory collector uses NVIDIA `nvidia-smi`.
Start with one 2K lifetime; three repetitions and full evidence are optional
next steps. Did installation work, and did the report help with your
configuration choice?
[Short setup feedback](https://github.com/JoeyJia02/prismbench/issues/new?template=first_run.md) and
[real-machine reports](https://github.com/JoeyJia02/prismbench/issues/1) are useful,
including failures. A short description is enough to start, with no attachment
required. Before posting logs, follow
[sharing results](https://github.com/JoeyJia02/prismbench/blob/main/docs/sharing-results.md):
paths, identifiers and token IDs can reveal private information. There is no
automatic anonymization. No deliberate OOM test is needed.

Development and documentation are AI-assisted with OpenAI Codex. The linked
tests, raw evidence and limitations are available for inspection; this is early
work and feedback on the methodology is welcome.

## 中文：技术分享与首批体验邀请

**建议标题：** 12GB 显卡上 Qwen3-1.7B 的 F16、Q8、Q4 实测：速度、显存与困惑度

本地跑模型时，我想知道的不只是“能不能启动”，还有：这个上下文是否真的跑完，
速度和显存代价是多少，失败后换配置能否继续，以及结果能不能复查。

我正在维护 [PrismBench](https://github.com/JoeyJia02/prismbench)，一个小型 Python CLI。
它管理本地 llama.cpp 服务，核对实际输入/输出 token 数，记录延迟、采样内存、
模型与运行时哈希、原始日志和失败尝试，输出 JSON、CSV 和 Markdown 报告。
确认 OOM 后可以按用户明确指定的配置依次降级，并保留每次尝试。

这次使用一张 RTX 4070 SUPER 12GB、Windows 和 llama.cpp b10964，比较
Qwen3-1.7B 的同源 F16、Q8_0 和 Q4_K_M。性能测试固定为 2K 上下文、
1,792 个新输入 token、128 个输出 token，每种配置独立启动服务三次。

| 格式 | 文件大小，GB | 平均首段文本延迟，秒 | 平均生成 token/s | 整卡采样峰值，MiB | 文本前缀 PPL |
|---|---:|---:|---:|---:|---:|
| F16 参考 | 4.070 | 0.2050 | 104.14 | 5,197 | 15.0861 |
| Q8_0 | 2.165 | 0.1767 | 167.33 | 3,645 | 15.1083 |
| Q4_K_M | 1.282 | 0.1791 | 233.20 | 2,953 | 16.3602 |

这里的 GB 为十进制。相对 F16，Q8/Q4 文件分别缩小约 46.8%/68.5%。
这个工作负载中，Q4 生成更快，但文本预测代价也更大；不能据此给所有模型排序。

困惑度由上游 `llama-perplexity` 单独测量，使用预先选定的 WikiText-2 raw test
前 32 个 2K 文本块，共 32,736 个评分目标。参考 F16 来自固定哈希的社区 BF16
文件转换，Q8 和 Q4 分别由该 F16 量化；没有独立验证社区母本与官方权重完全一致。
Q8/Q4 的 PPL 分别上升约 0.147%/8.446%，**这不等于整体能力下降了对应百分比**，
也不是聊天、推理或中文任务准确率。Q8 的小幅变化不能证明完全没有退化。

这还是单机试验：后台 GPU 负载没有严格控制，显存是包含桌面应用的整卡采样峰值，
不是精确的模型分配峰值。Q8/Q4 的首段文本延迟差异很小，不适合据此判定谁更快。
[完整方法、原始证据与限制](https://github.com/JoeyJia02/prismbench/blob/main/docs/validation-quantization-20260922.md)
都已公开。该困惑度试验需要源码中的可选辅助脚本，与安装后的部署测量 CLI、
内置轻量探针是分开的。

PrismBench 当前是 **0.1.0a1 实验性 alpha**，从
[GitHub Release](https://github.com/JoeyJia02/prismbench/releases/tag/v0.1.0a1)
安装，尚未发布到 PyPI。无模型 demo 使用模拟数据，不代表 GPU 性能。
开发与文档使用了 OpenAI Codex 辅助，欢迎检查实现、测试和测量方法。

如果你已经有能运行的 llama.cpp 和 GGUF，可以按
[首次运行指南](https://github.com/JoeyJia02/prismbench/blob/main/docs/first-run.md)
给自己的机器生成一份 2K 部署报告。先跑一个服务生命周期即可，三次重复和完整证据
是后续可选步骤。我们希望先找到 3～5 位外部体验者，尤其是 8GB、16GB、24GB 的
NVIDIA 显卡或 Linux 用户；目前 GPU 内存采集使用 NVIDIA `nvidia-smi`。
最有帮助的反馈是：卡在哪一步，报告能不能帮助你做配置选择。

安装或说明问题可用 [简短反馈表](https://github.com/JoeyJia02/prismbench/issues/new?template=first_run.md)，
外部机器实测可写到 [issue #1](https://github.com/JoeyJia02/prismbench/issues/1)。
失败记录也有价值，不需要提交 PR 或故意制造 OOM。先描述现象即可；公开日志前请
阅读 [分享结果说明](https://github.com/JoeyJia02/prismbench/blob/main/docs/sharing-results.md)，
检查个人路径、设备标识和私有提示词等内容。Token ID 也能还原文本；工具不会自动
匿名化，不要求为初次反馈上传附件。

## Short invitation for an appropriate follow-up

Use only where a person has expressed interest or the community permits it;
this is not a bulk-message template.

> If you already run a GGUF with llama.cpp and are comparing context size or
> GPU placement, PrismBench can record the actual workload, latency, memory and
> failures in a local report. It's an experimental alpha, currently measured
> on one 12 GB GPU. The [first-run guide](https://github.com/JoeyJia02/prismbench/blob/main/docs/first-run.md)
> reuses your existing model/runtime. Feedback on a failed installation is as
> useful as a successful report; a short description is enough to start.

> 如果你已经用 llama.cpp 跑 GGUF，正在比较上下文或 GPU 层数，可以用实验性
> alpha 工具 PrismBench 为自己的配置生成报告。按
> [首次运行指南](https://github.com/JoeyJia02/prismbench/blob/main/docs/first-run.md)
> 可以复用已有模型和运行时。当前只有一张 12GB 显卡的实测，欢迎其他机器尝试；
> 安装失败或报告看不懂也值得反馈，先描述现象即可。
