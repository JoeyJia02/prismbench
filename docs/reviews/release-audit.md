# 独立发布审计：安装、文档与开源可用性

日期：2026-09-21。审阅者负责竞品研究和报告模块，独立检查打包、CLI 安装体验、README、CI 与仓库边界。未运行 GPU 工作负载，也未将其他成员运行的测试或 benchmark 冒充自己的执行结果。

## 结论

**具备发布实验性 alpha 的基础，不能宣称稳定版或已经公开发布。** 当前设计规模合理，开源价值来自可审阅的部署与失败证据；通用模型适配、自动寻优和完整能力评测已有更成熟的替代工具。README 已清楚推荐这些替代工具，并限制本项目的承诺。

审计中发现的 CLI 输入错误 P2 已修复并独立复验。报告汇总身份 P2 也已按最终审阅要求修复：即使 token 数相同，prompt hash 或 runtime version 不同，也不混算均值或排列性能。

剩余发布门槛是最终源码快照的重新打包、完整文档/实测链接收口，以及真实的远端 CI 与公开发布。前两项由最终审计收口；后两项在未配置远端时应保持明确未完成。没有因本次审阅发现的问题而要求添加服务、数据库、Web 界面或新的重依赖。

## 独立执行的检查

| 检查 | 实际结果 |
| --- | --- |
| Wheel 内容和源码比对 | 审计时的 wheel 共 22 个条目、39,766 字节；所有包内 `.py` / `.json` 与当时源码逐字节一致。包含 `probes.json`、`result.schema.json` 和 MIT LICENSE。 |
| Source distribution 内容 | 当时 sdist 共 65 个条目、76,973 字节；包含 docs、examples、tests 及 `tests/fixtures/fake_llama_server.py`。未发现模型、运行器、旧实验、DLL、EXE 或 GGUF 被打入包。 |
| 干净环境导入 | 使用已单独安装 wheel 的虚拟环境，带 `-I` 验证导入来自 `site-packages`，两份 packaged data 均可加载。 |
| 真正位于仓库之外的 CLI | 从系统临时目录运行已安装的 `prismbench.exe`：version、help、demo、report 全部 exit 0；没有依赖 checkout cwd。 |
| 依赖一致性 | 已安装环境执行 `python -m pip check` 通过。 |
| 无 GPU demo | ledger 为 `SUCCESS → OOM → SUCCESS` 且 session 为 synthetic；没有调用模型或 GPU。 |
| 报告重新导出 | 相对链接指向原 demo 的证据；原数据未复制/覆盖。拒绝重复导出目录，exit 2。 |
| 普通输入错误 | 不存在的配置文件返回 exit 2，无 traceback。 |
| 无效 schema 回归 | 初次在已安装 wheel 上复现 exit 1 + traceback；根因是 CLI 未捕获 `jsonschema.ValidationError`。修复后从源码执行同一输入，exit 2 且无 traceback。最终 wheel 必须包含此修复。 |
| 最终报告身份回归 | `tests/test_report.py` 44 项通过，Ruff 通过；覆盖不同 prompt/runtime 不混算、不同 runtime 不排名、成功结果必须记录 runtime version。 |
| 本地文档链接 | README、CONTRIBUTING、release checklist 的链接已检查；仅最终负责人正在编写的 `validation.md` 和 `final-audit.md` 在检查时尚不存在。发布前必须收口。 |
| 资产与凭据边界 | `git check-ignore` 确认旧 README、模型、运行器、下载、实验记录、授权 JSON、旧脚本、虚拟环境和个人 outputs 被忽略。对拟发布文本的常见 GitHub/HF/OpenAI/AWS/private-key 模式检查无命中；该检查不等于完整秘密扫描。 |

本地详细 CLI 检查记录位于忽略的 `outputs/release-audit/installed-cli-checks.json`，没有把个人临时目录路径写入发布文档。最初安装检查的 wheel/sdist 是修复前快照，不能用它们替代最终构建。最终构建哈希和重新安装结果应以最终审计为准。

## 文档、CI 与维护体验

- README 的 `pip install .`、单命令 demo、配置路径解析、已有输出目录保护、错误码、模型许可和指标定义与已检查实现一致。对“最大上下文”“TTFT 近似”“整卡采样峰值”“质量 smoke probes”均有明确限制。
- 样例为 Windows 路径；README 告知 Linux/WSL 需替换二进制和路径。发布的固定模型样例应同时指向可获取的精确源与 SHA256，不能只给模糊文件名。
- `pyproject.toml` 的 alpha classifier 与 `0.1.0a1` 一致；运行时仅有 psutil/jsonschema 两个直接依赖。MIT LICENSE 与第三方模型/运行器许可分开说明，贡献指南要求记录外部数据的来源和许可。
- CI 配置包括 Windows/Linux、Python 3.10/3.12/3.14、lint、CPU/进程协议测试、构建以及隔离环境 wheel demo。这里只验证配置存在与命令结构，**没有观察到远端执行**；不能宣称 Linux/多 Python 版本的远端 CI 已绿。
- issue 模板、贡献指南、roadmap/backlog 与发布 checklist 齐备。检查时已有 3 个清晰本地提交，没有 Git remote。文档/样例/许可证/CI/真实结果仍需进入最终提交。
- sdist 默认不包含原始 benchmark 目录。若 validation 使用相对链接，需明确完整证据在 Git checkout/单独证据归档中，并让 sdist 中的阅读路径有清晰说明；wheel 无需打包 benchmark。

## 风险与产品判断

没有明显过度设计：一个 CLI、一个真实 backend、一个测试替身、纯文件输出和小接口。进程树所有权、严格结果验证、失败 ledger 与证据身份带来实现成本，但直接服务用户所要求的可信性和恢复路径。

最重要的未验证项是**别人是否能顺利复跑并从报告中做出部署决定**。本机 4070 SUPER 结果可以证明这一配置可执行，不能替代 8/16/24GB 设备覆盖、其他模型族或外部开发者的安装反馈。至少获得外部复跑、处理真实用户问题并证明比组合现有工具省事后，再扩大功能或主张更强的生态价值。新建本地项目没有已证明的 adoption 或 OSS 资助资格。

本审计不替代实测可信度审计。最终负责人仍需核对完整请求数量、失败与恢复记录、真实结果 provenance、模型/运行器版本与最终发布快照的关系。

## 最终负责人收口

后续已重建并安装包含 CLI/report/v2 probe 修复的最终 wheel，SHA256 `07576ad9355c69a413581010a49250cb709c00a07c1ec1bbf1cace54cad0d349`。150 项测试通过，1 项可选 GPU 测试跳过；另行完成 21/21 次安装包真实 GPU 验证。完整 benchmark 已加入 sdist manifest，压缩源码包约 1.5 MB，不含模型或运行器。`validation.md`、`final-audit.md` 和 `benchmark-audit.md` 已补齐。最终有效结论以这些文件的证据和声明边界为准。
